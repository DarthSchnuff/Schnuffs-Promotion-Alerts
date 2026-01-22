from PySide6.QtCore import QObject, Signal
from core.config import load_settings
from services.discord_notifier import DiscordNotifier
from services.twitch_watcher import TwitchWatcher


class AppController(QObject):
    """
    Zentrale Steuerung für Schnuffs Promotion Alerts
    Verbindet Settings, Services und Dashboard
    """

    status_message = Signal(str)
    streamer_updated = Signal(object)

    def __init__(self):
        super().__init__()
        self.settings = load_settings()

        discord_cfg = self.settings.get("discord", {})
        self.discord_twitch = DiscordNotifier(
            discord_cfg.get("twitch_webhook", ""),
            name="Twitch"
        )
        self.discord_freegames = DiscordNotifier(
            discord_cfg.get("freegames_webhook", ""),
            name="Freegames"
        )

        twitch_cfg = self.settings.get("twitch", {})
        self.twitch_client_id = twitch_cfg.get("client_id", "")
        self.twitch_client_secret = twitch_cfg.get("client_secret", "")
        self.twitch_watcher: TwitchWatcher | None = None

    def reload_settings(self):
        """✅ Settings neu laden und laufende Services/Notifiers aktualisieren."""
        self.settings = load_settings()

        discord_cfg = self.settings.get("discord", {})
        self.discord_twitch.webhook_url = (discord_cfg.get("twitch_webhook", "") or "").strip()
        self.discord_freegames.webhook_url = (discord_cfg.get("freegames_webhook", "") or "").strip()

        twitch_cfg = self.settings.get("twitch", {})
        self.twitch_client_id = (twitch_cfg.get("client_id", "") or "").strip()
        self.twitch_client_secret = (twitch_cfg.get("client_secret", "") or "").strip()

        self.status_message.emit("✅ Settings aktualisiert")

    # ======================================================================
    # STARTUP
    # ======================================================================

    def start(self):
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
        return self.settings.get("streamers", [])

    def _on_streamer_update(self, name: str, is_live: bool, info: dict | None):
        # Dashboard immer updaten
        streamer_data = {
            "name": name,
            "is_online": bool(is_live),
            "title": (info.get("title", "") if (is_live and info) else ""),
            "game_name": (info.get("game_name", "") if (is_live and info) else ""),
            "viewer_count": (info.get("viewer_count", 0) if (is_live and info) else 0),
            "started_at": (info.get("started_at", "") if (is_live and info) else ""),
        }
        self.streamer_updated.emit(streamer_data)

        # Discord nur wenn LIVE
        if is_live and info:
            self.discord_twitch.send(
                title=f"{name} ist jetzt LIVE!",
                description=info.get("title", "")
            )

    # ======================================================================
    # SHUTDOWN
    # ======================================================================

    def shutdown(self):
        self.status_message.emit("Stoppe Services...")

        if self.twitch_watcher:
            try:
                self.twitch_watcher.stop()
                self.twitch_watcher.join(timeout=5)
            except Exception:
                pass
            finally:
                self.twitch_watcher = None

        self.status_message.emit("✅ Alle Services gestoppt")
