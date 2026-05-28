import sys
import typer
from cli.configuration import run_config_wizard
from cli.app import main as launch_dashboard

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

    launch_dashboard()


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


if __name__ == "__main__":
    app()
