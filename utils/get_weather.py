from utils.db import get_db

def get_weather(db, event_name, lat, lon, run_dt):
    db = get_db("DB_PKRGEO")
    weather = db.execute("""
        SELECT * FROM weather_cache
        WHERE event_name = ? AND run_dt = ?
    """, (event_id, run_dt)).fetchone()

    if weather:
        return weather

    weather = call_weather_api(lat, lon, run_dt)

    db.execute("""
        INSERT INTO weather_cache (...)
        VALUES (...)
    """)

    db.commit()

    return weather
