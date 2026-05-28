import os
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.style import Style
from rich.columns import Columns
from rich.syntax import Syntax
from rich.align import Align
from rich.box import ROUNDED, HEAVY, DOUBLE, MINIMAL

from cli.config_manager import (
    load_config, save_config, config_exists,
    section_exists, delete_section,
    add_media_entry, update_media_entry, delete_media_entry,
    get_default_config, get_config_path
)

console = Console()

TITLE_STYLE = "bold white on blue"
HEADER_STYLE = "bold cyan"
LABEL_STYLE = "bold cyan"
VALUE_STYLE = "bold white"
SUCCESS_STYLE = "bold green"
WARN_STYLE = "bold yellow"
ERROR_STYLE = "bold red"
DIM_STYLE = "dim white"
ACCENT_STYLE = "bold magenta"
INFO_STYLE = "bold blue"

SECTIONS = ["whatsapp", "media_storage", "database", "dashboard", "logging"]
SECTION_LABELS = {
    "whatsapp": "WhatsApp Connection",
    "media_storage": "Media Storage",
    "database": "Database Settings",
    "dashboard": "Display & Dashboard",
    "logging": "Logging",
}


def print_header(title: str, subtitle: str = ""):
    console.clear()
    text = Text()
    text.append("  ╔═══════════════════════════════════════════════════════════╗  ", TITLE_STYLE)
    text.append("\n")
    text.append(f"  ║{title:^67}║  ", TITLE_STYLE)
    if subtitle:
        text.append("\n")
        text.append(f"  ║{subtitle:^67}║  ", DIM_STYLE)
    text.append("\n")
    text.append("  ╚═══════════════════════════════════════════════════════════╝  ", TITLE_STYLE)
    console.print(Panel(text, box=HEAVY, border_style="blue"))


def print_success(msg: str):
    console.print(f"  ✅ {msg}", style=SUCCESS_STYLE)


def print_warn(msg: str):
    console.print(f"  ⚠️  {msg}", style=WARN_STYLE)


def print_error(msg: str):
    console.print(f"  ❌ {msg}", style=ERROR_STYLE)


def print_info(msg: str):
    console.print(f"  ℹ️  {msg}", style=INFO_STYLE)


def show_section_status(section: str, config: dict) -> Text:
    exists = section_exists(section)
    label = SECTION_LABELS.get(section, section.replace("_", " ").title())

    text = Text()
    text.append("  ", style=DIM_STYLE)
    if exists:
        text.append("✅", style=SUCCESS_STYLE)
    else:
        text.append("❌", style=ERROR_STYLE)
    text.append(f"  {label}", style=LABEL_STYLE)
    if section == "media_storage" and exists:
        count = len(config.get("media_storage", {}).get("entries", []))
        text.append(f"  ({count} provider{'s' if count != 1 else ''})", style=ACCENT_STYLE)
    return text


def choose_option(prompt_text: str, valid: list, default: str = "") -> str:
    while True:
        choice = Prompt.ask(
            f"\n  {prompt_text}",
            default=default
        ).strip().lower()
        if not choice and default:
            return default
        if choice in valid:
            return choice
        console.print(f"  Invalid choice. Valid options: {', '.join(valid)}", style=ERROR_STYLE)


def confirm_action(msg: str, default: bool = True) -> bool:
    return Confirm.ask(f"\n  {msg}", default=default)


def make_divider(label: str = "") -> str:
    if label:
        return f"  ── {label} ──"
    return "  " + "─" * 50


def show_main_menu():
    config = load_config()

    print_header("PYWACLI CONFIGURATION")

    status_lines = []
    for s in SECTIONS:
        status_lines.append(show_section_status(s, config))

    console.print()
    console.print(Columns(status_lines, equal=True, expand=False))
    console.print()

    divider = Text("  ──" + "─" * 50 + "──", style=DIM_STYLE)
    console.print(divider)

    menu_table = Table(box=MINIMAL, show_header=False, padding=(0, 4))
    menu_table.add_column("Key", style=ACCENT_STYLE, width=8)
    menu_table.add_column("Action", style="white")
    menu_table.add_row("1", "WhatsApp Connection")
    menu_table.add_row("2", "Media Storage")
    menu_table.add_row("3", "Database Settings")
    menu_table.add_row("4", "Display & Dashboard")
    menu_table.add_row("5", "Logging")
    menu_table.add_row("")
    menu_table.add_row("6", "Save & Exit")
    menu_table.add_row("7", "Discard & Exit")

    console.print(Panel(menu_table, title="[bold cyan]Menu[/]", box=ROUNDED, border_style="cyan"))

    choice = choose_option("Enter choice [1-7]", [str(i) for i in range(1, 8)])
    return choice


