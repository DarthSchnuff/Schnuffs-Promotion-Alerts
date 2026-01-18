from PySide6.QtCore import QObject, Signal
from core.config import load_settings
from services.discord_notifier import DiscordNotifier
from services.twitch_watcher import TwitchWatcher  # ← HINZUFÜGEN!


class AppController(QObject):
    """
    Zentrale Steuerung für Schnuffs Promotion Alerts
    Verbindet Settings, Services und Dashboard
    """

    # ================= SIGNALS =================
    status_message = Signal(str)
    streamer_updated = Signal(object)

    def __init__(self):
        super().__init__()
        self.settings = load_settings()

        # ================= DISCORD =================
        discord_cfg = self.settings.get("discord", {})
        self.discord_twitch = DiscordNotifier(
            discord_cfg.get("twitch_webhook", "")
        )
        self.discord_freegames = DiscordNotifier(
            discord_cfg.get("freegames_webhook", "")
        )

        # ================= TWITCH =================
        twitch_cfg = self.settings.get("twitch", {})
        self.twitch_client_id = twitch_cfg.get("client_id", "")
        self.twitch_client_secret = twitch_cfg.get("client_secret", "")
        self.twitch_watcher: TwitchWatcher | None = None

    # ======================================================================
    # STARTUP
    # ======================================================================

    def start(self):
        """Startet alle aktivierten Services"""
        self.status_message.emit("Initialisiere Services...")
        self._start_twitch()
        self.status_message.emit("Alle aktiven Services gestartet ✅")

    # ======================================================================
    # TWITCH
    # ======================================================================

    def _start_twitch(self):
        if not self.twitch_client_id or not self.twitch_client_secret:
            self.status_message.emit("⚠ Twitch nicht konfiguriert")
            return

        self.status_message.emit("Starte Twitch Watcher...")

        self.twitch_watcher = TwitchWatcher(
            client_id=self.twitch_client_id,
            client_secret=self.twitch_client_secret,
            get_streamers=self.get_streamers,
            callback=self._on_streamer_update,
            interval=60,
            fire_initial=True,
        )
        self.twitch_watcher.start()

        self.status_message.emit("🟢 Twitch Service aktiv")

    def get_streamers(self) -> list[str]:
        """Gibt Liste der zu überwachenden Streamer zurück"""
        return self.settings.get("streamers", [])

    def _on_streamer_update(self, name: str, is_live: bool, info: dict | None):
        """TwitchWatcher Callback"""

        # Nur weiter, wenn Stream wirklich live ist
        if not is_live or not info:
            return

        # Dashboard Update
        streamer_data = {
            "name": name,
            "is_online": True,
            "title": info.get("title", "")
        }
        self.streamer_updated.emit(streamer_data)

        # Discord Notification
        self.discord_twitch.send(
            title=f"{name} ist jetzt LIVE!",
            description=info.get("title", "")
        )

    # ======================================================================
    # SHUTDOWN
    # ======================================================================

    def shutdown(self):
        """Stoppt alle Services beim Beenden der App"""
        self.status_message.emit("Stoppe Services...")

        if self.twitch_watcher:
            self.twitch_watcher.stop()
            self.twitch_watcher.join()  # <- sorgt dafür, dass Thread wirklich beendet wird

        self.status_message.emit("✅ Alle Services gestoppt")

