import requests
from .settings import settings

TOKEN = None

def get_token():
    global TOKEN
    if TOKEN:
        return TOKEN

    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": settings.TWITCH_CLIENT_ID,
            "client_secret": settings.TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
    )
    TOKEN = r.json()["access_token"]
    return TOKEN


def is_live(username):
    token = get_token()
    headers = {
        "Client-ID": settings.TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    r = requests.get(
        "https://api.twitch.tv/helix/streams",
        headers=headers,
        params={"user_login": username}
    )
    data = r.json().get("data", [])
    return data[0] if data else None