def show_media_action_menu(entry: dict, entry_index: int, total: int):
    print_header(
        f"Media Storage — Entry #{entry['id']}",
        f"Entry {entry_index + 1} of {total}"
    )

    tbl = Table(box=MINIMAL, show_header=False, border_style="cyan")
    tbl.add_column("Field", style=LABEL_STYLE, width=22)
    tbl.add_column("Value", style=VALUE_STYLE)
    tbl.add_row("Store Images", "✅ Yes" if entry.get("store_image") else "❌ No")
    tbl.add_row("Store Videos", "✅ Yes" if entry.get("store_video") else "❌ No")
    tbl.add_row("Store Documents", "✅ Yes" if entry.get("store_document") else "❌ No")
    provider = entry.get("provider", "")
    provider_labels = {"s3": "AWS S3", "r2": "Cloudflare R2", "local": "Local Path"}
    tbl.add_row("Provider", provider_labels.get(provider, provider.upper()))
    if provider in ("s3", "r2"):
        tbl.add_row("Endpoint", entry.get("endpoint", ""))
        tbl.add_row("Access Key ID", entry.get("access_key_id", ""))
        tbl.add_row("Secret Key", "********")
        tbl.add_row("Region", entry.get("region", ""))
        tbl.add_row("Bucket", entry.get("bucket_name", ""))
    elif provider == "local":
        tbl.add_row("Local Path", entry.get("local_path", ""))

    console.print(Panel(tbl, box=ROUNDED, border_style="cyan"))
    console.print()

    menu_table = Table(box=MINIMAL, show_header=False, padding=(0, 4))
    menu_table.add_column("Key", style=ACCENT_STYLE, width=8)
    menu_table.add_column("Action", style="white")
    menu_table.add_row("1", "Reconfigure this entry")
    menu_table.add_row("2", "Delete this entry")
    menu_table.add_row("3", "Add new entry")
    menu_table.add_row("4", "Back to main menu")

    console.print(Panel(menu_table, title="[bold cyan]Actions[/]", box=ROUNDED, border_style="cyan"))
    choice = choose_option("Enter choice [1-4]", ["1", "2", "3", "4"])
    return choice


def configure_whatsapp():
    config = load_config()
    current = config.get("whatsapp", {})
    print_header("WhatsApp Connection", "Configure WebSocket connection settings")

    console.print(Panel(
        "[dim]Enter values or press ENTER to keep current (shown in brackets)[/]",
        box=ROUNDED, border_style="blue"
    ))
    console.print()

    url = Prompt.ask(
        "  WebSocket URL",
        default=current.get("websocket_url", "ws://localhost:3000")
    )

    reconnect = Confirm.ask(
        "  Auto-reconnect on disconnect?",
        default=current.get("auto_reconnect", True)
    )

    config["whatsapp"] = {
        "websocket_url": url,
        "auto_reconnect": reconnect
    }
    save_config(config)
    print_success("WhatsApp connection configured successfully!")


