from math import ceil
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import current_user
from datetime import datetime
from collections import defaultdict, Counter
import json

from utils.helpers import time_to_seconds, seconds_to_time
from utils.pagination import paginate
from utils.user import get_user_settings
from utils.weather import get_weather
from utils.sqlhelper import get_sql
from utils.db import get_db
from utils.qr import make_qrcode

BP="runner"
runner_bp = Blueprint(BP, __name__, url_prefix=f"/{BP}")

@runner_bp.route("/qr")
def qr():
    runner_id = "A184594"
    qr_data = make_qrcode(runner_id)
    return render_template("runner/qr.html", runner_id=runner_id, qr_base64=qr_data) 

@runner_bp.route("/", defaults={"runner_id": None})
@runner_bp.route("/<int:runner_id>")
def runs(runner_id):
    current_app.logger.info(
        f"Request received: path={request.path} args={request.args.to_dict()}"
    )

    # --- Access control: allowed runners ---
    user_settings = get_user_settings(current_user.username)
    allowed_runners = user_settings.get("allowed_runners",
                                        [{"id": user_settings.get("runner_id"),
                                          "name": "You"}])

    allowed_runner_ids = [r["id"] for r in allowed_runners]

    if runner_id not in allowed_runner_ids:
        return redirect(url_for("runner.runs", runner_id=user_settings.get("runner_id")))


    # Get all runs
    runner_runs, runner_title, runner_last_seen_age = get_runner_results(runner_id)

    current_app.logger.info(runner_runs[0])
    # Count occurrences of each event 
    event_counts = Counter(r["Event"] for r in runner_runs)

    # Convert fields for sorting
    for r in runner_runs:
        r["date_obj"] = datetime.strptime(r["Run Date"], "%d/%m/%Y")
        r["time_seconds"] = time_to_seconds(r["Time"])

    # -----------------------------
    # Event filter
    # -----------------------------

    # Event list for dropdown filter
    events = sorted({r["Event"] for r in runner_runs})

    event_filter = request.args.get("event")

    if event_filter:
            runner_runs = [r for r in runner_runs if r["Event"] == event_filter]

    # -----------------------------
    # Year filter
    # -----------------------------

    # Compute year list
    years = sorted({r["date_obj"].year for r in runner_runs}, reverse=True)

    year_filter = request.args.get("year", type=int)

    if year_filter:
       current_app.logger.info(f'** Year filter:  {year_filter}')
       if year_filter > 0:
          runner_runs = [r for r in runner_runs if r["date_obj"].year == year_filter]
    else:
        current_app.logger.info('** No filter set')


    # -----------------------------
    # Sorting
    # -----------------------------
    sort_key = request.args.get("sort", "date")
    reverse = request.args.get("reverse", "0") == "1"

    if sort_key == "time":
        runner_runs.sort(key=lambda x: x["time_seconds"] or 999999, reverse=reverse)

    elif sort_key == "event":
        runner_runs.sort(key=lambda x: x["Event"], reverse=reverse)

    elif sort_key == "age":
        runner_runs.sort(key=lambda x: float(x["AgeGrade"].strip("%")), reverse=reverse)

    else:  # default sort by date
        runner_runs.sort(key=lambda x: x["date_obj"], reverse=not reverse)

    # -----------------------------
    # Pagination
    # -----------------------------
    page = request.args.get("page", 1, type=int)

    pagination = paginate(runner_runs, page, per_page=12)

    return render_template(
        "runner/runs.html",
        page_title="Runs",

        runner_id=runner_id,
        runner_title=runner_title.split()[0],
        runner_last_seen_age=runner_last_seen_age,

        allowed_runners=allowed_runners,

        runs=pagination["items"],

        page=pagination["page"],
        pages=pagination["pages"],

        total=pagination["total"],
        start=pagination["start"],
        end=pagination["end"],

        events=events,
        event_filter=event_filter,
        event_counts=event_counts,

        years=years,
        year_filter=year_filter,

        sort_key=sort_key,
        reverse=reverse
    )

def get_runner_results(runner_id=184594):
    with open(f'data/runners/{runner_id}.pkr','r',encoding='utf-8') as f:
        data = json.loads(f.read())

#    Add weather data for runs
    for r in data[1]['runs']:
        r['weather']=get_weather(r['short_name'],r['Run Date'])

    return data[1]['runs'], data[1]['title'], data[1]['last_seen_age']


