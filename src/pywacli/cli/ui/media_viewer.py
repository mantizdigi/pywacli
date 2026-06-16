import os
import shutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED, HEAVY, MINIMAL
from rich.prompt import Prompt
from datetime import datetime, timezone

from pywacli.db.retriver_db import get_media_types, get_media_by_type, get_media_by_id
from pywacli.cli.config_manager import load_config
from pywacli.utils.bucket_utils import download_file_from_s3

console = Console()


def _format_media_table(rows):
    table = Table(box=ROUNDED, border_style="cyan", header_style="bold cyan")
    table.add_column("ID", style="bold magenta", width=5)
    table.add_column("Type", width=10)
    table.add_column("Filename", width=30)
    table.add_column("Sender", width=20)
    table.add_column("Time", width=16)
    table.add_column("Sync", width=6)

    for row in rows:
        media_id, media_type, file_name, push_name, from_me, timestamp, file_path, sync = row
        try:
            if timestamp and timestamp > 1e10:
                timestamp = timestamp / 1000
            ts = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if timestamp else "N/A"
        except (OSError, ValueError, OverflowError, TypeError):
            ts = "N/A"
        sync_str = "✅" if sync == 1 else "❌" if sync == 0 else "—"
        table.add_row(
            str(media_id),
            media_type or "—",
            file_name or "—",
            push_name or "—",
            ts,
            sync_str
        )
    return table


def _show_media_list(media_type_label, rows):
    console.clear()
    console.print(Panel(
        f"[bold cyan]Media — {media_type_label}[/]",
        box=HEAVY, border_style="blue"
    ))

    if not rows:
        console.print("\n[dim]No media found.[/]")
        Prompt.ask("\nPress ENTER to go back", default="")
        return None

    table = _format_media_table(rows)
    console.print(table)

    ids = [str(r[0]) for r in rows]
    choice = Prompt.ask(
        "\n[bold cyan]Enter media ID to view details, or B to go back[/]",
        default="B"
    )
    if choice.upper() == "B":
        return None
    if choice in ids:
        return int(choice)
    console.print("[red]Invalid selection.[/]")
    Prompt.ask("Press ENTER to continue", default="")
    return _show_media_list(media_type_label, rows)


def _show_media_detail(media_id):
    row = get_media_by_id(media_id)
    if not row:
        console.print("[red]Media not found.[/]")
        Prompt.ask("Press ENTER to go back", default="")
        return

    (mid, media_type, file_name, push_name, from_me,
     timestamp, file_path, mime_type, sync, failure_reason) = row

    try:
        if timestamp and timestamp > 1e10:
            timestamp = timestamp / 1000
        ts = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if timestamp else "N/A"
    except (OSError, ValueError, OverflowError, TypeError):
        ts = "N/A"
    sync_str = "✅ Synced" if sync == 1 else f"❌ Failed ({failure_reason or 'Unknown'})" if sync == 0 else "— Pending"

    console.clear()
    console.print(Panel(
        f"[bold cyan]Media Details — ID #{mid}[/]",
        box=HEAVY, border_style="blue"
    ))

    detail = Table(box=MINIMAL, show_header=False, border_style="cyan")
    detail.add_column("Field", style="bold cyan", width=16)
    detail.add_column("Value", style="white")
    detail.add_row("ID", str(mid))
    detail.add_row("Type", media_type or "—")
    detail.add_row("Filename", file_name or "—")
    detail.add_row("MIME Type", mime_type or "—")
    detail.add_row("Sender", push_name or "—")
    detail.add_row("From Me", "Yes" if from_me else "No")
    detail.add_row("Timestamp", ts)
    detail.add_row("Original Path", file_path or "—")
    detail.add_row("Sync Status", sync_str)
    console.print(Panel(detail, box=ROUNDED, border_style="cyan"))

    console.print()
    menu = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
    menu.add_column("Key", style="bold magenta", width=6)
    menu.add_column("Action", style="white")
    menu.add_row("D", "Download file")
    menu.add_row("B", "Back to list")
    console.print(Panel(menu, title="[bold cyan]Actions[/]", box=ROUNDED, border_style="cyan"))

    choice = Prompt.ask("\n[bold cyan]Your choice[/]", default="B").upper()
    if choice == "D":
        _download_media(mid, media_type, file_name)
        _show_media_detail(media_id)
    elif choice == "B":
        return


