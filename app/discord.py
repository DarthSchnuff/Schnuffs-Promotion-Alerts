import requests
from .settings import settings

def send_notification(user, stream):
    payload = {
        "content": (
            f"🔴 **{user} ist LIVE!**\n"
            f"🎮 {stream['game_name']}\n"
            f"📝 {stream['title']}\n"
            f"https://twitch.tv/{user}"
        )
    }
    requests.post(settings.DISCORD_WEBHOOK, json=payload)
