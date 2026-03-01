import json

def get_user_settings(db, username):
    row = db.execute(
        "SELECT settings FROM user WHERE username = ?",
        (username,)
    ).fetchone()

    if not row or not row["settings"]:
        return {}

    return json.loads(row["settings"])


def update_user_settings(db, username, settings):
    db.execute(
        "UPDATE user SET settings = ? WHERE username = ?",
        (json.dumps(settings), username)
    )
    db.commit()
