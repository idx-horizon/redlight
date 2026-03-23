import os
import requests
import sqlite3
from  utils.sqlhelper import get_sql
from utils.db import get_db

TOKEN = os.environ.get("TELEGRAM_TOKEN")

def send_telegram(chat_id, text, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode}, timeout=5)


def handle_command(chat_id, text):
    """
    Dispatch commands sent to the bot.
    """
    if text == "/status":
        send_telegram(chat_id, "✅ Server running")

    elif text == "/lastrun":
#        conn = sqlite3.connect("data/PKRGEO.DB")
        conn = get_db("data/PKRGEO.DB")
        row = conn.execute("""
            SELECT *
            FROM runs
            WHERE runner_id = 184594
            ORDER BY run_date DESC
            LIMIT 1
        """).fetchone()
        if row:
            send_telegram(chat_id, f"🏃‍ Last run\n{row}")
        else:
            send_telegram(chat_id, "No runs found.")

    elif text.startswith('/allpb'):
        try:
           runner = text.split()[1]
        except:
           send_telegram(chat_id, "Usage:  /allpb name")

        conn = sqlite3.connect("data/PKRGEO.DB")
        rows = conn.execute('''
            SELECT year, pb, slowest, avg_time 
            FROM vw_runner_stats 
            WHERE known_as = ? collate NOCASE 
            ORDER BY year desc;
           ''',(runner,)).fetchall()

        best_ever = conn.execute('''
            SELECT year, pb, min(pb_seconds) 
            FROM vw_runner_stats 
            WHERE known_as = ? collate nocase;
           ''',(runner,)).fetchone()

        message = f'🥇 Best year: {best_ever[0]}: {best_ever[1]}\n'
        for r  in rows:
           message +=  f"{r[0]}: {r[1]} -> {r[2]} Avg:{r[3]} \n" 

        if rows:
            send_telegram(chat_id,
                          message,
                          parse_mode='html')
        else:
            send_telegram(chat_id, f"Not found {runner}")

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
