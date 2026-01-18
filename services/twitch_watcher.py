import time
import threading
import requests
import logging
from typing import Callable, Optional

logger = logging.getLogger("TwitchWatcher")
logging.basicConfig(level=logging.INFO)


class TwitchWatcher(threading.Thread):
    """
    Thread-basierter Twitch Streamer Status Watcher

    Args:
        client_id: Twitch Client-ID
        client_secret: Twitch Client-Secret
        get_streamers: Callable, liefert Liste von Streamern (str)
        callback: Callable(name: str, is_live: bool, info: dict | None)
        interval: Check-Intervall in Sekunden
        fire_initial: beim Start direkt einmal prüfen
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        get_streamers: Callable[[], list[str]],
        callback: Callable[[str, bool, Optional[dict]], None],
        interval: int = 60,
        fire_initial: bool = False,
    ):
        super().__init__(daemon=True)

        self.client_id = client_id
        self.client_secret = client_secret
        self.get_streamers = get_streamers
        self.callback = callback
        self.interval = max(interval, 30)
        self.fire_initial = fire_initial

        self._running = threading.Event()
        self._running.set()

        self.access_token: Optional[str] = None
        self.token_expiry: float = 0

        # name -> bool
        self.live_state: dict[str, bool] = {}

    # ================= THREAD =================
    def stop(self):
        """Thread sauber stoppen"""
        self._running.clear()
        self.join(timeout=5)  # Optional: Warten bis Thread wirklich endet

    def run(self):
        """Thread-Loop"""
        self._fetch_token()

        if self.fire_initial:
            self.check_streamers(force_fire=True)

        while self._running.is_set():
            try:
                self.check_streamers()
            except Exception as e:
                logger.error(f"Fehler bei Twitch-Check: {e}")

            for _ in range(self.interval):
                if not self._running.is_set():
                    return
                time.sleep(1)

    # ================= LOGIC =================
    def _fetch_token(self):
        """Holt einen App-Access-Token via Client-Credentials Flow"""
        if self.access_token and time.time() < self.token_expiry - 60:
            return

        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            resp = requests.post(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            self.access_token = data["access_token"]
            self.token_expiry = time.time() + data["expires_in"]

            logger.info("✅ Twitch Token erfolgreich abgerufen")

        except Exception as e:
            logger.error(f"❌ Twitch Token Fehler: {e}")
            self.access_token = None

    def check_streamers(self, force_fire: bool = False):
        """Prüft alle Streamer auf Live-Status"""
        self._fetch_token()
        if not self.access_token:
            return

        current = {
            name.strip().lower()
            for name in self.get_streamers()
            if name.strip()
        }

        removed = set(self.live_state.keys()) - current
        for name in removed:
            del self.live_state[name]

        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
        }

        for name in current:
            try:
                info = self._is_streamer_live(name, headers)
                is_live = info is not None
                last = self.live_state.get(name)

                if force_fire or last is None or last != is_live:
                    self.live_state[name] = is_live
                    self.callback(name, is_live, info)

            except requests.HTTPError as e:
                if e.response.status_code == 401:
                    logger.warning("🔁 Twitch Token abgelaufen, erneuere...")
                    self.access_token = None
                    self._fetch_token()
                else:
                    logger.error(f"[{name}] HTTP Fehler: {e}")

            except Exception as e:
                logger.error(f"[{name}] Fehler: {e}")

    def _is_streamer_live(self, name: str, headers: dict) -> Optional[dict]:
        """Prüft ob Streamer live ist"""
        url = "https://api.twitch.tv/helix/streams"
        params = {"user_login": name}

        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()

        data = r.json().get("data", [])
        if not data:
            return None

        stream = data[0]
        return {
            "title": stream.get("title", "")
        }

