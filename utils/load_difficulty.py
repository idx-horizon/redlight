import sqlite3
import csv

conn = sqlite3.connect("/home/redagent/apps/website/data/PKRGEO.DB")
cursor = conn.cursor()

with open("/home/redagent/apps/website/data/difficulty.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    
    rows = [
        (
            row["name"],
            row["variant"] or None,
            float(row["difficulty"]) if row["difficulty"] else None,
            row["note"] or None
        )
        for row in reader
    ]

cursor.executemany("""
    INSERT OR REPLACE INTO difficulty (
        name, variant, difficulty, note
    ) VALUES (?, ?, ?, ?)
""", rows)

conn.commit()
conn.close()
