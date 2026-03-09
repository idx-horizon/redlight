from flask import Blueprint, Response, render_template, request, current_app, stream_with_context, flash, redirect, url_for
from flask_login import login_required
from werkzeug.security import generate_password_hash
import pandas as pd
import os
import math
import json
from datetime import datetime
import matplotlib.pyplot as plt
import sqlite3

from forms.admin_forms import UserAdminForm
from auth import requires_permission
from models import User
from app import db
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

@admin_bp.route('/user/<username>', methods=['GET', 'POST'])
@admin_bp.route('/user', defaults={'username': None}, methods=['GET', 'POST'])
#@login_required
def user_admin(username=None):
    user = User.query.filter_by(username=username).first() if username else None
    form = UserAdminForm(obj=user)

    # Pretty-print JSON for Ace Editor
    if user and user.settings:
        try:
            form.settings.data = json.dumps(json.loads(user.settings), indent=2)
        except json.JSONDecodeError:
            form.settings.data = user.settings  # leave as-is if invalid

    if form.validate_on_submit():
        if not user:
            user = User(username=form.username.data)
            db.session.add(user)
        user.email = form.email.data
        user.enabled = form.enabled.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)

        # Grab JSON from the form submission
        settings_json = request.form.get('settings', '{}')
        try:
            # Validate JSON on backend too
            user.settings = json.dumps(json.loads(settings_json))
        except json.JSONDecodeError:
            flash("Invalid JSON in settings!", "danger")
            return render_template("admin/user_form.html", form=form, user=user)

        db.session.commit()
        flash("User saved successfully!", "success")
        return redirect(url_for('admin.user_admin', username=user.username))

    return render_template("admin/user_form.html", form=form, user=user)


