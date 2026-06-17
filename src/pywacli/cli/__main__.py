import sys
import os
import re
import shutil
import socket
import subprocess
import importlib.resources
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from rich.prompt import Prompt
from pywacli.cli.configuration import run_config_wizard
from pywacli.cli.app import main as launch_dashboard
from pywacli.cli.ui.media_viewer import run_media_viewer
from pywacli.cli.config_manager import (
    get_service_logger,
    console_logs_muted,
    get_send_host,
    get_send_port,
)

console = Console()

# Background WhatsApp session chatter (node logs, connection state). Shown on the
# console AND written to the log file, but silenced on the console while the
# interactive Send flow is active so the picker/prompt stays clean.
_session_log = get_service_logger("pywacli.session")


def _contact_key(jid: str, phone: str = "") -> str:
    """Normalize a contact identifier for dedup (strip WhatsApp suffixes)."""
    raw = jid or phone
    return re.sub(r"@\w+(\.\w+)*$", "", raw).strip()


def _sort_contacts(contacts):
    """Order contacts for the picker: named contacts first (alphabetical,
    case-insensitive), then unnamed / group-only entries by their id."""
    def key(c):
        name = (c.get("name") or "").strip()
        has_name = bool(name) and name != "-"
        ident = c.get("phone") or c.get("jid") or ""
        return (0 if has_name else 1, name.casefold() if has_name else ident)
    return sorted(contacts, key=key)


def _ensure_jid(raw_jid: str) -> str:
    """Ensure a JID has the @s.whatsapp.net suffix."""
    if not raw_jid:
        return ""
    if "@" in raw_jid:
        return raw_jid
    return f"{raw_jid}@s.whatsapp.net"
app = typer.Typer(
    name="pywacli",
    help="Python WhatsApp CLI — Terminal dashboard for WhatsApp",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    setup: bool = typer.Option(
        False, "--setup", "-s",
        help="Run the configuration setup wizard"
    ),
    config: bool = typer.Option(
        False, "--config", "-c",
        help="Open configuration menu"
    ),
):
    if ctx.invoked_subcommand is not None:
        return

    if setup:
        run_config_wizard()
        return

    if config:
        run_config_wizard()
        return

    _show_menu()


@app.command()
def dashboard():
    """Launch the WhatsApp dashboard (default)"""
    launch_dashboard()


@app.command()
def setup():
    """Run the interactive configuration wizard"""
    run_config_wizard()


@app.command()
def config():
    """Open the configuration menu"""
    run_config_wizard()


@app.command()
def send(
    phone: str = typer.Option(..., prompt=True, help="Phone number (e.g. 919876543210)"),
    message: str = typer.Option(..., prompt=True, help="Message text to send"),
):
    """Send a WhatsApp message to a phone number"""
    from pywacli.services.message_sender import send_message
    from pywacli.cli.config_manager import load_config

    config = load_config()
    ws_url = config.get("whatsapp", {}).get("websocket_url", "ws://localhost:3000")

    phone = phone.strip().replace("+", "").replace(" ", "").replace("-", "")

    console.print(f"[cyan]Sending to[/] {phone} ...")
    try:
        result = send_message(phone, message, uri=ws_url)
        console.print(f"[green]Message sent to {phone}[/]")
    except Exception as e:
        console.print(f"[red]Failed to send message: {e}[/]")
        raise typer.Exit(code=1)


@app.command()
def media():
    """Browse stored media files"""
    run_media_viewer()


@app.command()
def automate():
    """Start an AI-powered automated chat session"""
    _interactive_automate()


def _package_dir() -> Path:
    """Filesystem path to the installed `pywacli` package."""
    return Path(str(importlib.resources.files("pywacli")))


def _node_modules_present() -> bool:
    """True if Node deps are resolvable (in the package dir or the cwd)."""
    if _package_dir().joinpath("node_modules").is_dir():
        return True
    return Path("node_modules").is_dir()


