import os, sys
import json
from flask import Flask, session, render_template, redirect, url_for, flash, request, current_app, got_request_exception
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import check_password_hash
import sqlite3
from werkzeug.exceptions import HTTPException
import logging
from logging.handlers import RotatingFileHandler
import traceback

from utils.security import is_safe_url
from utils.db import close_dbs
from utils.sidebar import get_sidebar_items
from utils.helpers import get_version
# ---------------------------------------------------
# Load environment variables
# ---------------------------------------------------
load_dotenv()

# ---------------------------------------------------
# Flask app
# ---------------------------------------------------
app = Flask(__name__)

# Use the existing database file
db_path = os.path.join(os.path.dirname(__file__), 'data', 'USERS.DB')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.jinja_env.globals['get_sidebar_items'] = get_sidebar_items

# ---- logging setup ----
LOGFILE = os.environ['LOGFILE']

file_handler = RotatingFileHandler(
    LOGFILE,
    maxBytes=1000000,  # 1MB
    backupCount=3
)

# Remove Flask’s default handler
app.logger.handlers.clear()

# Prevent propagation to root logger (stops duplicates)
app.logger.propagate = False

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

log_level = os.getenv("LOGGING_LEVEL", "INFO").upper()
level = getattr(logging, log_level, logging.INFO)

app.logger.setLevel(level)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(level)

app.logger.setLevel(level)
#app.logger.addHandler(handler)

file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)

# log uncaught exceptions with full traceback
def log_exception(sender, exception, **extra):
    app.logger.exception("Unhandled Exception")

got_request_exception.connect(log_exception, app)


# Config
app.config["WEBSITE_NAME"] = os.getenv("WEBSITE_NAME", "Default Site")
app.config["WEBSITE_VERSION"] = os.getenv("WEBSITE_VERSION", "0.0.1")
#app.config["USERS_DB"] = os.path.join(BASE_DIR, "users.db")
app.config["DB_USERS"] = os.getenv("DB_USERS")
app.config["DB_PKRGEO"] = os.getenv("DB_PKRGEO")
app.config["LOGFILE"] = os.getenv("LOGFILE")
app.secret_key = os.getenv("SECRET_KEY", "dev-unsafe-key")  # must set in .env

@app.context_processor
def inject_context_processor():
    return {
        "WEBSITE_NAME": app.config.get("WEBSITE_NAME", "Default"),
#        "WEBSITE_VERSION": app.config.get("WEBSITE_VERSION", "0.0.1")
	"WEBSITE_VERSION": get_version()
    }

from flask import request, current_app, g
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

# Wrap the app with ProxyFix if behind a trusted proxy
# x_for=1 means trust the first X-Forwarded-For entry
# x_proto=1 if you want to trust X-Forwarded-Proto for HTTPS info
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

@app.before_request
def log_request_info():
    """
    Logs every request with:
    - Real client IP (from X-Forwarded-For if set)
    - Route and HTTP method
    - Logged-in user ID
    - Query parameters
    Stores IP in g.client_ip for routes/templates
    """

    # Get the real client IP from headers if available
    xfwd = request.headers.get("X-Forwarded-For")
    if xfwd:
        ip = xfwd.split(",")[0].strip()  # first IP is real client
    else:
        ip = request.remote_addr  # fallback

    # Route and HTTP method
    route = request.path
    method = request.method

    # Logged-in user ID if available
    user_id = getattr(current_user, "username", None)

    # Query parameters
    query_params = dict(request.args)

    # Store IP for use in routes/templates
    g.client_ip = ip

    # Log everything
    current_app.logger.info(
        f"IP={ip}, User={user_id}, Route={route}, Method={method}, Params={query_params}"
    )

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------------------------------------------
# Flask-Login setup
# ---------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Path to SQLite users DB
#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#USERS_DB = os.path.join(BASE_DIR, "users.db")
#USERS_DB = os.environ["USERS_DB"]
USERS_DB = app.config["DB_USERS"]

