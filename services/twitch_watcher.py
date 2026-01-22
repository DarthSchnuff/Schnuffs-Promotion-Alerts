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
        self.interval = max(int(interval), 30)
        self.fire_initial = fire_initial

        # Event = "running"; stop() -> clear()
        self._running = threading.Event()
        self._running.set()

        self.access_token: Optional[str] = None
        self.token_expiry: float = 0

        self.live_state: dict[str, bool] = {}

        # Optional: cache user_id to avoid repeated /users calls
        self._user_id_cache: dict[str, str] = {}

        # Session: sauber schließbar
        self._session = requests.Session()

    # ================= THREAD =================
    def stop(self):
        """Thread sauber stoppen (kein join hier!)."""
        self._running.clear()

    def run(self):
        """Thread-Loop"""
        try:
            self._fetch_token()

            if self.fire_initial and self._running.is_set():
                self.check_streamers(force_fire=True)

            while self._running.is_set():
                try:
                    self.check_streamers()
                except Exception as e:
                    logger.error(f"Fehler bei Twitch-Check: {e}")

                # ✅ WICHTIG: wirklich schlafen (Event.wait wäre hier falsch, da Event gesetzt ist)
                for _ in range(self.interval):
                    if not self._running.is_set():
                        break
                    time.sleep(1)

        finally:
            try:
                self._session.close()
            except Exception:
                pass

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
            resp = self._session.post(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 0) or 0
            self.token_expiry = time.time() + float(expires_in)

            if self.access_token:
                logger.info("✅ Twitch Token erfolgreich abgerufen")
            else:
                logger.error("❌ Twitch Token Antwort ohne access_token")

        except Exception as e:
            logger.error(f"❌ Twitch Token Fehler: {e}")
            self.access_token = None

    def check_streamers(self, force_fire: bool = False):
        """Prüft alle Streamer auf Live-Status"""
        self._fetch_token()
        if not self.access_token or not self._running.is_set():
            return

        current = {
            name.strip().lower()
            for name in self.get_streamers()
            if name and name.strip()
        }

        removed = set(self.live_state.keys()) - current
        for name in removed:
            del self.live_state[name]
            self._user_id_cache.pop(name, None)

        headers = {
            # ✅ Twitch erwartet "Client-Id"
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
        }

        for name in current:
            if not self._running.is_set():
                return

            try:
                info = self._get_stream_info(name, headers)
                is_live = info is not None
                last = self.live_state.get(name)

                if force_fire or last is None or last != is_live:
                    self.live_state[name] = is_live
                    self.callback(name, is_live, info)

            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    logger.warning("🔁 Twitch Token abgelaufen, erneuere...")
                    self.access_token = None
                    self._fetch_token()
                else:
                    status = e.response.status_code if e.response is not None else "?"
                    body = ""
                    try:
                        body = e.response.text if e.response is not None else ""
                    except Exception:
                        pass
                    logger.error(f"[{name}] HTTP Fehler {status}: {e} {body[:200]}")

            except Exception as e:
                logger.error(f"[{name}] Fehler: {e}")

    # ------------------ Twitch helpers ------------------
    def _get_user_id(self, login: str, headers: dict) -> Optional[str]:
        """Resolve login -> user_id (cached)."""
        if login in self._user_id_cache:
            return self._user_id_cache[login]

        url = "https://api.twitch.tv/helix/users"
        params = {"login": login}

        r = self._session.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()

        data = r.json().get("data", [])
        if not data:
            return None

        user_id = data[0].get("id")
        if user_id:
            self._user_id_cache[login] = user_id
        return user_id

    def _get_stream_info(self, login: str, headers: dict) -> Optional[dict]:
        """
        Prüft ob Streamer live ist und liefert Live-Infos zurück.
        Nutzt bevorzugt user_id (robuster) und fällt zur Not auf user_login zurück.
        """
        # 1) Prefer user_id
        user_id = self._get_user_id(login, headers)
        if user_id:
            info = self._fetch_stream_by_params(headers, {"user_id": user_id})
            if info:
                return info

        # 2) Fallback user_login
        return self._fetch_stream_by_params(headers, {"user_login": login})

    def _fetch_stream_by_params(self, headers: dict, params: dict) -> Optional[dict]:
        url = "https://api.twitch.tv/helix/streams"
        r = self._session.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()

        data = r.json().get("data", [])
        if not data:
            return None

        stream = data[0]
        # ✅ Mehr echte Live-Daten fürs Dashboard / Logging
        return {
            "title": stream.get("title", "") or "",
            "game_name": stream.get("game_name", "") or "",
            "viewer_count": stream.get("viewer_count", 0) or 0,
            "started_at": stream.get("started_at", "") or "",
        }
