import json
import os
from pathlib import Path
from typing import Any, Optional

CONFIG_DIR = Path.home() / ".pywacli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config_path() -> str:
    return str(CONFIG_FILE)


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
