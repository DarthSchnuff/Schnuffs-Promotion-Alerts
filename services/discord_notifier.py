import requests
import datetime


class DiscordNotifier:
    """
    Universeller Discord Webhook Notifier.
    Wird pro Service (z.B. FreeGames / Twitch) separat instanziert.
    """

    def __init__(self, webhook_url: str, name: str = "Discord"):
        self.webhook_url = (webhook_url or "").strip()
        self.name = name

    # ================= CORE =================
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
            print(f"[{self.name}] Discord Fehler: {e}")

    # ================= TWITCH =================
    def streamer_live(self, name: str, title: str, game: str, url: str, thumbnail: str):
        if not self.webhook_url:
            return

        payload = {
            "embeds": [
                {
                    "title": f"🔴 {name} ist LIVE!",
                    "url": url,
                    "description": f"**{title}**\n🎮 {game}",
                    "color": 0xED4245,
                    "image": {"url": thumbnail},
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }
            ]
        }

        try:
            requests.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            print(f"[{self.name}] Twitch Live Fehler: {e}")

    def streamer_offline(self, name: str):
        self.send(
            title="⚫ Stream Offline",
            description=f"**{name}** ist jetzt offline.",
            color=0x2F3136
        )

    # ================= INFO / ERROR =================
    def info(self, message: str):
        self.send(
            title="ℹ️ Info",
            description=message,
            color=0x57F287
        )

    def error(self, message: str):
        self.send(
            title="⚠️ Fehler",
            description=message,
            color=0xFEE75C
        )
