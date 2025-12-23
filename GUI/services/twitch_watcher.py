import time
import threading
import requests


class TwitchWatcher(threading.Thread):
    """
    Überwacht Twitch-Streamer und meldet Statusänderungen (LIVE / OFFLINE)
    callback(streamer_name: str, is_live: bool)
    """

    def __init__(
        self,
        client_id: str,
        token: str,
        streamers: list[str],
        callback,
        interval: int = 60,
        fire_initial: bool = False
    ):
        super().__init__(daemon=True)

        self.client_id = client_id
        self.token = token
        self.streamers = streamers
        self.callback = callback
        self.interval = max(interval, 30)  # Twitch-freundlich
        self.fire_initial = fire_initial

        self._running = threading.Event()
        self._running.set()

        self.headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }

        # name -> bool (live status)
        self.live_state: dict[str, bool] = {}

    # ================= THREAD =================
    def stop(self):
        """Stoppt den Watcher sauber"""
        self._running.clear()

    def run(self):
        while self._running.is_set():
            self.check_streamers()

            # interruptable sleep
            for _ in range(self.interval):
                if not self._running.is_set():
                    return
                time.sleep(1)

    # ================= LOGIC =================
    def check_streamers(self):
        for name in list(self.streamers):
            try:
                is_live = self.is_streamer_live(name)
                last_state = self.live_state.get(name)

                # Initialer Zustand
                if last_state is None:
                    self.live_state[name] = is_live
                    if self.fire_initial:
                        self.callback(name, is_live)
                    continue

                # Statuswechsel
                if last_state != is_live:
                    self.live_state[name] = is_live
                    self.callback(name, is_live)

            except requests.HTTPError as e:
                code = e.response.status_code
                if code == 401:
                    self._log(f"Token ungültig oder abgelaufen ({name})")
                elif code == 429:
                    self._log("Twitch Rate-Limit erreicht")
                else:
                    self._log(f"HTTP Fehler {code} bei {name}")

            except Exception as e:
                self._log(f"Fehler bei {name}: {e}")

    def is_streamer_live(self, name: str) -> bool:
        url = "https://api.twitch.tv/helix/streams"
        params = {"user_login": name}

        r = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )
        r.raise_for_status()

        data = r.json().get("data", [])
        return len(data) > 0

    # ================= UTILS =================
    def _log(self, msg: str):
        # absichtlich kein print-Spam – zentral steuerbar
        print(f"[TwitchWatcher] {msg}")
