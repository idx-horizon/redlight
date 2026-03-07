from math import ceil
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import current_user
from datetime import datetime
import json

from utils.helpers import time_to_seconds, seconds_to_time
from utils.pagination import paginate
from utils.user import get_user_settings

BP="runner"
runner_bp = Blueprint(BP, __name__, url_prefix=f"/{BP}")


@runner_bp.route("/", defaults={"runner_id": None})
@runner_bp.route("/<int:runner_id>")
def runs(runner_id):
    # --- Access control: allowed runners ---
    user_settings = get_user_settings(current_user.username)
    current_app.logger.info(f"** Settings: {user_settings}")

    allowed_runners = user_settings.get("allowed_runners",
                                        [{"id": user_settings.get("runner_id"),
                                          "name": "You"}])
    current_app.logger.info(f"** Allowed: {allowed_runners}")

    allowed_runner_ids = [r["id"] for r in allowed_runners]

    if runner_id not in allowed_runner_ids:
        return redirect(url_for("runner.runs", runner_id=user_settings.get("runner_id")))


    # Get all runs
    runner_runs, runner_title, runner_last_seen_age = get_runner_results(runner_id)

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
       runner_runs = [r for r in runner_runs if r["date_obj"].year == year_filter]



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

    pagination = paginate(runner_runs, page, per_page=20)

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

        years=years,
        year_filter=year_filter,

        sort_key=sort_key,
        reverse=reverse
    )

def get_runner_results(runner_id=184594):
    with open(f'data/runners/{runner_id}.json','r',encoding='utf-8') as f:
        data = json.loads(f.read())
    return data[1]['runs'], data[1]['title'], data[1]['last_seen_age']

