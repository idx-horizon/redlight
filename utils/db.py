# app/utils/db.py
import sqlite3
from flask import g, has_app_context, current_app

def get_db(db_path):
    if has_app_context():
        current_app.logger.info(f"Get DB: {db_path}")

        if not hasattr(g, "db_connections"):
            g.db_connections = {}

        if db_path not in g.db_connections:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            g.db_connections[db_path] = conn

        return g.db_connections[db_path]

    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

def close_dbs(e=None):
    """
    Close all stored SQLite connections at the end of request.
    """
    dbs = g.pop("dbs", {})
    for conn in dbs.values():
        conn.close()
