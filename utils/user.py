import os
import json
from  flask import current_app
from utils.db import get_db

def get_user_settings(username):
    db = get_db(os.environ.get('DB_USERS'))

    row = db.execute(
        "SELECT settings FROM user WHERE username = ?",
        (username,)
    ).fetchone()

    if not row or not row["settings"]:
        return {}

    return json.loads(row["settings"])


def update_user_settings(username, settings):
    db = get_db(os.environ.get('DB_USERS'))
    db.execute(
        "UPDATE user SET settings = ? WHERE username = ?",
        (json.dumps(settings), username)
    )
    db.commit()
