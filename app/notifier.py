import json

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

STREAMERS = config["streamers"]
CLIENT_ID = config["twitch"]["client_id"]
CLIENT_SECRET = config["twitch"]["client_secret"]
WEBHOOK_URL = config["discord"]["webhook_url"]
