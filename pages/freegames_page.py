# pages/freegames_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QSizePolicy, QAbstractItemView
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer

from io import BytesIO
import requests
from datetime import datetime
import threading
import time
import logging
import json
from typing import List, Dict

from core.config import load_settings
from core.paths import data  # ✅ EXE-sicherer data()-Pfad

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FreeGame:
    def __init__(self, data_: dict):
        self.id = data_.get('id', 0)
        self.title = data_.get('title', 'Unknown')
        self.description = data_.get('description', '')
        self.thumbnail = data_.get('thumbnail', '')
        self.open_giveaway_url = data_.get('open_giveaway_url', '')
        self.end_date = data_.get('end_date', 'N/A')
        self.worth = data_.get('worth', 'N/A')
        self.store = self._determine_store(data_.get('platforms', ''))

    def _determine_store(self, platforms: str) -> str:
        p = platforms.lower()
        if 'epic' in p: return 'Epic Games'
        if 'steam' in p: return 'Steam'
        if 'gog' in p: return 'GOG'
        if 'ubisoft' in p: return 'Ubisoft'
        if 'origin' in p or 'ea' in p: return 'EA'
        if 'amazon' in p: return 'Amazon Prime Gaming'
        return 'PC'

    def is_expired(self) -> bool:
        if self.end_date == 'N/A':
            return False
        try:
            end = datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
            return datetime.now() > end
        except Exception:
            return False


class GamerPowerAPI:
    BASE_URL = "https://www.gamerpower.com/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'SchnuffsPromotionAlerts/1.1.0'})

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    def get_by_platform(self, platform: str) -> List[FreeGame]:
        try:
            url = f"{self.BASE_URL}/giveaways"
            params = {'platform': platform, 'type': 'game'}
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data_ = resp.json()
            return [FreeGame(item) for item in data_]
        except Exception as e:
            logger.error(f"Fehler bei {platform}: {e}")
            return []


class SchnuffsFreegamesIntegration:
    def __init__(self, settings: dict):
        self.settings = settings
        self.cache_file = data("freegames_cache.json")

        self.seen_games: Dict[str, str] = {}

        self.monitored_stores = settings.get('enabled_stores', [
            'epic-games-store', 'steam', 'gog', 'ubisoft', 'origin', 'pc'
        ])
        self.refresh_interval = settings.get('check_interval_hours', 6) * 60 * 60
        self.running = False
        self.refresh_thread = None
        self.api = GamerPowerAPI()

        self.discord_webhook_url = settings.get('discord_webhook_url', '')

        self._load_cache()

    def _load_cache(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.seen_games = {str(k): str(v) for k, v in loaded.items()}
        except Exception:
            self.seen_games = {}

    def _save_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.seen_games, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_all_active_games(self) -> List[FreeGame]:
        all_games: List[FreeGame] = []
        new_games: List[FreeGame] = []

        for store in self.monitored_stores:
            try:
                games = self.api.get_by_platform(store)
                for game in games:
                    if not game.is_expired():
                        all_games.append(game)

                        gid = str(game.id)
                        if gid not in self.seen_games:
                            self.seen_games[gid] = str(game.end_date)
                            new_games.append(game)

                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Fehler beim Laden von {store}: {e}")

        self._save_cache()

        if new_games:
            self._send_discord_notifications(new_games)

        return all_games

    def _send_discord_notifications(self, games: List[FreeGame]):
        if not self.discord_webhook_url:
            logger.warning("⚠️ Discord Webhook URL nicht konfiguriert!")
            return

        for game in games:
            try:
                embed = {
                    "embeds": [{
                        "title": f"🎮 {game.title}",
                        "description": (game.description[:200] + "...") if len(game.description) > 200 else game.description,
                        "color": self._get_store_color(game.store),
                        "thumbnail": {"url": game.thumbnail},
                        "fields": [
                            {"name": "🏪 Store", "value": game.store, "inline": True},
                            {"name": "💰 Wert", "value": game.worth, "inline": True},
                            {"name": "⏰ Läuft ab", "value": game.end_date, "inline": True},
                        ],
                        "url": game.open_giveaway_url,
                        "footer": {"text": "SchnuffsPromotionAlerts • Freegames Checker"},
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }

                response = requests.post(self.discord_webhook_url, json=embed, timeout=10)
                response.raise_for_status()

                logger.info(f"✅ Discord Notification gesendet: {game.title}")
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ Discord Notification Fehler für {game.title}: {e}")

    def _get_store_color(self, store: str) -> int:
        colors = {
            'Epic Games': 0x2E3440,
            'Steam': 0x1B2838,
            'GOG': 0x86328A,
            'Ubisoft': 0x0080FF,
            'EA': 0xFF6600,
            'Amazon Prime Gaming': 0x232F3E,
            'PC': 0x5865F2
        }
        return colors.get(store, 0x5865F2)

    def start_auto_refresh(self):
        if self.running:
            return
        self.running = True
        self.refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self.refresh_thread.start()
        logger.info("✅ Freegames Auto-Refresh gestartet")

    def _auto_refresh_loop(self):
        self.get_all_active_games()

        while self.running:
            time.sleep(self.refresh_interval)
            if not self.running:
                break
            self.get_all_active_games()

    def cleanup(self):
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        self.api.close()


class FreegamesPage(QWidget):
    def __init__(self, settings: dict = None):
        super().__init__()
        self.setObjectName("FreegamesPage")

        app_settings = load_settings()
        discord_webhook = app_settings.get("discord", {}).get("freegames_webhook", "")

        if settings is None:
            settings = {}

        settings['discord_webhook_url'] = discord_webhook
        self.settings = settings

        self.integration = SchnuffsFreegamesIntegration(settings)
        self.integration.start_auto_refresh()

        self.init_ui()
        self.load_games()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_games)
        self.timer.start(10 * 60 * 1000)

    # ✅ NEU: live updaten (ohne Neustart)
    def set_discord_webhook_url(self, webhook_url: str):
        url = (webhook_url or "").strip()
        self.settings["discord_webhook_url"] = url
        self.integration.discord_webhook_url = url

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.title_label = QLabel("🎮 Freegames Übersicht")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.title_label)

        self.refresh_button = QPushButton("🔄 Aktualisieren")
        self.refresh_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.refresh_button.clicked.connect(self.load_games)
        layout.addWidget(self.refresh_button)

        self.games_list = QListWidget()
        self.games_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.games_list.setSpacing(5)
        layout.addWidget(self.games_list)

    def load_games(self):
        self.games_list.clear()
        games = self.integration.get_all_active_games()

        if not games:
            self.games_list.addItem(QListWidgetItem("Keine Freegames verfügbar"))
            return

        for game in games:
            display_text = f"{game.title} [{game.store}] - Wert: {game.worth} - Läuft ab: {game.end_date}"
            item = QListWidgetItem(display_text)

            if game.thumbnail:
                try:
                    resp = requests.get(game.thumbnail, timeout=5)
                    img_data = BytesIO(resp.content)
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data.read())
                    icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)
                except Exception:
                    pass

            desc = game.description or "Keine Beschreibung verfügbar."
            url = game.open_giveaway_url or ""
            item.setToolTip(f"{desc}\n\nLink: {url}")

            self.games_list.addItem(item)

    def cleanup(self):
        if hasattr(self, "timer") and self.timer:
            self.timer.stop()
        self.integration.cleanup()
