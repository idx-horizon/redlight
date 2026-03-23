import json
import sqlite3
from datetime import datetime

DB_PATH = "data/PKRGEO.DB"  # change to your SQLite file

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn

def to_seconds(t):
    parts = list(map(int, t.split(':')))
    if len(parts) == 3:
        return parts[0]*3600 + parts[1]*60 + parts[2]
    return parts[0]*60 + parts[1]

def load_runner_runs(runner_id):
    """
    Load runner JSON into the `runs` table. Skips rows that already exist.
    """
    # 1️⃣ Read runner JSON
    with open(f"data/runners/{runner_id}.pkr", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    runs = data[1]["runs"]  # assuming your JSON format
    who = data[1]["title"]

    # 2️⃣ Insert runs into DB
    insert_sql = """
    INSERT INTO runs (
        runner_id,
        run_date,
        short_name,
        age_grade,
        event,
        pb,
        pos,
        run_number,
        time,
        results_link,
        time_seconds,
        ingest_dttm
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
    ON CONFLICT(runner_id, run_date, short_name) DO NOTHING;
    """

    changes = 0
    ingest_dttm = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    with db:
        for r in runs:
            convert_date = f"{r['Run Date'][6:10]}-{r['Run Date'][3:5]}-{r['Run Date'][0:2]}"
            db.execute(
                insert_sql,
                (
                    runner_id,
                    convert_date,
#                    r["Run Date"],
                    r["short_name"],
                    r.get("AgeGrade"),
                    r.get("Event"),
                    r.get("PB?"),
                    r.get("Pos"),
                    r.get("Run Number"),
                    r.get("Time"),
                    r.get("results_link"),
                    to_seconds(r["Time"]),
                    ingest_dttm
                )
            )
            change_ind = db.execute('select changes()').fetchone()
            changes +=  change_ind[0]

    print(f"{who} - Read {len(runs)} runs for runner {runner_id} - {changes} inserts")
