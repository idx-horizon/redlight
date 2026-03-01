# app/utils/db.py
import sqlite3
from flask import g

def get_db(db_path):
    """
    Return a SQLite connection for the given database path.
    Stores one connection per database per request in `g`.
    """
    if "dbs" not in g:
        g.dbs = {}

    if db_path not in g.dbs:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        g.dbs[db_path] = conn

    return g.dbs[db_path]


def close_dbs(e=None):
    """
    Close all stored SQLite connections at the end of request.
    """
    dbs = g.pop("dbs", {})
    for conn in dbs.values():
        conn.close()
