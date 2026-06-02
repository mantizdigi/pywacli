import sys
import os
import shutil
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


@app.command()
def run():
    """Run baileys service and websocket service in separate terminals"""
    if shutil.which("node") is None:
        console.print("[red]Node.js was not found on PATH.[/] Install it, then run [bold]pywacli init[/].")
        raise typer.Exit(code=1)
    if not _node_modules_present():
        console.print("[yellow]Node dependencies not found. Run [bold]pywacli init[/] first.[/]")
        raise typer.Exit(code=1)

    baileys_js = _package_dir().joinpath("services", "baileys_service.js")
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0

    # Node service: cwd stays at the user's directory so ./auth and ./media
    # are created where the user expects them.
    subprocess.Popen(
        ["node", str(baileys_js)],
        creationflags=flags,
        cwd=os.getcwd(),
    )
    # Python websocket service: launched as a module so its `pywacli.*`
    # imports resolve regardless of where it lives on disk.
    subprocess.Popen(
        [sys.executable, "-m", "pywacli.services.websocket_services"],
        creationflags=flags,
        cwd=os.getcwd(),
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
    table.add_row("6", "Init", "Install Node.js (Baileys) dependencies")
    table.add_row("0", "Exit", "Exit the application")
    console.print(table)

    choice = Prompt.ask(
        "\n[bold cyan]Enter your choice[/]",
        choices=["0", "1", "2", "3", "4", "5", "6"],
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
    elif choice == "6":
        init()
    elif choice == "0":
        console.print("[yellow]Exiting...[/]")


if __name__ == "__main__":
    app()
