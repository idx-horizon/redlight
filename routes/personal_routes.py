
from flask import Blueprint, render_template, request, current_app, jsonify
from flask_login import login_required
import pandas as pd
import os
import math
import json
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import sqlite3

from helpers.googlesheets import get_metrics
from utils.db import get_db
from auth import requires_permission

BP="personal"
personal_bp = Blueprint( BP, __name__, url_prefix=f"/{BP}")

@personal_bp.route('/box_breathing')
def box_breathing():
    return render_template(
        "personal/box_breathing.html",
        page_title="Box Breathing",
    )


@personal_bp.route("/alcohol")
@login_required
@requires_permission()
def alcohol():
    db = get_db(os.environ.get('DB_HEALTH'))

    # ---- Step 1: read query params ----
    range_param = request.args.get("range")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    today = date.today()

    # ---- Step 2: apply range shortcuts if specified ----
    if range_param == "7d":
        end_date = today.isoformat()
        start_date = (today - timedelta(days=6)).isoformat()
    elif range_param == "28d":
        end_date = today.isoformat()
        start_date = (today - timedelta(days=27)).isoformat()
    elif range_param == "All":
        end_date = today.isoformat()
        earliest = db.execute("SELECT MIN(sample_date) FROM alcohol_units").fetchone()[0]
        start_date = earliest or end_date  # fallback if table empty
    else:
        # fallback to start/end dates if provided
        if not end_date:
            end_date = today.isoformat()
        if not start_date:
            start_date = (today - timedelta(days=7)).isoformat()

    # ---- Step 3: fetch daily series for chart ----
    rows = db.execute("""
        SELECT sample_date, sample_units
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
        ORDER BY sample_date
    """, (start_date, end_date)).fetchall()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    # ---- Step 4: calculate summary metrics for cards ----
    total = db.execute("""
        SELECT COALESCE(SUM(sample_units), 0)
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0]

    avg = db.execute("""
        SELECT ROUND(AVG(sample_units), 1)
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
    """, (start_date, end_date)).fetchone()[0] or 0

    dry_days = db.execute("""
        SELECT COUNT(*)
        FROM alcohol_units
        WHERE sample_date BETWEEN ? AND ?
        AND sample_units = 0
    """, (start_date, end_date)).fetchone()[0]

#    conn.close()

    # ---- Step 5: render template ----
    return render_template(
        "personal/alcohol_dashboard.html",
        page_title="Alcohol",
        labels=labels,
        values=values,
        total=total,
        avg=avg,
        dry_days=dry_days,
        start_date=start_date,
        end_date=end_date
    )

@personal_bp.route("/api/bp", methods=["POST"])
def ingest_bp():

    if request.headers.get("X-API-Key") != "my-jff-red-key":
        return jsonify({"error": "Unauthorized"}), 401

    raw = request.get_data(as_text=True)

    current_app.logger.info(f"RAW BODY:\n{raw}")

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    db = get_db(os.environ.get('DB_HEALTH'))

    parsed=[]

    for sample in data['records'].split():
        r=json.loads(sample)
        parsed.append((
            datetime.strptime(r["sample_date"], "%Y-%m-%d").date(),
            int(r["sample_value"]),
            datetime.strptime(data['meta_extract_dt'], "%Y-%m-%d %H:%M:%S"),
            data['meta_source'],
            data['meta_version']
        ))


    return jsonify({"status": "ok", "records": len(parsed)})


@personal_bp.route("/api/alcohol", methods=["POST"])
def ingest_alcohol():

    if request.headers.get("X-API-Key") != "my-jff-red-key":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    db = get_db(os.environ.get('DB_HEALTH'))

    db.execute("""
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

    db.executemany("""
        INSERT OR REPLACE INTO alcohol_units
        (sample_date, sample_units, meta_extract_dt, meta_source, meta_version)
        VALUES (?, ?, ?, ?, ?)
    """, parsed)

    db.commit()

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
             spreadsheet_id=os.environ['SHEET_FINANCE'],
             ranges=required_ranges,
             creds_path=os.environ['GOOGLE_CREDS']
        )

        return render_template(
            "personal/finance_dashboard.html",
            page_title="Finance",
            data=data
        )

    except Exception as e:
        current_app.logger.exception("Google Sheet read failed")
        return {"error": str(e)}, 500


