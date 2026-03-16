import os
import requests
import sqlite3

TOKEN = os.environ.get("TELEGRAM_TOKEN")

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)


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
        # example SQLite query
        conn = sqlite3.connect("data/PKRGEO.DB")
        row = conn.execute("""
            SELECT *
            FROM runs
            where runner_id = 184594
            ORDER BY run_date DESC
            LIMIT 1
        """).fetchone()
        if row:
            send_telegram(chat_id, f"🏃 Last run\n{row[0]}\n{row[1]}\nTime: {row[2]}")
        else:
            send_telegram(chat_id, "No runs found.")

    elif text == "/pb":
        # latest personal best
        conn = sqlite3.connect("runs.db")
        row = conn.execute("""
            SELECT event, time
            FROM runs
            WHERE time IS NOT NULL
            ORDER BY time ASC
            LIMIT 1
        """).fetchone()
        if row:
            send_telegram(chat_id, f"🏆 PB\n{row[0]}\nTime: {row[1]}")
        else:
            send_telegram(chat_id, "No PB found.")

    else:
        send_telegram(chat_id, "Unknown command. Try /start, /status, /lastrun, /pb")
