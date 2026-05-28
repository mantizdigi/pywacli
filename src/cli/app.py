from cli.config_manager import config_exists
from cli.configuration import run_config_wizard
from cli.ui.dashboard import run_dashboard
from db.init_db import init_database


def main():
    if not config_exists():
        result = run_config_wizard()
        if result != "launch":
            return

    init_database()
    run_dashboard()
