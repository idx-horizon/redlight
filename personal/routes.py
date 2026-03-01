
from flask import Blueprint, render_template, request, current_app, jsonify
from flask_login import login_required
import pandas as pd
import os
import math
import json
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import logging
import sqlite3

from helpers.googlesheets import get_metrics

from auth import requires_permission

BP="personal"
personal_bp = Blueprint( BP, __name__, url_prefix=f"/{BP}")

DB_PATH = "data/healthdata.db"

def get_db():
    return sqlite3.connect(DB_PATH)

@personal_bp.route("/alcohol")
@login_required
@requires_permission()
def alcohol():
    conn = get_db()
    cur = conn.cursor()

    # ---- Step 1: read query params ----
    range_param = request.args.get("range")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    today = date.today()

    # ---- Step 2: apply range shortcuts if specified ----
    if range_param == "7d":
        end_date = today.isoformat()
        start_date = (today - timedelta(days=6)).isoformat()
    elif range_param == "30d":
        end_date = today.isoformat()
        start_date = (today - timedelta(days=29)).isoformat()
    elif range_param == "All":
        end_date = today.isoformat()
        earliest = cur.execute("SELECT MIN(sample_date) FROM alcohol_units").fetchone()[0]
        start_date = earliest or end_date  # fallback if table empty
    else:
        # fallback to start/end dates if provided
        if not end_date:
            end_date = today.isoformat()
        if not start_date:
            start_date = (today - timedelta(days=29)).isoformat()

    # ---- Step 3: fetch daily series for chart ----
    rows = cur.execute("""
        SELECT sample_date, sample_units
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
        ORDER BY sample_date
    """, (start_date, end_date)).fetchall()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    # ---- Step 4: calculate summary metrics for cards ----
    total = cur.execute("""
        SELECT COALESCE(SUM(sample_units), 0)
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    avg = cur.execute("""
        SELECT ROUND(AVG(sample_units), 1)
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0] or 0

    dry_days = cur.execute("""
        SELECT COUNT(*)
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
        AND sample_units = 0
    """, (start_date, end_date)).fetchone()[0]

    conn.close()

    # ---- Step 5: render template ----
    return render_template(
        "personal/alcohol_dashboard.html",
        page_title="Dashboard: Alcohol",
        labels=labels,
        values=values,
        total=total,
        avg=avg,
        dry_days=dry_days,
        start_date=start_date,
        end_date=end_date
    )

from flask import request, jsonify
from datetime import datetime
import sqlite3

@personal_bp.route("/api/alcohol", methods=["POST"])
def ingest_alcohol():

    if request.headers.get("X-API-Key") != "my-jff-red-key":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    current_app.logger.debug(data)

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alcohol_units (
        sample_date DATE PRIMARY KEY,
        sample_units INTEGER,
        meta_extract_dt TIMESTAMP,
        meta_source VARCHAR(20),
        meta_version VARCHAR(10)
    )
    """)

    parsed = []
    for sample in data['records'].split():
        r=json.loads(sample)
        parsed.append((
            datetime.strptime(r["sample_date"], "%Y-%m-%d").date(),
            int(r["sample_value"]),
            datetime.strptime(data['meta_extract_dt'], "%Y-%m-%d %H:%M:%S"),
            data['meta_source'],
            data['meta_version']
        ))

    cur.executemany("""
        INSERT OR REPLACE INTO alcohol_units
        (sample_date, sample_units, meta_extract_dt, meta_source, meta_version)
        VALUES (?, ?, ?, ?, ?)
    """, parsed)

    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "records": len(parsed)})

@personal_bp.route("/countdown")
@login_required
@requires_permission()
def countdown():

    def prepare_events(data):
        today = datetime.today().date()

        # handle dict or list input
        rows = data.get("values") if isinstance(data, dict) else data

        events = []
        for label, date_str, icon in rows[1:]:
            event_date = datetime.strptime(date_str, "%d-%b-%Y").date()
            days_left = (event_date - today).days
            progress = max(0, min(100, 100 - (days_left / 365 * 100)))

            events.append({
                "label": label,
                "icon": icon or "📅",
                "date": event_date.strftime("%d %b %Y"),
                "days_left": days_left,
                "progress": round(progress)
            })

        events.sort(key=lambda e: e["days_left"])
        return events

    data = get_metrics(
          spreadsheet_id=os.environ['SHEET_LIGHTSAIL'],
          ranges=['CountdownDates'],
          creds_path=os.environ['GOOGLE_CREDS']
    )

    return render_template(
         "personal/countdown.html",
         page_title="Countdown",
         events=prepare_events(data.get('CountdownDates'))
    )

@personal_bp.route("/finance")
@login_required
@requires_permission()
def finance():
    try:
        required_ranges = {
            "Ian": "Summary!H9",
            "Sheila": "Summary!H10",
            "Joint": "Summary!H11",
            "Total": "Summary!H12"
        }

        data = get_metrics(
#             spreadsheet_id='133lOhBaTYkus5_tQ79QDkBShbCaFYwjTuGWeXMcfxcU',
             spreadsheet_id=os.environ['SHEET_FINANCE'],
             ranges=required_ranges,
             creds_path=os.environ['GOOGLE_CREDS']
#             creds_path='/home/redagent/apps/googlecreds.json'
        )
        current_app.logger.info("Fetched %d rows from Google Sheet", len(data))

        return render_template(
            "personal/finance_dashboard.html",
            page_title="Dashboard: Finance",
            data=data
        )

    except Exception as e:
        current_app.logger.exception("Google Sheet read failed")
        return {"error": str(e)}, 500