@runner_bp.route("/dashboard")
def dashboard():

    # -----------------------------------
    # runner selection
    # -----------------------------------
    user_settings = get_user_settings(current_user.username)
    runners = user_settings.get("allowed_runners")
    runner_id = request.args.get("runner_id", type=int)

    if not runner_id:
        user_settings = get_user_settings(current_user.username)
        runner_id = user_settings.get("runner_id")

    runs, runner_title, runner_last_seen_age = get_runner_results(runner_id)


    # -----------------------------
    # normalize fields
    # -----------------------------
    for r in runs:
        # date
        r["date_obj"] = datetime.strptime(r["Run Date"], "%d/%m/%Y")
        # time in seconds
        r["seconds"] = time_to_seconds(r["Time"])
        # age grade as float
        r["age_grade"] = float(r["AgeGrade"].replace("%", ""))
        # PB flag
        r["is_pb"] = bool(r["PB?"].strip())

    # sort by date
    runs.sort(key=lambda r: r["date_obj"])

    # -----------------------------
    # summary stats
    # -----------------------------
    total_runs = len(runs)
    pb_seconds = min(r["seconds"] for r in runs)
    avg_age_grade = sum(r["age_grade"] for r in runs) / total_runs
    events = len(set(r["Event"] for r in runs))

    stats = {
        "total_runs": total_runs,
        "pb": seconds_to_time(pb_seconds),
        "avg_age_grade": round(avg_age_grade, 1),
        "events": events
    }

    # -----------------------------
    # chart data
    # -----------------------------
    dates = [r["Run Date"] for r in runs]
    times = [r["seconds"] for r in runs]
    pb_flags = [r["is_pb"] for r in runs]

    # PB progression
    best = float("inf")
    pb_progression = []
    for r in runs:
        if r["seconds"] < best:
            best = r["seconds"]
        pb_progression.append(best)

    # runs per year
    runs_per_year = defaultdict(int)
    for r in runs:
        year = r["date_obj"].year
        runs_per_year[year] += 1
    years = sorted(runs_per_year.keys())
    yearly_counts = [runs_per_year[y] for y in years]

    return render_template(
        "runner/dashboard.html",
        stats=stats,
        dates=dates,
        times=times,
        pb_progression=pb_progression,
        years=years,
        yearly_counts=yearly_counts,
        runners=runners,
        selected_runner=runner_id,
        pb_flags=pb_flags
    )

@runner_bp.route("/compare")
def compare():
    # Get query parameters
    runner1 = request.args.get("runner1")
    runner2 = request.args.get("runner2")
    page = int(request.args.get("page", 1))
    page_size = 10

    # Build list of allowed runners 
    user_settings = get_user_settings(current_user.username)
    allowed_runners = user_settings.get("allowed_runners",
                                        [{"id": user_settings.get("runner_id"),
                                          "name": "You"}])

    if not runner1:
        runner1 = allowed_runners[0]['id']

    # Build runner lookup for template
    runner_lookup = {str(r["id"]): r for r in allowed_runners}

    r1 = runner_lookup.get(str(runner1))
    r2 = runner_lookup.get(str(runner2))

    # Only fetch head-to-head if both runners are selected
    pb_compare = []
    stats = None
    total_rows = 0

    if r1 and r2:
        offset = (page - 1) * page_size
        # SQL: join results for the two runners for the same events

        db = get_db('data/PKRGEO.DB')

        sql = get_sql('compare_pb')
        pb_compare = db.execute(sql, (runner1, runner2, page_size, offset, runner1, runner2)).fetchall()

        # Get total number of shared events for pagination
        sql = get_sql("total_event_pb_count")
        total_rows = db.execute(sql, (runner1, runner2)).fetchone()[0]

        sql = get_sql('stats_pb_compare')
        stats = db.execute(sql, (runner1, runner2)).fetchone()
        stats = dict(stats)


    total_pages = (total_rows + page_size - 1) // page_size if total_rows else 1

    # Prepare query params for pagination links (page will be replaced)
    pagination_args = {"runner1": runner1, "runner2": runner2}

    return render_template(
        "runner/compare.html",
        page_title="Compare PBs",
        allowed_runners=allowed_runners,
        runner1=runner1,
        runner2=runner2,
        r1=r1,
        r2=r2,
        pb_compare=pb_compare,
        page=page,
        pages=total_pages,
        pagination_args=pagination_args,
        stats=stats
    )