def configure_media_entry(existing: dict = None) -> dict:
    is_new = existing is None
    entry = dict(existing) if existing else {}

    print_header("Media Storage", "Configure what media to store and where")

    console.print(Panel(
        "[dim]Select which media types to store[/]",
        box=ROUNDED, border_style="blue"
    ))
    console.print()

    entry["store_image"] = Confirm.ask(
        "  Store images?", default=entry.get("store_image", False)
    )
    entry["store_video"] = Confirm.ask(
        "  Store videos?", default=entry.get("store_video", False)
    )
    entry["store_document"] = Confirm.ask(
        "  Store documents?", default=entry.get("store_document", False)
    )

    if not any([entry["store_image"], entry["store_video"], entry["store_document"]]):
        print_warn("No media types selected. Storage entry will be created but nothing will be stored.")
        if not confirm_action("Continue with no media types selected?", default=False):
            return None

    console.print()
    console.print("[bold cyan]  Storage Provider:[/]")
    provider_table = Table(box=MINIMAL, show_header=False, padding=(0, 4))
    provider_table.add_column("Key", style=ACCENT_STYLE, width=8)
    provider_table.add_column("Provider", style="white")
    provider_table.add_column("Description", style=DIM_STYLE)
    provider_table.add_row("1", "AWS S3", "Amazon Simple Storage Service")
    provider_table.add_row("2", "Cloudflare R2", "S3-compatible, no egress fees")
    provider_table.add_row("3", "Local Path", "Store on local filesystem")
    console.print(Panel(provider_table, box=ROUNDED, border_style="cyan"))

    current_provider = entry.get("provider", "")
    provider_map = {"1": "s3", "2": "r2", "3": "local"}
    default_key = "1"
    for k, v in provider_map.items():
        if v == current_provider:
            default_key = k
            break

    prov_choice = choose_option(
        "Enter choice [1-3]",
        ["1", "2", "3"],
        default=default_key
    )
    entry["provider"] = provider_map[prov_choice]

    console.print()
    if entry["provider"] in ("s3", "r2"):
        provider_name = "AWS S3" if entry["provider"] == "s3" else "Cloudflare R2"
        console.print(Panel(
            f"[bold cyan]{provider_name} Configuration[/]",
            box=HEAVY, border_style="cyan"
        ))

        if entry["provider"] == "s3":
            default_endpoint = entry.get("endpoint", "http://localhost:4566")
        else:
            default_endpoint = entry.get("endpoint", "https://<account>.r2.cloudflarestorage.com")

        entry["endpoint"] = Prompt.ask("  Endpoint URL", default=default_endpoint)
        entry["access_key_id"] = Prompt.ask("  Access Key ID", default=entry.get("access_key_id", ""))
        entry["secret_access_key"] = Prompt.ask(
            "  Secret Access Key",
            default=entry.get("secret_access_key", ""),
            password=True
        )
        entry["region"] = Prompt.ask("  Region", default=entry.get("region", "us-east-1"))
        entry["bucket_name"] = Prompt.ask("  Bucket Name", default=entry.get("bucket_name", "whatsapp-media"))
        entry["local_path"] = None

    else:
        console.print(Panel(
            "[bold cyan]Local Storage Configuration[/]",
            box=HEAVY, border_style="cyan"
        ))
        entry["local_path"] = Prompt.ask(
            "  Storage directory path",
            default=entry.get("local_path", "./media")
        )
        entry["endpoint"] = None
        entry["access_key_id"] = None
        entry["secret_access_key"] = None
        entry["region"] = None
        entry["bucket_name"] = None

    return entry


def configure_media_section():
    config = load_config()
    entries = config.get("media_storage", {}).get("entries", [])

    if entries:
        current_idx = 0
        while True:
            entry = entries[current_idx]
            choice = show_media_action_menu(entry, current_idx, len(entries))

            if choice == "1":
                result = configure_media_entry(existing=entry)
                if result is not None:
                    update_media_entry(entry["id"], result)
                    entries = load_config().get("media_storage", {}).get("entries", [])
                    print_success(f"Entry #{entry['id']} updated!")
                    Prompt.ask("\n  Press ENTER to continue", default="")

            elif choice == "2":
                if confirm_action(f"Delete entry #{entry['id']}? This cannot be undone.", default=False):
                    delete_media_entry(entry["id"])
                    entries = load_config().get("media_storage", {}).get("entries", [])
                    print_success(f"Entry #{entry['id']} deleted.")
                    if not entries:
                        print_info("No media entries remaining.")
                        Prompt.ask("\n  Press ENTER to continue", default="")
                        return
                    current_idx = min(current_idx, len(entries) - 1)
                else:
                    print_info("Deletion cancelled.")

            elif choice == "3":
                result = configure_media_entry()
                if result is not None:
                    add_media_entry(result)
                    entries = load_config().get("media_storage", {}).get("entries", [])
                    current_idx = len(entries) - 1
                    print_success(f"Entry #{result['id']} added!")
                else:
                    print_info("Entry creation cancelled.")
                Prompt.ask("\n  Press ENTER to continue", default="")

            elif choice == "4":
                return

    else:
        print_header("Media Storage", "No entries configured yet")
        console.print()
        print_info("No media storage entries found.")
        if confirm_action("Would you like to add a new media storage entry?", default=True):
            result = configure_media_entry()
            if result is not None:
                add_media_entry(result)
                print_success(f"Media storage entry #{result['id']} added successfully!")
            else:
                print_info("Entry creation cancelled.")
        Prompt.ask("\n  Press ENTER to continue", default="")


