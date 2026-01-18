# update_checker.py
import requests

GITHUB_API_RELEASES = (
    "https://api.github.com/repos/"
    "DarthSchnuff/Schnuffs-Promotion-Alerts/releases/latest"
)

def check_for_update(current_version: str):
    try:
        r = requests.get(GITHUB_API_RELEASES, timeout=5)
        r.raise_for_status()
        data = r.json()

        latest_version = data["tag_name"].lstrip("v")
        url = data["html_url"]

        if latest_version != current_version:
            return {
                "update": True,
                "latest": latest_version,
                "url": url
            }

        return {"update": False}

    except Exception:
        return {"update": False}
