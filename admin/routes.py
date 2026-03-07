from flask import Blueprint, Response, render_template, request, current_app, stream_with_context
import pandas as pd
import os
import math
import json
from datetime import datetime
import matplotlib.pyplot as plt
import sqlite3

from auth import requires_permission

from helpers.logging import tail_log, stream_log

BP="admin"
admin_bp = Blueprint( BP, __name__, url_prefix=f"/{BP}")

@admin_bp.route("/", methods=['POST','GET'])
@requires_permission()
def dashboard():
    DB=os.environ.get("DB_USERS")
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # User list
    c.execute("SELECT username, settings FROM user;")
    users = c.fetchall()

    stats = {
        "total_users": len(users),
    }

    return render_template(
        "admin/admin_dashboard.html",
        page_title="Dashboard: Admin",
        users=users,
        stats=stats
    )


LOGFILE = os.environ["LOGFILE"]

@admin_bp.route("/logs")
def logs():
    # replace with your auth check
#    if not is_admin_user():
#        abort(403)
    lines = tail_log(LOGFILE, 300)
    return render_template(
                  "admin/adminstream.html",
                  page_title="Log", 
                  lines=lines)


@admin_bp.route("/stream")
def admin_log_stream():
    return Response(
        stream_with_context(stream_log(LOGFILE)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # critical if any proxy exists
            "Connection": "keep-alive"
        }
    )
