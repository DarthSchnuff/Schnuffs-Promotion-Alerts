import requests
import datetime


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()

    def send(self, title: str, description: str, color: int = 0x5865F2):
        if not self.webhook_url:
            return

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
            ]
        }

        try:
            r = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            r.raise_for_status()
        except Exception as e:
            print(f"[DiscordNotifier] Fehler: {e}")

    # ================= EVENTS =================
    def streamer_live(self, name: str):
        self.send(
            title="🔴 Stream LIVE",
            description=f"**{name}** ist jetzt live auf Twitch!",
            color=0xED4245
        )

    def streamer_offline(self, name: str):
        self.send(
            title="⚫ Stream Offline",
            description=f"**{name}** ist jetzt offline.",
            color=0x2F3136
        )

    def error(self, message: str):
        self.send(
            title="⚠️ Fehler",
            description=message,
            color=0xFEE75C
        )

    def info(self, message: str):
        self.send(
            title="ℹ️ Info",
            description=message,
            color=0x57F287
        )
