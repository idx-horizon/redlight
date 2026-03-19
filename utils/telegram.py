import os
import requests
import sqlite3
from  utils.sqlhelper import get_sql

TOKEN = os.environ.get("TELEGRAM_TOKEN")

def send_telegram(chat_id, text, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode}, timeout=5)


def handle_command(chat_id, text):
    """
    Dispatch commands sent to the bot.
    Extend this as needed.
    """
    if text == "/start":
        send_telegram(chat_id, "👋 Bot ready")

    elif text == "/status":
        send_telegram(chat_id, "✅ Server running")

    elif text == "/lastrun":
        conn = sqlite3.connect("data/PKRGEO.DB")
        row = conn.execute("""
            SELECT *
            FROM runs
            where runner_id = 184594
            ORDER BY run_date DESC
            LIMIT 1
        """).fetchone()
        if row:
#            send_telegram(chat_id, f"🏃 Last run\n{row[0]}\n{row[1]}\nTime: {row[2]}")
            send_telegram(chat_id, f"🏃‍ Last run\n{row}")
        else:
            send_telegram(chat_id, "No runs found.")

    elif text.startswith("/pb"):
        try:
           runner = text.split()[1]
        except:
           send_telegram(chat_id, "Usage: /pb name")
           return

        conn = sqlite3.connect("data/PKRGEO.DB")
        row =  conn.execute(get_sql('pbs'),(runner,)).fetchone()
        if row:
           send_telegram(chat_id,
                        f"🏆 {row[1]}'s PB:{row[2]}",
                        parse_mode='HTML')
        else:
           send_telegram(chat_id, f"Not found: {runner}")

    else:
        send_telegram(chat_id, "Unknown command. Try /start, /status, /lastrun, /pb")