# PENSION SERVICE

def load_data():
    with open("data/pension/service.json", "r") as f:
        return json.load(f)

def sanitise_service(raw):
    if isinstance(raw, dict):
        return {
            k: sanitise_service(v)
            for k, v in raw.items()
            if k not in ["_links", "_uid"]
        }

    if isinstance(raw, list):
        return [sanitise_service(v) for v in raw]

    return raw


def normalise_services(services):

    normalised = []

    for s in services:
        start = s.get("FromDate")
        end = s.get("ToDate") or datetime.today().strftime("%Y-%m-%d")

        breaks = []

        for b in s.get("Breaks", []):
            breaks.append({
                "start": b["FromDate"],
                "end": b["ToDate"],
                "type": b.get("BreakType"),
                "raw": b
            })

        normalised.append({
            "start": start,
            "end": end,
            "employer": s.get("EmployerName"),
            "employerCode": s.get("EmployerCode"),
            "type": s.get("BenefitType"),
            "breaks": breaks,
            "raw": s
        })

    normalised.sort(key=lambda x: x["start"])

    return normalised

def detect_gaps(services):

    gaps = []
    for i in range(len(services) - 1):
        if services[i]["end"] < services[i+1]["start"]:
            gaps.append({
                "start": services[i]["end"],
                "end": services[i+1]["start"]
            })

    return gaps

def add_positions(services, gaps):

    dates = []

    for s in services:
        dates.append(datetime.fromisoformat(s["start"]))
        dates.append(datetime.fromisoformat(s["end"]))

        for b in s["breaks"]:
            dates.append(datetime.fromisoformat(b["start"]))
            dates.append(datetime.fromisoformat(b["end"]))

    min_date = min(dates)
    max_date = max(dates)
    total_days = (max_date - min_date).days or 1

    def to_percent(date_str):
        d = datetime.fromisoformat(date_str)

        return ((d - min_date).days / total_days) * 100

    for s in services:
        s["start_pos"] = to_percent(s["start"])
        s["width"] = to_percent(s["end"]) - s["start_pos"]

        service_days = (
            datetime.fromisoformat(s["end"]) -
            datetime.fromisoformat(s["start"])
        ).days or 1

        break_days = 0

        for b in s["breaks"]:
            b_start = datetime.fromisoformat(b["start"])
            b_end = datetime.fromisoformat(b["end"])
            b["start_pos"] = to_percent(b["start"])
            b["width"] = to_percent(b["end"]) - b["start_pos"]
            break_days += (b_end - b_start).days

        s["break_pct"] = round((break_days / service_days) * 100, 1)

    for g in gaps:
        g["start_pos"] = to_percent(g["start"])
        g["width"] = to_percent(g["end"]) - g["start_pos"]


def enrich_service(service):
    mapping = {
        "HO": ("deptA", "Department A"),
        "NPIA": ("deptB", "Department B"),
        "HAHO": ("deptC", "Department C"),
        "HOFF": ("deptD", "Department D"),
    }

    code = service["employerCode"]

    if code in mapping:
        service["dispEmployerCode"] = mapping[code][0]
        service["dispEmployerName"] = mapping[code][1]
    else:
        service["dispEmployerCode"] = code
        service["dispEmployerName"] = service.get("EmployerName")

    return service

@personal_bp.route("/pension")
@login_required
def pension():

    data = load_data()

    services = normalise_services(data.get("Services", []))

    for s in services:
        enrich_service(s)   # adds dispEmployerCode / dispEmployerName

    for s in services:
        s["clean_raw"] = sanitise_service(s["raw"])

    gaps = detect_gaps(services)
    add_positions(services, gaps)

    return render_template(
        "personal/pension.html",
        data=data,
        services=services,
        gaps=gaps

    )
