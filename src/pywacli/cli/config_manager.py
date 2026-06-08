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


RECENT_CONTACTS_FILE = CONFIG_DIR / "recent_contacts.json"


def save_recent_contact(phone: str, name: str = ""):
    """Save a phone number to recent contacts (most recent first, max 20)."""
    contacts = load_recent_contacts()
    contacts = [c for c in contacts if c["phone"] != phone]
    contacts.insert(0, {"phone": phone, "name": name})
    contacts = contacts[:20]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(RECENT_CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2)


def load_recent_contacts() -> list:
    """Load recent contacts from file."""
    if not RECENT_CONTACTS_FILE.exists():
        return []
    try:
        with open(RECENT_CONTACTS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def load_ai_provider_keys():
    """Load AI provider API keys from config and set as environment variables.
    Returns the ai_providers config dict."""
    config = load_config()
    ai_config = config.get("ai_providers", {})

    key_map = {
        "openai_api_key": "OPENAI_API_KEY",
        "google_api_key": "GOOGLE_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "zhipuai_api_key": "ZHIPUAI_API_KEY",
    }

    for config_key, env_var in key_map.items():
        value = ai_config.get(config_key, "")
        if value:
            os.environ[env_var] = value

    return ai_config


def has_api_key(provider: str) -> bool:
    """Check if a provider has a saved API key in config."""
    config = load_config()
    ai_config = config.get("ai_providers", {})
    key_map = {
        "openai": "openai_api_key",
        "gemini": "google_api_key",
        "claude": "anthropic_api_key",
        "glm": "zhipuai_api_key",
    }
    config_key = key_map.get(provider)
    if not config_key:
        return True  # ollama needs no key
    return bool(ai_config.get(config_key, "").strip())


def get_saved_provider() -> dict | None:
    """Return saved provider/model if a valid key exists, else None."""
    config = load_config()
    ai_config = config.get("ai_providers", {})
    provider = ai_config.get("default_provider", "")
    model = ai_config.get("default_model", "")
    if provider and has_api_key(provider):
        return {"provider": provider, "model": model}
    return None


def save_ai_provider(provider: str, model: str, api_key: str = ""):
    """Save AI provider settings and optionally its API key."""
    config = load_config()
    if "ai_providers" not in config:
        config["ai_providers"] = {}
    ai = config["ai_providers"]
    ai["default_provider"] = provider
    ai["default_model"] = model
    key_map = {
        "openai": "openai_api_key",
        "gemini": "google_api_key",
        "claude": "anthropic_api_key",
        "glm": "zhipuai_api_key",
    }
    config_key = key_map.get(provider)
    if config_key and api_key:
        ai[config_key] = api_key
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
        },
        "ai_providers": {
            "openai_api_key": "",
            "google_api_key": "",
            "anthropic_api_key": "",
            "default_provider": "ollama",
            "default_model": "llama3"
        }
    }
