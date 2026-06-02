import json
import os
import logging
from pathlib import Path
from typing import Any, Optional

CONFIG_DIR = Path.home() / ".pywacli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config_path() -> str:
    return str(CONFIG_FILE)


def _resolve_path(p: str) -> str:
    """Expand ~ / env vars and make a relative path absolute (against cwd)."""
    p = os.path.expanduser(os.path.expandvars(p))
    if not os.path.isabs(p):
        p = os.path.abspath(p)
    return p


def _as_file_in_dir(resolved: str, raw: str, default_name: str) -> str:
    """If the configured path is a directory, place ``default_name`` inside it.

    Users commonly enter a data *folder* where a *file* is expected; opening a
    directory as a SQLite/log file fails. Detect that and append the filename.
    """
    if os.path.isdir(resolved) or raw.endswith(("/", "\\")):
        return os.path.join(resolved, default_name)
    return resolved


def get_db_path() -> str:
    """Resolved SQLite path from config['database']['path'].

    Falls back to ~/.pywacli/pywacli.db (a stable, cwd-independent default)
    when no path is configured. Parent directory is created if missing.
    """
    config = load_config()
    path = (config.get("database") or {}).get("path") or str(CONFIG_DIR / "pywacli.db")
    resolved = _as_file_in_dir(_resolve_path(path), path, "pywacli.db")
    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    return resolved


def get_log_file() -> str:
    """Resolved log file path from config['logging']['file']."""
    config = load_config()
    path = (config.get("logging") or {}).get("file") or str(CONFIG_DIR / "pywacli.log")
    return _as_file_in_dir(_resolve_path(path), path, "pywacli.log")


def get_log_level() -> str:
    config = load_config()
    return (config.get("logging") or {}).get("level", "INFO")


def setup_logging() -> None:
    """Attach a file handler (configured path) + console handler to the root logger.

    Without this, the configured logging.file was never written — only
    ``logging.basicConfig(level=INFO)`` ran, which logs to stderr only.
    """
    # The services print emoji status lines; on a Windows cp1252 console an
    # emoji print() raises UnicodeEncodeError and can kill the process. Force
    # UTF-8 on the standard streams so that can't happen.
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    log_file = get_log_file()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    level = getattr(logging, get_log_level().upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def load_config() -> dict:
    if not config_exists():
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, default=str)


def section_exists(section: str) -> bool:
    config = load_config()
    if section == "media_storage":
        return "media_storage" in config and bool(config["media_storage"].get("entries"))
    return section in config and bool(config[section])


def delete_section(section: str):
    config = load_config()
    if section == "media_storage":
        config["media_storage"]["entries"] = []
        if not any(config["media_storage"].values()):
            del config["media_storage"]
    else:
        config.pop(section, None)
    save_config(config)


def get_next_entry_id(entries: list) -> int:
    if not entries:
        return 1
    return max(e.get("id", 0) for e in entries) + 1


def add_media_entry(entry: dict):
    config = load_config()
    if "media_storage" not in config:
        config["media_storage"] = {"entries": []}
    if "entries" not in config["media_storage"]:
        config["media_storage"]["entries"] = []
    entry["id"] = get_next_entry_id(config["media_storage"]["entries"])
    config["media_storage"]["entries"].append(entry)
    save_config(config)


def update_media_entry(entry_id: int, updated: dict):
    config = load_config()
    for i, e in enumerate(config["media_storage"]["entries"]):
        if e.get("id") == entry_id:
            updated["id"] = entry_id
            config["media_storage"]["entries"][i] = updated
            break
    save_config(config)


def delete_media_entry(entry_id: int):
    config = load_config()
    config["media_storage"]["entries"] = [
        e for e in config["media_storage"]["entries"]
        if e.get("id") != entry_id
    ]
    save_config(config)


def get_default_config() -> dict:
    return {
        "whatsapp": {
            "websocket_url": "ws://localhost:3000",
            "auto_reconnect": True
        },
        "media_storage": {
            "entries": []
        },
        "database": {
            "path": "./pywacli.db"
        },
        "dashboard": {
            "refresh_interval_sec": 1,
            "theme": "default"
        },
        "logging": {
            "level": "INFO",
            "file": "./pywacli.log"
        }
    }