def _download_media(media_id, media_type, file_name):
    dest = Prompt.ask("[bold cyan]Download destination directory[/]", default=".")
    dest_dir = os.path.abspath(dest)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file_name or f"media_{media_id}")

    config = load_config()
    entries = config.get("media_storage", {}).get("entries", [])

    storage_options = []

    for entry in entries:
        provider = entry.get("provider")
        type_field = f"store_{media_type}"
        if not entry.get(type_field, False):
            continue

        if provider in ("s3", "r2", "b2"):
            bucket = entry.get("bucket_name")
            object_key = f"{media_type}/{file_name}" if file_name else None
            if bucket and object_key:
                storage_options.append(("s3", {
                    "bucket": bucket,
                    "key": object_key,
                    "entry": entry
                }))

        elif provider == "local":
            src = os.path.join(
                entry.get("local_path", "./media"), media_type or "", file_name or ""
            )
            storage_options.append(("local", {"path": src}))

    if not storage_options:
        console.print("[yellow]⚠ No storage entry configured for this media type.[/]")
        Prompt.ask("\nPress ENTER to continue", default="")
        return

    for kind, opts in storage_options:
        if kind == "s3":
            s3url = f"s3://{opts['bucket']}/{opts['key']}"
            console.print(f"[dim]Trying {s3url}...[/]")
            success = download_file_from_s3(
                file_path=dest_path,
                object_name=opts["key"],
                bucket_name=opts["bucket"],
                entry=opts["entry"]
            )
            if success:
                console.print(f"[green]✅ Downloaded to {dest_path}[/]")
                Prompt.ask("\nPress ENTER to continue", default="")
                return

        elif kind == "local":
            console.print(f"[dim]Trying {opts['path']}...[/]")
            if os.path.exists(opts["path"]):
                try:
                    shutil.copy2(opts["path"], dest_path)
                    console.print(f"[green]✅ Copied to {dest_path}[/]")
                    Prompt.ask("\nPress ENTER to continue", default="")
                    return
                except Exception as e:
                    console.print(f"[red]❌ Copy failed: {e}[/]")
            else:
                console.print(f"[yellow]⚠ Not found at: {opts['path']}[/]")

    console.print("[red]❌ File not found in any configured storage.[/]")
    Prompt.ask("\nPress ENTER to continue", default="")


def run_media_viewer():
    while True:
        console.clear()
        console.print(Panel(
            "[bold cyan]╔════════════════════════════╗\n"
            "║      M E D I A   V I E W E R    ║\n"
            "╚════════════════════════════╝",
            box=HEAVY, border_style="blue"
        ))

        menu = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
        menu.add_column("Key", style="bold magenta", width=6)
        menu.add_column("Option", style="bold white", width=20)
        menu.add_column("Count", style="dim white")

        from pywacli.db.retriver_db import get_total_media
        total = get_total_media()
        menu.add_row("1", "Images", "")
        menu.add_row("2", "Videos", "")
        menu.add_row("3", "Documents", "")
        menu.add_row("4", "All Media", str(total))
        menu.add_row("", "")
        menu.add_row("0", "Back", "")
        console.print(Panel(menu, title="[bold cyan]Select Media Type[/]", box=ROUNDED, border_style="cyan"))

        choice = Prompt.ask(
            "\n[bold cyan]Your choice[/]",
            choices=["0", "1", "2", "3", "4"],
            default="1"
        )

        type_map = {"1": "image", "2": "video", "3": "document", "4": None}
        label_map = {"1": "Images", "2": "Videos", "3": "Documents", "4": "All Media"}

        if choice == "0":
            break

        media_type = type_map[choice]
        label = label_map[choice]

        rows = get_media_by_type(media_type=media_type, limit=50)
        selected = _show_media_list(label, rows)
        if selected:
            _show_media_detail(selected)