@app.command()
def init():
    """Install the Node.js (Baileys) dependencies required by pywacli."""
    npm = shutil.which("npm")
    if shutil.which("node") is None or npm is None:
        console.print("[red]Node.js and npm are required but were not found on PATH.[/]")
        console.print("Install Node.js from https://nodejs.org/ and re-run [bold]pywacli init[/].")
        raise typer.Exit(code=1)

    pkg_dir = _package_dir()
    if not pkg_dir.joinpath("package.json").exists():
        console.print("[red]Bundled package.json not found; cannot install Node dependencies.[/]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Installing Node dependencies in[/] {pkg_dir} ...")
    result = subprocess.run([npm, "install"], cwd=str(pkg_dir))
    if result.returncode != 0:
        console.print("[red]npm install failed.[/]")
        raise typer.Exit(code=result.returncode)
    console.print("[green]✓ Node dependencies installed.[/]")


def _display_qr(qr_string):
    import qrcode
    qr = qrcode.QRCode(border=1)
    qr.add_data(qr_string)
    qr.print_ascii()


class _Session:
    """A live baileys bridge: it owns the single WhatsApp socket, streams events
    (saved to DB, logged to the console), shows the QR, and sends messages over
    the node process's stdin."""

    def __init__(self, proc, stop, connected, cleanup):
        self.proc = proc
        self.stop = stop
        self.connected = connected
        self._cleanup = cleanup

    def wait_connected(self, timeout=None):
        """Block until the WhatsApp session is live. Returns True if connected."""
        import time as _time
        deadline = None if timeout is None else _time.monotonic() + timeout
        while not self.stop.is_set() and self.proc.poll() is None:
            if self.connected.wait(timeout=0.3):
                return True
            if deadline is not None and _time.monotonic() >= deadline:
                break
        return self.connected.is_set()

    def is_alive(self):
        return not self.stop.is_set() and self.proc.poll() is None

    def close(self):
        self._cleanup()


