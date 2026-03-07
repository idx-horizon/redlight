import os

def get_version():
    try:
        with open("VERSION") as f:
            return f.read().strip()
    except Exception:
        return "dev"

def time_to_seconds(t):
    """
    Convert MM:SS or H:MM:SS to total seconds.
    """
    if not t or ":" not in t:
        return None

    parts = list(map(int, t.split(":")))

    if len(parts) == 2:
        parts = [0] + parts

    h, m, s = parts
    return h * 3600 + m * 60 + s


def seconds_to_time(seconds):
    """
    Convert seconds back to MM:SS or H:MM:SS.
    """
    if seconds is None:
        return ""

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}:{m:02}:{s:02}"
    else:
        return f"{m}:{s:02}"
