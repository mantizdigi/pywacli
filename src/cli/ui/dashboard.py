from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY, ROUNDED
from rich.align import Align
import time

from src.db.retriver_db import (
    get_total_messages,
    get_total_statuses,
    get_total_reactions,
    get_total_media,
    get_recent_messages
)
from src.cli.config_manager import load_config

console = Console()

HEADER_STYLE = "bold white on blue"
SUCCESS_STYLE = "bold green"
ACCENT_STYLE = "bold magenta"
INFO_STYLE = "bold blue"
DIM_STYLE = "dim white"

THEMES = {
    "default": {
        "header": "bold white on blue",
        "stat_title": "bold cyan",
        "stat_border": "blue",
        "feed_border": "cyan",
        "footer": "bold white on red",
        "body_bg": "",
    },
    "dark": {
        "header": "bold green on black",
        "stat_title": "bold green",
        "stat_border": "green",
        "feed_border": "green",
        "footer": "bold yellow on black",
        "body_bg": "black",
    },
    "light": {
        "header": "bold black on white",
        "stat_title": "bold blue",
        "stat_border": "blue",
        "feed_border": "blue",
        "footer": "bold white on red",
        "body_bg": "white",
    },
}


def get_theme():
    config = load_config()
    theme_name = config.get("dashboard", {}).get("theme", "default")
    return THEMES.get(theme_name, THEMES["default"])


def create_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    return layout


def make_header(theme):
    title = Text()
    title.append("╔", style=theme["header"])
    title.append("═" * 70, style=theme["header"])
    title.append("╗", style=theme["header"])
    title.append("\n")
    title.append("║", style=theme["header"])
    title.append("  📱  P Y W A C L I   D A S H B O A R D  ", style=theme["header"])
    title.append(" " * 15, style=theme["header"])
    title.append("║", style=theme["header"])
    title.append("\n")
    title.append("╚", style=theme["header"])
    title.append("═" * 70, style=theme["header"])
    title.append("╝", style=theme["header"])
    return Panel(title, style=theme["header"], box=HEAVY)


def make_footer(theme):
    return Panel(
        Align.center(" 📱  Press CTRL+C to exit  📱 "),
        style=theme["footer"],
        box=HEAVY
    )


def make_stats(theme):
    total_messages = get_total_messages()
    total_statuses = get_total_statuses()
    total_reactions = get_total_reactions()
    total_media = get_total_media()

    table = Table(
        title="[bold]📊 Database Stats[/]",
        title_style=theme["stat_title"],
        border_style=theme["stat_border"],
        box=ROUNDED,
        show_edge=True,
    )
    table.add_column("📌 Type", style="bold cyan", width=20)
    table.add_column("🔢 Count", style="bold magenta", justify="center", width=10)

    table.add_row("💬 Messages", str(total_messages))
    table.add_row("📋 Statuses", str(total_statuses))
    table.add_row("❤️ Reactions", str(total_reactions))
    table.add_row("🖼️ Media", str(total_media))

    return Panel(
        Align.center(table),
        border_style=theme["stat_border"],
        box=HEAVY,
    )


def make_live_feed(theme):
    recent = get_recent_messages()
    lines = []
    for push_name, text in recent:
        lines.append(f"  💬 [bold cyan]{push_name}[/]: [white]{text}[/]")

    if not lines:
        lines.append("  [dim]No messages yet...[/]")

    feed = "\n".join(lines)
    return Panel(
        Align.left(feed),
        title="[bold]📨 Recent Messages[/]",
        title_align="left",
        border_style=theme["feed_border"],
        box=ROUNDED,
    )


def run_dashboard():
    theme = get_theme()
    config = load_config()
    refresh_interval = config.get("dashboard", {}).get("refresh_interval_sec", 1)

    layout = create_layout()

    with Live(layout, refresh_per_second=2):
        while True:
            layout["header"].update(make_header(theme))
            layout["left"].update(make_stats(theme))
            layout["right"].update(make_live_feed(theme))
            layout["footer"].update(make_footer(theme))
            time.sleep(refresh_interval)
