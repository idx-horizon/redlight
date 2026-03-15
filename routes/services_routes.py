from threading import Thread
from flask import Blueprint
import requests
import time
import os
from utils.telegram import send_telegram, handle_command

BP="services"
services_bp = Blueprint( BP, __name__, url_prefix=f"/{BP}")

AUTHORIZED_CHAT = int(os.environ.get("TELEGRAM_CHAT_ID", 0))
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OFFSET = None

def poll_telegram():
    global OFFSET
    while True:
        params = {"timeout": 30}
        if OFFSET:
            params["offset"] = OFFSET

        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=35)
            updates = r.json().get("result", [])
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)
            continue

        for update in updates:
            OFFSET = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue

            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            # Only allow authorized user
            if chat_id != AUTHORIZED_CHAT:
                continue

            handle_command(chat_id, text)

        time.sleep(1)

# Start polling in a background thread when blueprint is imported
Thread(target=poll_telegram, daemon=True).start()