# ---------------------------------------------------
# User class for Flask-Login
# ---------------------------------------------------
class User(UserMixin):
    def __init__(self, username):
        self.username = username
        self._permissions = None  # cache effective permissions

    @staticmethod
    def get(username):
        """Fetch a user from DB by username"""
        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM user WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        if row:
            user = User(row["username"])
            user.password_hash = row["password_hash"]
            user.email = row["email"]
            user.enabled = bool(row["enabled"])
            user.settings = json.loads(row["settings"])
            return user

        return None

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def load_permissions(self):
        """Load effective permissions from roles + overrides"""
        if self._permissions is not None:
            return self._permissions

        conn = sqlite3.connect(USERS_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Get role permissions for all roles assigned to the user
        cur.execute("""
            SELECT rp.blueprint, rp.view
            FROM role_permission rp
            JOIN user_role ur ON rp.role_name = ur.role_name
            WHERE ur.username = ?
        """, (self.username,))
        perms = set((row["blueprint"], row["view"]) for row in cur.fetchall())

        # 2A Apply user overrides
        cur.execute("""
            SELECT blueprint, view, effect
            FROM user_override
            WHERE username = ?
        """, (self.username,))
        overrides = cur.fetchall()
        conn.close()

        # Convert to dictionary for easier checking
        self._permissions = {"allow": set(), "deny": set()}
        for bp, vw in perms:
            self._permissions["allow"].add((bp, vw))

        for row in overrides:
            bp, vw, effect = row["blueprint"], row["view"], row["effect"]
            if effect == "deny":
                self._permissions["deny"].add((bp, vw))
                # Remove from allow if present
                self._permissions["allow"].discard((bp, vw))
            elif effect == "allow":
                self._permissions["allow"].add((bp, vw))
                self._permissions["deny"].discard((bp, vw))

        return self._permissions

    def can_access(self, blueprint, view):
        """
        Check if user can access a given blueprint/view,
        considering wildcards and overrides
        """
        self.load_permissions()
        allow = self._permissions["allow"]
        deny = self._permissions["deny"]

        # First, check denies (specific or wildcard)
        for bp, vw in deny:
            if (bp == blueprint or bp == "*") and (vw == view or vw == "*"):
                return False

        # Then, check allows
        for bp, vw in allow:
            if (bp == blueprint or bp == "*") and (vw == view or vw == "*"):
                return True

        return False

    # Flask-Login required properties
    @property
    def is_active(self):
        return self.enabled

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(username):
    return User.get(username)


# ---------------------------------------------------
# Home / Dashboard
# ---------------------------------------------------
@app.route("/")
@app.route("/home")
def index():
    return render_template("index.html", page_title="Home")


# ---------------------------------------------------
# Login route
# ---------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        # Fetch user row from DB
        conn = sqlite3.connect(app.config["DB_USERS"])
        c = conn.cursor()
        c.execute("SELECT username, password_hash FROM user WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if not row or not check_password_hash(row[1], password):
            error = "Invalid username or password"
        else:
            user = User.get(username)   # Build User object

            login_user(user, remember=True)           # ← this sets current_user

            next_url = request.args.get("next")
            current_app.logger.info(f"LOGIN: user={current_user.username}")
            session['username'] = username
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            else:
                return redirect(url_for("index"))

    return render_template("login.html", error=error, page_title="Login")


# ---------------------------------------------------
# Logout route
# ---------------------------------------------------
@app.route("/logout")
def logout():
    username = current_user.username
    logout_user()
    app.logger.info(f'LOGOUT: user={username}')
    return redirect(url_for("index"))


# ---------------------------------------------------
# Global error handlers
# ---------------------------------------------------
@app.errorhandler(403)
@app.errorhandler(404)
def handle_errors(e):
    """Handle both 403 and 404 errors."""
    if e.code == 403:
        template = "errors/403.html"
    elif e.code == 404:
        template = "errors/404.html"
    else:
        template = "errors/error.html"  # fallback generic template
    return render_template(template, message=str(e), page_title="Error"), e.code


@app.errorhandler(Exception)
def handle_all_exceptions(e):
    if isinstance(e, HTTPException):
        return e
    # Log the error if needed
    app.logger.error(f"Unhandled Exception: {e} {traceback.format_exc()}")
    return render_template("errors/500.html", page_title="Error"), 500


# ---------------------------------------------------
# Register Blueprints
# ---------------------------------------------------
from routes.parkrun_routes import parkrun_bp
from routes.transaction_routes import transaction_bp
from routes.personal_routes import personal_bp
from routes.admin_routes import admin_bp
from routes.runner_routes import runner_bp

app.register_blueprint(parkrun_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(personal_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(runner_bp)

# Ensure all DB connections are closed at the end of each request
app.teardown_appcontext(close_dbs)

#if __name__ == "__main__":
#    app.run(debug=True)

# ---------------------------------------------------
# Run in debug mode (optional)
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)


