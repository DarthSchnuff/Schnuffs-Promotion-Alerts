import json
import os
from pathlib import Path
from typing import Any, Dict

from core.paths import data


APP_NAME = "SchnuffsPromotionAlerts"


def _user_config_dir() -> Path:
    """
    Windows: %APPDATA%\\SchnuffsPromotionAlerts
    Sonst:   ~/.config/SchnuffsPromotionAlerts
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Fehler beim Laden von {path}: {e}")
    return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"Fehler beim Speichern von {path}: {e}")


def load_settings() -> Dict[str, Any]:
    """
    Lädt Settings:
    1) User-Config (wenn vorhanden)
    2) Fallback: gebundelte Defaults aus /data
    Streamer-Liste wird ebenfalls gemerged.
    """
    user_dir = _user_config_dir()
    user_settings_path = user_dir / "settings.json"
    user_streamers_path = user_dir / "streamers.json"

    default_settings_path = data("settings.json")
    default_streamers_path = data("streamers.json")

    # settings
    settings = _read_json(user_settings_path) or _read_json(default_settings_path) or {}

    # streamers (separat)
    streamers_data = _read_json(user_streamers_path) or _read_json(default_streamers_path) or {}
    settings["streamers"] = streamers_data.get("streamers", settings.get("streamers", []))

    return settings


def save_settings(data_dict: Dict[str, Any]) -> None:
    """
    Speichert NUR in User-Config (EXE-sicher).
    """
    user_dir = _user_config_dir()
    user_settings_path = user_dir / "settings.json"
    _write_json(user_settings_path, data_dict)


def save_streamers(streamers: list[str]) -> None:
    """
    Optional/empfohlen: streamers.json separat speichern,
    falls deine UI irgendwann streamers.json direkt pflegt.
    """
    user_dir = _user_config_dir()
    user_streamers_path = user_dir / "streamers.json"
    _write_json(user_streamers_path, {"streamers": streamers})