def _launch_session():
    """Spawn the single baileys node bridge, register it for sending, and start
    the background threads that stream/save events and display the QR. Returns a
    _Session. Exits the command if node / its deps are missing."""
    import queue
    import threading
    import json
    from pywacli.services.event_processor import process_event
    from pywacli.services.message_sender import set_node_process

    if shutil.which("node") is None:
        console.print("[red]Node.js was not found on PATH.[/]")
        raise typer.Exit(code=1)
    if not _node_modules_present():
        console.print("[yellow]Node dependencies not found. Run [bold]pywacli init[/] first.[/]")
        raise typer.Exit(code=1)

    baileys_js = _package_dir().joinpath("services", "baileys_service.js")

    console.print("[cyan]Starting WhatsApp bridge...[/]")

    # Tell the node bridge which local port to host its command server on, so a
    # separate Send process can reach this single connection.
    node_env = {
        **os.environ,
        "PYWACLI_SEND_HOST": get_send_host(),
        "PYWACLI_SEND_PORT": str(get_send_port()),
    }

    proc = subprocess.Popen(
        ["node", str(baileys_js)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=node_env,
    )

    set_node_process(proc)

    console.print("[dim]Waiting for QR code...[/]")

    event_queue = queue.Queue()
    stop = threading.Event()
    connected = threading.Event()

    def _read_stdout():
        for line in proc.stdout:
            line = line.strip()
            if line:
                event_queue.put(line)
        event_queue.put(None)

    def _read_stderr():
        for line in proc.stderr:
            text = line.rstrip()
            # Node's verbose logs go to the file always, and to the console
            # unless the Send flow has muted it.
            _session_log.info(text)

    def _process_events():
        while not stop.is_set():
            try:
                line = event_queue.get(timeout=0.5)
            except queue.Empty:
                if proc.poll() is not None:
                    _session_log.error("Node.js process exited unexpectedly.")
                    stop.set()
                    break
                continue

            if line is None:
                stop.set()
                break

            try:
                msg = json.loads(line)
                event = msg.get("event")
                data = msg.get("data", {})

                if event == "auth.qr":
                    # Always surface the QR — it's needed to (re)authenticate.
                    qr_data = data.get("qr", "")
                    console.print("[bold cyan]Scan the QR code below with WhatsApp:[/]")
                    _display_qr(qr_data)
                elif event == "connection.open":
                    user = data.get("user", {})
                    phone = user.get("id", "")
                    connected.set()
                    if not console_logs_muted():
                        console.print(f"[bold green]Connected as {phone}[/]")
                elif event == "connection.close":
                    logged_out = data.get("loggedOut", False)
                    connected.clear()
                    text = ("Logged out. Waiting for new QR..." if logged_out
                            else "Disconnected. Reconnecting...")
                    if not console_logs_muted():
                        console.print(f"[yellow]{text}[/]")
                elif event == "error":
                    err = data.get("message", "Unknown")
                    if not console_logs_muted():
                        console.print(f"[red]Error: {err}[/]")
                else:
                    process_event(event, data)

            except json.JSONDecodeError:
                continue
            except Exception as e:
                _session_log.error(f"Error processing event: {e}")

    threading.Thread(target=_read_stdout, daemon=True).start()
    threading.Thread(target=_read_stderr, daemon=True).start()
    threading.Thread(target=_process_events, daemon=True).start()

    def cleanup():
        stop.set()
        set_node_process(None)
        console.print("[yellow]Disconnecting WhatsApp...[/]")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        console.print("[green]Disconnected.[/]")

    return _Session(proc, stop, connected, cleanup)


@app.command()
def connect():
    """Connect to WhatsApp - single terminal: shows QR and receives/saves events."""
    import time

    session = _launch_session()
    try:
        # Passive listener: stream and save events until interrupted.
        while session.is_alive():
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        session.close()


def _service_reachable():
    """True if a Connect session's local command server is accepting connections."""
    try:
        with socket.create_connection((get_send_host(), get_send_port()), timeout=0.4):
            return True
    except OSError:
        return False


def _menu_send():
    """Menu 6: send through the Connect session running in another terminal.
    Opens no WhatsApp socket of its own — just talks to the command server."""
    if not _service_reachable():
        console.print(
            "[yellow]WhatsApp service not reachable.[/] "
            "Start [bold]Connect (4)[/] in another terminal first."
        )
        Prompt.ask("[dim]Press Enter to continue[/]", default="")
        return
    _interactive_send()


def _interactive_send():
    """Interactive send flow with recent contacts, quick messages and continue option."""
    from pywacli.services.message_sender import send_message
    from pywacli.cli.config_manager import load_config, load_recent_contacts, save_recent_contact
    from pywacli.db.retriver_db import get_all_contacts

    QUICK_MESSAGES = {
        "1": "Hello!",
        "2": "Thank you!",
        "3": "On my way",
        "4": "OK",
        "5": "Call me later",
        "6": "Good morning!",
        "7": "Good night!",
        "8": "Happy Birthday!",
        "9": "See you soon",
        "10": "Sorry, I'm busy right now",
    }

    config = load_config()
    ws_url = config.get("whatsapp", {}).get("websocket_url", "ws://localhost:3000")

    phone = None
    picked_name = ""
    picked_jid = None

    while True:
        # Ask phone number only if we don't have one yet
        if phone is None:
            console.print()
            db_contacts = get_all_contacts()
            recent = load_recent_contacts()

            merged = []
            seen = set()
            for phone_num, push_name, jid in db_contacts:
                key = _contact_key(jid, phone_num)
                if key and key not in seen:
                    merged.append({"phone": phone_num, "name": push_name, "jid": jid})
                    seen.add(key)
            for c in recent:
                key = _contact_key(c.get("jid", ""), c.get("phone", ""))
                if key and key not in seen:
                    merged.append({"phone": c["phone"], "name": c.get("name", ""), "jid": c.get("jid", "")})
                    seen.add(key)

            merged = _sort_contacts(merged)

            if merged:
                table = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
                table.add_column("Key", style="bold magenta", width=4)
                table.add_column("Display", style="bold white", width=22)
                table.add_column("Phone / ID", style="dim white")
                for i, c in enumerate(merged, 1):
                    display = c.get("name") or "-"
                    phone_id = c.get("phone") or c.get("jid", "")
                    table.add_row(str(i), display, phone_id)
                table.add_row("0", "[dim]Type a new number[/]", "")
                console.print(table)
                raw = Prompt.ask("[bold cyan]Pick a contact or enter new number[/]", default="1")
            else:
                raw = Prompt.ask("[bold cyan]Phone number[/] (e.g. 919876543210, no +)")

            # Check if user picked a contact by index
            if raw.isdigit() and merged and 1 <= int(raw) <= len(merged):
                picked = merged[int(raw) - 1]
                phone = picked.get("phone", "")
                picked_jid = picked.get("jid", "")
                if not phone:
                    phone = picked_jid.split("@")[0] if "@" in picked_jid else ""
                    phone = "".join(ch for ch in phone if ch.isdigit())
                picked_name = picked.get("name", phone)
                console.print(f"[dim]Selected:[/] {picked_name} ({phone})")
            else:
                phone = raw.strip().replace("+", "").replace(" ", "").replace("-", "")
                picked_name = ""
                picked_jid = None

            if not phone.isdigit() or len(phone) < 7:
                console.print("[red]Invalid phone number. Enter 7-15 digits (e.g. 919876543210).[/]")
                phone = None
                continue

        _show_quick_messages()
        msg_choice = Prompt.ask(
            "[bold cyan]Pick a quick message or type '0' for custom[/]",
            default="0"
        )

        if msg_choice == "0":
            message = Prompt.ask("[bold cyan]Message[/]")
            if not message.strip():
                console.print("[red]Message cannot be empty.[/]")
                continue
        elif msg_choice in QUICK_MESSAGES:
            message = QUICK_MESSAGES[msg_choice]
            console.print(f"[dim]Selected:[/] {message}")
        else:
            console.print("[red]Invalid choice. Type '0' for custom message.[/]")
            continue

        console.print(f"[cyan]Sending to[/] {phone} ...")
        try:
            send_message(phone, message, uri=ws_url, jid=picked_jid)
            console.print(f"[green]Message sent to {phone}[/]")
            save_recent_contact(phone, name=picked_name)
        except Exception as e:
            console.print(f"[red]Failed to send message: {e}[/]")

        console.print()
        again = Prompt.ask(
            "[bold cyan]What next?[/] [dim]1=Undo, 2=New number, 3=Back to menu[/]",
            choices=["1", "2", "3"],
            default="3"
        )
        if again == "1":
            continue
        elif again == "2":
            phone = None
            continue
        else:
            break


def _show_quick_messages():
    """Display quick message options."""
    console.print()
    table = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
    table.add_column("Key", style="bold magenta", width=4)
    table.add_column("Message", style="bold white")
    table.add_row("1", "Hello!")
    table.add_row("2", "Thank you!")
    table.add_row("3", "On my way")
    table.add_row("4", "OK")
    table.add_row("5", "Call me later")
    table.add_row("6", "Good morning!")
    table.add_row("7", "Good night!")
    table.add_row("8", "Happy Birthday!")
    table.add_row("9", "See you soon")
    table.add_row("10", "Sorry, I'm busy right now")
    table.add_row("0", "[dim]Type your own message[/]")
    console.print(table)


def _show_skill_picker():
    """Display available AI skill/prompt templates."""
    from pywacli.ai_engine.skill_generator import SkillGenerator

    skills = SkillGenerator.get_all_skills()
    skill_labels = {
        "personal": "Personal Assistant",
        "sales": "Sales Assistant",
        "scheduler": "Scheduling Assistant",
        "customer_support": "Customer Support",
        "translator": "Translator",
        "summarizer": "Summarizer",
        "content_writer": "Content Writer",
        "lead_qualifier": "Lead Qualifier",
        "appointment_booking": "Appointment Booking",
        "order_tracking": "Order Tracking",
        "faq_bot": "FAQ Bot",
        "clone": "Conversation Clone",
    }

    console.print()
    table = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
    table.add_column("Key", style="bold magenta", width=4)
    table.add_column("Skill", style="bold white", width=22)
    table.add_column("Description", style="dim white")
    for i, (key, label) in enumerate(skill_labels.items(), 1):
        table.add_row(str(i), label, key)
    console.print(table)
    return list(skills.keys())


def _interactive_automate():
    """Auto-reply AI bot: monitors incoming messages and responds automatically."""
    import time
    import threading
    from pywacli.services.message_sender import send_message
    from pywacli.cli.config_manager import (
        load_config, load_recent_contacts, save_recent_contact,
        get_saved_provider, save_ai_provider, has_api_key,
    )
    from pywacli.ai_engine.factory import AIEngineFactory
    from pywacli.ai_engine.skill_generator import SkillGenerator
    from pywacli.db.retriver_db import get_messages_by_contact, get_new_messages_after, get_all_contacts

    config = load_config()
    ws_url = config.get("whatsapp", {}).get("websocket_url", "ws://localhost:3000")
    poll_interval = config.get("automate", {}).get("poll_interval", 3)

    # --- Step 1: Pick contact ---
    console.print()
    db_contacts = get_all_contacts()
    recent = load_recent_contacts()
    recent_phones = {c["phone"] for c in recent}

    # Merge: DB contacts first, then recent contacts not already in DB
    merged = []
    seen = set()
    for phone_num, push_name, jid in db_contacts:
        key = _contact_key(jid, phone_num)
        if key and key not in seen:
            merged.append({"phone": phone_num, "name": push_name, "jid": jid})
            seen.add(key)
    for c in recent:
        key = _contact_key(c.get("jid", ""), c.get("phone", ""))
        if key and key not in seen:
            merged.append({"phone": c["phone"], "name": c.get("name", ""), "jid": c.get("jid", "")})
            seen.add(key)

    merged = _sort_contacts(merged)

    phone = None

    if merged:
        table = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
        table.add_column("Key", style="bold magenta", width=4)
        table.add_column("Display", style="bold white", width=22)
        table.add_column("Phone / ID", style="dim white")
        for i, c in enumerate(merged, 1):
            display = c.get("name") or "-"
            phone_id = c.get("phone") or c.get("jid", "")
            table.add_row(str(i), display, phone_id)
        table.add_row("0", "[dim]Type a new number[/]", "")
        console.print(table)
        raw = Prompt.ask("[bold cyan]Pick a contact or enter new number[/]", default="1")
    else:
        raw = Prompt.ask("[bold cyan]Phone number or name[/] (e.g. 919876543210)")

    if raw == "0":
        phone = Prompt.ask("[bold cyan]Enter phone number[/] (e.g. 919876543210)")
        phone = phone.strip().replace("+", "").replace(" ", "").replace("-", "")
    elif raw.isdigit() and merged and 1 <= int(raw) <= len(merged):
        picked = merged[int(raw) - 1]
        phone = picked.get("phone") or picked.get("name") or picked.get("jid", "")
        console.print(f"[dim]Selected:[/] {picked.get('name') or phone} ({phone})")
    else:
        phone = raw.strip().replace("+", "").replace(" ", "").replace("-", "")

    if not phone:
        console.print("[red]Invalid selection.[/]")
        return

    # --- Step 2: Pick AI skill ---
    available_skills = _show_skill_picker()
    skill_choice = Prompt.ask(
        "[bold cyan]Pick a skill[/]",
        choices=[str(i) for i in range(1, len(available_skills) + 1)],
        default="1"
    )
    selected_skill = available_skills[int(skill_choice) - 1]
    skill_label = selected_skill.replace("_", " ").title()
    console.print(f"[dim]Skill:[/] {skill_label}")

    # --- Step 3: Pick provider ---
    provider_options = ["ollama", "openai", "gemini", "claude", "glm"]
    model_defaults = {
        "ollama": "llama3",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-2.0-flash",
        "claude": "claude-sonnet-4-20250514",
        "glm": "glm-4-plus",
    }

    saved = get_saved_provider()
    provider_name = None
    model_name = None

    if saved:
        sp = saved["provider"]
        sm = saved["model"]
        console.print()
        console.print(f"[dim]Saved provider:[/] {sp.title()} ({sm})")
        use_saved = Prompt.ask(
            "[bold cyan]Use saved provider?[/]",
            choices=["y", "n"],
            default="y"
        )
        if use_saved == "y":
            provider_name = sp
            model_name = sm

    if provider_name is None:
        console.print()
        for i, p in enumerate(provider_options, 1):
            console.print(f"  [bold magenta]{i}[/]  {p.title()}")
        provider_choice = Prompt.ask(
            "[bold cyan]Pick a provider[/]",
            choices=["1", "2", "3", "4", "5"],
            default="1"
        )
        provider_name = provider_options[int(provider_choice) - 1]

        model_name = Prompt.ask(
            "[bold cyan]Model name[/]",
            default=model_defaults.get(provider_name, "")
        )

        # --- Ask for API key if needed (non-ollama) ---
        if provider_name != "ollama" and not has_api_key(provider_name):
            console.print(f"[yellow]No API key found for {provider_name.title()}.[/]")
            api_key = Prompt.ask(
                f"[bold cyan]Enter {provider_name.title()} API key[/]",
                password=True
            )
            if api_key.strip():
                save_ai_provider(provider_name, model_name, api_key.strip())
                console.print(f"[green]API key saved for {provider_name.title()}.[/]")
            else:
                console.print("[red]No API key provided. Connection may fail.[/]")
        else:
            # Ollama or key already exists — just save the provider/model preference
            save_ai_provider(provider_name, model_name)

    # --- Step 4: Initialize AI ---
    try:
        ai_provider = AIEngineFactory().create(
            provider_name,
            model_name=model_name,
            temperature=0.7,
        )
        prompt_template = AIEngineFactory().create_prompt(selected_skill)
    except Exception as e:
        console.print(f"[red]Failed to initialize AI: {e}[/]")
        console.print("[yellow]Tip: Run `pywacli --setup` to configure API keys.[/]")
        return

    save_recent_contact(phone)

    # --- Step 5: Load existing conversation history ---
    existing_messages = get_messages_by_contact(phone, limit=200, include_sent=True)
    is_self_chat = existing_messages and not any(not msg[2] for msg in existing_messages)

    for msg in existing_messages:
        msg_id, text, from_me, push_name, p_number, timestamp, msg_jid = msg
        if text:
            if is_self_chat:
                # alternate roles so AI sees conversation flow
                ai_provider.history.add_user_message(text)
            elif from_me:
                ai_provider.history.add_ai_message(text)
            else:
                ai_provider.history.add_user_message(text)

    last_message_id = existing_messages[-1][0] if existing_messages else None
    # Get the real JID for sending replies
    contact_jid = existing_messages[-1][6] if existing_messages else None

    # --- Step 6: Show status and start monitoring ---
    console.print()
    mode_str = "Self-chat" if is_self_chat else "Auto-reply"
    console.print(Panel(
        f"[bold green]{mode_str} Bot Started[/]\n"
        f"[dim]Contact:[/] {phone}\n"
        f"[dim]Skill:[/] {skill_label}\n"
        f"[dim]Provider:[/] {provider_name.title()} ({model_name})\n"
        f"[dim]Polling every:[/] {poll_interval}s\n"
        f"[dim]Loaded {len(existing_messages)} previous messages[/]\n"
        f"[dim]Press Ctrl+C to stop[/]",
        box=ROUNDED, border_style="green"
    ))
    console.print()

    # Conversation display
    if existing_messages:
        console.print("[bold yellow]─── Previous Messages ───[/]")
        for msg in existing_messages[-5:]:
            _, text, from_me, push_name, _, _, _ = msg
            if text:
                if from_me:
                    console.print(f"  [bold blue]You:[/] {text}")
                else:
                    console.print(f"  [bold green]{push_name or phone}:[/] {text}")
        console.print("[bold yellow]─── Listening for new messages... ───[/]")
        console.print()

    # --- Step 7: Polling loop ---
    running = True
    _skip_echo = None

    def _stop_handler():
        nonlocal running
        try:
            while running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            running = False

    stop_thread = threading.Thread(target=_stop_handler, daemon=True)
    stop_thread.start()

    try:
        while running:
            time.sleep(poll_interval)
            if not running:
                break

            # Check for new messages
            new_msgs = get_new_messages_after(phone, last_message_id, include_sent=is_self_chat)

            for msg in new_msgs:
                if not running:
                    break
                msg_id, text, from_me, push_name, p_number, timestamp, msg_jid = msg
                if not text:
                    continue

                # Self-chat: skip echo of our own last response
                if is_self_chat:
                    if from_me and _skip_echo is not None and text.strip() == _skip_echo:
                        _skip_echo = None
                        last_message_id = msg_id
                        continue
                elif from_me:
                    continue

                # Use the real JID from the message for replies
                if msg_jid:
                    contact_jid = msg_jid

                # Display incoming message
                label = "You" if from_me else (push_name or phone)
                console.print(f"  [bold {'blue' if from_me else 'green'}]{label}:[/] {text}")

                # Generate AI response
                result = {"response": None, "error": None}

                def _gen(inp=text):
                    try:
                        result["response"] = ai_provider.generate(
                            prompt_template.prompt_template, inp
                        )
                    except Exception as e:
                        result["error"] = str(e)

                t = threading.Thread(target=_gen, daemon=True)
                t.start()
                with console.status("[bold cyan]AI thinking...[/]"):
                    t.join()

                if result["error"]:
                    console.print(f"  [red]AI Error: {result['error']}[/]")
                    last_message_id = msg_id
                    continue

                ai_reply = result["response"]
                console.print(f"  [bold blue]AI:[/] {ai_reply}")

                # Send to WhatsApp using the real JID
                try:
                    if contact_jid:
                        send_message(phone, ai_reply, uri=ws_url, jid=contact_jid)
                    else:
                        send_message(phone, ai_reply, uri=ws_url)
                    console.print(f"  [dim]Sent to {push_name or phone}[/]")
                    if is_self_chat:
                        _skip_echo = ai_reply.strip()
                except Exception as e:
                    console.print(f"  [red]Send failed: {e}[/]")

                last_message_id = msg_id

    except KeyboardInterrupt:
        pass
    finally:
        running = False
        console.print()
        console.print("[yellow]Auto-reply bot stopped.[/]")


def _show_menu():
    while True:
        console.clear()
        title = Panel(
            "[bold cyan]╔══════════════════════════════════════╗\n"
            "║       P Y W A C L I   M E N U       ║\n"
            "╚══════════════════════════════════════╝",
            box=ROUNDED, border_style="blue"
        )
        console.print(title)

        if _service_reachable():
            console.print("[bold green]● WhatsApp service running[/] [dim](Connect is live in another terminal)[/]")
        else:
            console.print("[dim]○ Not connected — run 4 (Connect) in a separate terminal[/]")

        table = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
        table.add_column("Key", style="bold magenta", width=6)
        table.add_column("Option", style="bold white", width=20)
        table.add_column("Description", style="dim white")
        table.add_row("1", "Dashboard", "Launch the WhatsApp dashboard")
        table.add_row("2", "Setup", "Run the interactive configuration wizard")
        table.add_row("3", "Config", "Open configuration menu")
        table.add_row("4", "Connect", "Connect WhatsApp (QR) — keep this terminal open")
        table.add_row("6", "Send", "Send a WhatsApp message")
        table.add_row("7", "Automate", "AI-powered automated chat")
        table.add_row("8", "Media", "Browse stored media")
        table.add_row("9", "Init", "Install Node.js (Baileys) dependencies")
        table.add_row("0", "Exit", "Exit the application")
        console.print(table)

        choice = Prompt.ask(
            "\n[bold cyan]Enter your choice[/]",
            choices=["0", "1", "2", "3", "4", "6", "7", "8", "9"],
            default="1"
        )

        if choice == "1":
            launch_dashboard()
        elif choice == "2":
            run_config_wizard()
        elif choice == "3":
            run_config_wizard()
        elif choice == "4":
            connect()
        elif choice == "6":
            _menu_send()
        elif choice == "7":
            _interactive_automate()
        elif choice == "8":
            run_media_viewer()
        elif choice == "9":
            init()
        elif choice == "0":
            console.print("[yellow]Exiting...[/]")
            break


if __name__ == "__main__":
    app()
