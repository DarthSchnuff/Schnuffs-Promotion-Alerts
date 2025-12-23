import requests


class DiscordWebhook:
    def __init__(self, url: str):
        self.url = url

    def send(self, title: str, message: str, color: int = 0x9146FF):
        if not self.url:
            return False

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color
                }
            ]
        }

        try:
            r = requests.post(self.url, json=payload, timeout=5)
            return r.status_code in (200, 204)
        except Exception:
            return False
