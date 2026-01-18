import json
from pathlib import Path

# ===============================
# Fester Projektpfad
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "data" / "settings.json"
STREAMERS_PATH = BASE_DIR / "data" / "streamers.json"


def load_settings():
    """Lädt die Settings aus settings.json und streamers.json"""
    settings = {}

    # settings.json laden
    if CONFIG_PATH.exists():
        try:
            settings = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Fehler beim Laden der Settings: {e}")
            settings = {}

    # streamers.json laden
    if STREAMERS_PATH.exists():
        try:
            streamers_data = json.loads(STREAMERS_PATH.read_text(encoding="utf-8"))
            settings["streamers"] = streamers_data.get("streamers", [])
        except Exception as e:
            print(f"Fehler beim Laden der Streamerliste: {e}")
            settings["streamers"] = []

    return settings


def save_settings(data: dict):
    """Speichert Settings in settings.json"""
    try:
        CONFIG_PATH.parent.mkdir(exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"Fehler beim Speichern der Settings: {e}")