def configure_database():
    config = load_config()
    current = config.get("database", {})
    print_header("Database Settings", "Configure SQLite database path")

    path = Prompt.ask(
        "  Database file path",
        default=current.get("path", "./pywacli.db")
    )

    config["database"] = {"path": path}
    save_config(config)
    print_success(f"Database path set to: {path}")


def configure_dashboard():
    config = load_config()
    current = config.get("dashboard", {})
    print_header("Display & Dashboard", "Configure refresh rate and theme")

    refresh = Prompt.ask(
        "  Refresh interval (seconds)",
        default=str(current.get("refresh_interval_sec", 1))
    )
    try:
        refresh = int(refresh)
    except ValueError:
        refresh = 1
        print_warn("Invalid number, using default: 1")

    theme_table = Table(box=MINIMAL, show_header=False, padding=(0, 4))
    theme_table.add_column("Key", style=ACCENT_STYLE, width=8)
    theme_table.add_column("Theme", style="white")
    theme_table.add_row("1", "default")
    theme_table.add_row("2", "dark")
    theme_table.add_row("3", "light")
    console.print(Panel(theme_table, title="[bold cyan]Theme[/]", box=ROUNDED, border_style="cyan"))

    theme_map = {"1": "default", "2": "dark", "3": "light"}
    current_theme = current.get("theme", "default")
    default_key = "1"
    for k, v in theme_map.items():
        if v == current_theme:
            default_key = k
            break

    theme_choice = choose_option(
        "  Enter choice [1-3]",
        ["1", "2", "3"],
        default=default_key
    )
    theme = theme_map[theme_choice]

    config["dashboard"] = {
        "refresh_interval_sec": refresh,
        "theme": theme
    }
    save_config(config)
    print_success(f"Dashboard configured — refresh: {refresh}s, theme: {theme}")


def configure_logging():
    config = load_config()
    current = config.get("logging", {})
    print_header("Logging", "Configure log level and output file")

    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    level_table = Table(box=MINIMAL, show_header=False, padding=(0, 4))
    level_table.add_column("Key", style=ACCENT_STYLE, width=8)
    level_table.add_column("Level", style="white")
    for i, lvl in enumerate(levels, 1):
        level_table.add_row(str(i), lvl)
    console.print(Panel(level_table, title="[bold cyan]Log Level[/]", box=ROUNDED, border_style="cyan"))

    current_level = current.get("level", "INFO")
    default_key = str(levels.index(current_level) + 1) if current_level in levels else "2"
    lvl_choice = choose_option(
        "  Enter choice [1-5]",
        [str(i) for i in range(1, 6)],
        default=default_key
    )
    level = levels[int(lvl_choice) - 1]

    log_file = Prompt.ask(
        "  Log file path",
        default=current.get("file", "./pywacli.log")
    )

    config["logging"] = {"level": level, "file": log_file}
    save_config(config)
    print_success(f"Logging configured — level: {level}, file: {log_file}")


