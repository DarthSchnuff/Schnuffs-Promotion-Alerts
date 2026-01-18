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
from pathlib import Path
import json
from typing import List, Dict
from core.config import load_settings  # NEU: Settings laden!

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= FreeGame + API =================
class FreeGame:
    def __init__(self, data: dict):
        self.id = data.get('id', 0)
        self.title = data.get('title', 'Unknown')
        self.description = data.get('description', '')
        self.thumbnail = data.get('thumbnail', '')
        self.open_giveaway_url = data.get('open_giveaway_url', '')
        self.end_date = data.get('end_date', 'N/A')
        self.worth = data.get('worth', 'N/A')
        self.store = self._determine_store(data.get('platforms', ''))

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
        if self.end_date == 'N/A': return False
        try:
            end = datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
            return datetime.now() > end
        except: return False

class GamerPowerAPI:
    BASE_URL = "https://www.gamerpower.com/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'SchnuffsPromotionAlerts/1.1.0'})

    def get_by_platform(self, platform: str) -> List[FreeGame]:
        try:
            url = f"{self.BASE_URL}/giveaways"
            params = {'platform': platform, 'type': 'game'}
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [FreeGame(item) for item in data]
        except Exception as e:
            logger.error(f"Fehler bei {platform}: {e}")
            return []

# ================= Freegames Integration =================
class SchnuffsFreegamesIntegration:
    def __init__(self, settings: dict):
        self.settings = settings
        self.cache_file = Path("data/freegames_cache.json")
        self.seen_games: Dict[int, str] = {}
        self.monitored_stores = settings.get('enabled_stores', [
            'epic-games-store', 'steam', 'gog', 'ubisoft', 'origin', 'pc'
        ])
        self.refresh_interval = settings.get('check_interval_hours', 6) * 60 * 60
        self.running = False
        self.refresh_thread = None
        self.api = GamerPowerAPI()
        
        # ========== NEU: Discord Webhook ==========
        self.discord_webhook_url = settings.get('discord_webhook_url', '')
        
        self._load_cache()

    def _load_cache(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.seen_games = json.load(f)
        except: 
            self.seen_games = {}

    def _save_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.seen_games, f, indent=2)
        except: 
            pass

    def get_all_active_games(self) -> List[FreeGame]:
        """Gibt **alle** aktiven Freegames zurück, sendet neue zu Discord"""
        all_games = []
        new_games = []  # NEU: Sammle neue Games
        
        for store in self.monitored_stores:
            try:
                games = self.api.get_by_platform(store)
                for game in games:
                    if not game.is_expired():
                        all_games.append(game)
                        
                        # NEU: Check ob neu
                        if game.id not in self.seen_games:
                            self.seen_games[game.id] = game.end_date
                            new_games.append(game)  # Zu Liste hinzufügen
                
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Fehler beim Laden von {store}: {e}")
        
        self._save_cache()
        
        # NEU: Sende neue Games zu Discord
        if new_games:
            self._send_discord_notifications(new_games)
        
        return all_games

    def _send_discord_notifications(self, games: List[FreeGame]):
        """Sendet neue Freegames zu Discord"""
        if not self.discord_webhook_url:
            logger.warning("⚠️ Discord Webhook URL nicht konfiguriert!")
            return
        
        for game in games:
            try:
                embed = {
                    "embeds": [{
                        "title": f"🎮 {game.title}",
                        "description": game.description[:200] + "..." if len(game.description) > 200 else game.description,
                        "color": self._get_store_color(game.store),
                        "thumbnail": {
                            "url": game.thumbnail
                        },
                        "fields": [
                            {
                                "name": "🏪 Store",
                                "value": game.store,
                                "inline": True
                            },
                            {
                                "name": "💰 Wert",
                                "value": game.worth,
                                "inline": True
                            },
                            {
                                "name": "⏰ Läuft ab",
                                "value": game.end_date,
                                "inline": True
                            }
                        ],
                        "url": game.open_giveaway_url,
                        "footer": {
                            "text": "SchnuffsPromotionAlerts • Freegames Checker"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
                
                response = requests.post(
                    self.discord_webhook_url,
                    json=embed,
                    timeout=10
                )
                response.raise_for_status()
                
                logger.info(f"✅ Discord Notification gesendet: {game.title}")
                
                # Rate-Limit beachten
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Discord Notification Fehler für {game.title}: {e}")
    
    def _get_store_color(self, store: str) -> int:
        """Gibt Discord Embed Farbe für Store zurück"""
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
        # Erster Check beim Start
        self.get_all_active_games()
        
        while self.running:
            time.sleep(self.refresh_interval)
            self.get_all_active_games()

    def cleanup(self):
        self.running = False
        if self.refresh_thread: 
            self.refresh_thread.join(timeout=5)

# ================= FreegamesPage (GUI) =================
class FreegamesPage(QWidget):
    def __init__(self, settings: dict = None):
        super().__init__()
        self.setObjectName("FreegamesPage")
        
        # ========== NEU: Lade Settings selbst! ==========
        app_settings = load_settings()
        discord_webhook = app_settings.get("discord", {}).get("freegames_webhook", "")
        
        # Merge mit übergebenen Settings
        if settings is None:
            settings = {}
        
        settings['discord_webhook_url'] = discord_webhook
        
        self.settings = settings
        
        # Integration
        self.integration = SchnuffsFreegamesIntegration(settings)
        self.integration.start_auto_refresh()

        self.init_ui()
        self.load_games()

        # Auto-Refresh alle 10 Minuten für UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_games)
        self.timer.start(10 * 60 * 1000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Titel
        self.title_label = QLabel("🎮 Freegames Übersicht")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Refresh Button
        self.refresh_button = QPushButton("🔄 Aktualisieren")
        self.refresh_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.refresh_button.clicked.connect(self.load_games)
        layout.addWidget(self.refresh_button)

        # Liste für Freegames
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

            # Thumbnail
            if game.thumbnail:
                try:
                    resp = requests.get(game.thumbnail, timeout=5)
                    img_data = BytesIO(resp.content)
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data.read())
                    icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)
                except: 
                    pass

            # Tooltip
            desc = game.description or "Keine Beschreibung verfügbar."
            url = game.open_giveaway_url or ""
            item.setToolTip(f"{desc}\n\nLink: {url}")

            self.games_list.addItem(item)

    def cleanup(self):
        self.integration.cleanup()
