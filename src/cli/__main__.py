import sys
import os
import subprocess
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from rich.prompt import Prompt
from src.cli.configuration import run_config_wizard
from src.cli.app import main as launch_dashboard
from src.cli.ui.media_viewer import run_media_viewer

console = Console()
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
def media():
    """Browse stored media files"""
    run_media_viewer()


@app.command()
def run():
    """Run baileys service and websocket service in separate terminals"""
    subprocess.Popen(
        ['node', './src/services/baileys_service.js'],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        cwd=os.getcwd()
    )
    subprocess.Popen(
        ['python', './src/services/websocket_service.py'],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        cwd=os.getcwd()
    )


def _show_menu():
    console.clear()
    title = Panel(
        "[bold cyan]╔══════════════════════════════════════╗\n"
        "║       P Y W A C L I   M E N U       ║\n"
        "╚══════════════════════════════════════╝",
        box=ROUNDED, border_style="blue"
    )
    console.print(title)

    table = Table(box=ROUNDED, show_header=False, border_style="cyan", padding=(0, 2))
    table.add_column("Key", style="bold magenta", width=6)
    table.add_column("Option", style="bold white", width=20)
    table.add_column("Description", style="dim white")
    table.add_row("1", "Dashboard", "Launch the WhatsApp dashboard")
    table.add_row("2", "Setup", "Run the interactive configuration wizard")
    table.add_row("3", "Config", "Open configuration menu")
    table.add_row("4", "Run", "Start baileys + websocket services")
    table.add_row("5", "Media", "Browse stored media")
    table.add_row("0", "Exit", "Exit the application")
    console.print(table)

    choice = Prompt.ask(
        "\n[bold cyan]Enter your choice[/]",
        choices=["0", "1", "2", "3", "4", "5"],
        default="1"
    )

    if choice == "1":
        launch_dashboard()
    elif choice == "2":
        run_config_wizard()
    elif choice == "3":
        run_config_wizard()
    elif choice == "4":
        run()
    elif choice == "5":
        run_media_viewer()
    elif choice == "0":
        console.print("[yellow]Exiting...[/]")


if __name__ == "__main__":
    app()
