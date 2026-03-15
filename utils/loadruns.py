import json
import sqlite3

DB_PATH = "data/PKRGEO.DB"  # change to your SQLite file

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn

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
        results_link
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(runner_id, run_date, short_name) DO NOTHING;
    """

    db = get_db()
    with db:
        for r in runs:
            db.execute(
                insert_sql,
                (
                    runner_id,
                    r["Run Date"],
                    r["short_name"],
                    r.get("AgeGrade"),
                    r.get("Event"),
                    r.get("PB?"),
                    r.get("Pos"),
                    r.get("Run Number"),
                    r.get("Time"),
                    r.get("results_link"),
                )
            )

    print(f"{who} - Inserted {len(runs)} runs for runner {runner_id} (skipping existing rows).")