def show_summary():
    config = load_config()
    print_header("Configuration Summary")

    summary_table = Table(box=HEAVY, border_style="blue", show_edge=False)
    summary_table.add_column("Section", style=LABEL_STYLE, width=22)
    summary_table.add_column("Status", style="white")

    for s in SECTIONS:
        exists = section_exists(s)
        label = SECTION_LABELS.get(s, s.replace("_", " ").title())
        if s == "media_storage" and exists:
            entries = config.get("media_storage", {}).get("entries", [])
            status_text = Text()
            status_text.append("✅  ", style=SUCCESS_STYLE)
            status_text.append(f"{len(entries)} provider(s)", style=VALUE_STYLE)
            for e in entries:
                prov = e.get("provider", "")
                prov_label = {"s3": "S3", "r2": "R2", "local": "Local"}.get(prov, prov)
                types = []
                if e.get("store_image"): types.append("📷")
                if e.get("store_video"): types.append("🎬")
                if e.get("store_document"): types.append("📄")
                status_text.append(f"\n      #{e['id']} {prov_label} {' '.join(types)}", style=DIM_STYLE)
            summary_table.add_row(label, status_text)
        elif exists:
            summary_table.add_row(label, f"✅  Configured")
        else:
            summary_table.add_row(label, "❌  Not configured")

    console.print(Panel(summary_table, box=ROUNDED, border_style="cyan"))
    console.print()

    action_table = Table(box=MINIMAL, show_header=False, padding=(0, 4))
    action_table.add_column("Key", style=ACCENT_STYLE, width=8)
    action_table.add_column("Action", style="white")
    action_table.add_row("1", "Edit Section")
    action_table.add_row("2", "Export Config (view JSON)")
    action_table.add_row("3", "Save & Exit")
    action_table.add_row("4", "Save & Launch Dashboard")

    console.print(Panel(action_table, title="[bold cyan]Actions[/]", box=ROUNDED, border_style="cyan"))
    choice = choose_option("Enter choice [1-4]", ["1", "2", "3", "4"])
    return choice


def show_config_export():
    config = load_config()
    print_header("Configuration JSON")

    json_str = json.dumps(config, indent=2, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, box=HEAVY, border_style="blue"))
    console.print(f"\n  [dim]Saved to: {get_config_path()}[/]")
    Prompt.ask("\n  Press ENTER to go back", default="")


def run_config_main_menu():
    while True:
        choice = show_main_menu()

        if choice == "1":
            configure_whatsapp()
            Prompt.ask("\n  Press ENTER to continue", default="")
        elif choice == "2":
            configure_media_section()
        elif choice == "3":
            configure_database()
            Prompt.ask("\n  Press ENTER to continue", default="")
        elif choice == "4":
            configure_dashboard()
            Prompt.ask("\n  Press ENTER to continue", default="")
        elif choice == "5":
            configure_logging()
            Prompt.ask("\n  Press ENTER to continue", default="")
        elif choice == "6":
            print_success("Configuration saved. Exiting.")
            return "exit"
        elif choice == "7":
            if confirm_action("Discard all changes and exit?", default=False):
                print_info("Exiting without saving.")
                return "exit"


def run_full_setup():
    print_header(
        "PYWACLI SETUP WIZARD",
        "First-time configuration"
    )

    welcome = Panel(
        Text(
            "\n"
            "  Welcome to PyWacli — Python WhatsApp CLI!\n\n"
            "  This wizard will help you configure your environment.\n"
            "  You can reconfigure any section later from the main menu.\n",
            style="white"
        ),
        box=ROUNDED,
        border_style="cyan"
    )
    console.print(welcome)
    console.print()

    if not confirm_action("Begin setup?", default=True):
        print_info("Setup cancelled.")
        return "exit"

    configure_whatsapp()
    Prompt.ask("\n  Press ENTER to continue", default="")
    configure_media_section()
    configure_database()
    Prompt.ask("\n  Press ENTER to continue", default="")
    configure_dashboard()
    Prompt.ask("\n  Press ENTER to continue", default="")
    configure_logging()
    Prompt.ask("\n  Press ENTER to continue", default="")

    print_header("Setup Complete!")
    print_success("All sections configured successfully!")
    console.print()

    while True:
        choice = show_summary()
        if choice == "1":
            run_config_main_menu()
            break
        elif choice == "2":
            show_config_export()
        elif choice == "3":
            print_success("Configuration saved. Exiting.")
            return "exit"
        elif choice == "4":
            print_success("Configuration saved. Launching dashboard...")
            return "launch"

    return "exit"


def run_config_wizard() -> str:
    if not config_exists():
        return run_full_setup()
    else:
        while True:
            choice = show_summary()
            if choice == "1":
                run_config_main_menu()
                break
            elif choice == "2":
                show_config_export()
            elif choice == "3":
                print_success("Exiting.")
                return "exit"
            elif choice == "4":
                print_success("Launching dashboard...")
                return "launch"
        return "exit"
