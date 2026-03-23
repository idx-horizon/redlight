import os
import sqlite3
import requests

# ---- Config ----
PARKRUN_EVENTS_URL = "https://images.parkrun.com/events.json"
DB_PATH = "PKRGEO.DB"  # adjust to your path

# ---- Known country mapping ----
DOMAIN_METADATA = {
    "parkrun.org.uk": ("United Kingdom", "GB"),
    "parkrun.us": ("United States", "US"),
    "parkrun.com.au": ("Australia", "AU"),
    "parkrun.ie": ("Ireland", "IE"),
    "parkrun.co.za": ("South Africa", "ZA"),
    "parkrun.co.nz": ("New Zealand", "NZ"),
    "parkrun.ca": ("Canada", "CA"),
    "parkrun.dk": ("Denmark", "DK"),
    "parkrun.fi": ("Finland", "FI"),
    "parkrun.no": ("Norway", "NO"),
    "parkrun.se": ("Sweden", "SE"),
    "parkrun.pl": ("Poland", "PL"),
    "parkrun.it": ("Italy", "IT"),
    "parkrun.jp": ("Japan", "JP"),
    "parkrun.sg": ("Singapore", "SG"),
    "parkrun.lt": ("Lithuania", "LT"),
    "parkrun.my": ("Malaysia", "MY"),
    "parkrun.co.nl": ("Netherlands", "NL"),
    "parkrun.com.de": ("Germany", "DE"),
    "parkrun.co.at": ("Austria", "AT"),
}

# ---- Helpers ----
def iso_to_flag_emoji(iso2):
    if not iso2:
        return None
    return "".join(chr(127397 + ord(c)) for c in iso2.upper())

def guess_iso_from_domain(domain):
    if not domain:
        return None
    tld = domain.split('.')[-1].upper()
    if len(tld) == 2:  # simple ISO alpha-2 guess
        return tld
    return None

# ---- Fetch and normalize JSON ----
def fetch_and_normalize():
    resp = requests.get(PARKRUN_EVENTS_URL, timeout=30)
    resp.raise_for_status()
    raw = resp.json()

    # --- Countries ---
    countries = []
    for code, data in raw["countries"].items():
        bounds = data["bounds"]
        url = data.get("url")
        host = url.replace("www.", "") if url else None

        # Lookup in hardcoded mapping
        country_name, iso_code = DOMAIN_METADATA.get(host, (None, None))

        # Fallback for unknown domains
        if not iso_code and host:
            iso_code = guess_iso_from_domain(host)
            country_name = f"Unknown ({host})"
            print(f"Warning: unknown country domain '{host}', guessed ISO='{iso_code}'")

        countries.append({
            "country_code": int(code),
            "domain": host,
            "country_name": country_name,
            "iso_code": iso_code,
            "flag_emoji": iso_to_flag_emoji(iso_code),
            "min_lon": bounds[0],
            "min_lat": bounds[1],
            "max_lon": bounds[2],
            "max_lat": bounds[3],
        })

    # --- Events ---
    events = []
    for feature in raw["events"]["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]

        events.append({
            "event_id": feature["id"],
            "name": props.get("eventname"),
            "long_name": props.get("EventLongName"),
            "short_name": props.get("EventShortName"),
            "country_code": props.get("countrycode"),
            "location": props.get("EventLocation"),
            "lat": lat,
            "lon": lon,
            "seriesid": props.get("seriesid"),  # 1 = Saturday, 2 = Sunday
        })

    return countries, events

# ---- SQLite ingestion with upserts ----
def store_to_sqlite(db_path, countries, events):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # --- Create tables if missing ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            country_code INTEGER PRIMARY KEY,
            domain TEXT,
            country_name TEXT,
            iso_code TEXT,
            flag_emoji TEXT,
            min_lon REAL,
            min_lat REAL,
            max_lon REAL,
            max_lat REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY,
            name TEXT,
            long_name TEXT,
            short_name TEXT,
            country_code INTEGER,
            location TEXT,
            lat REAL,
            lon REAL,
            seriesid INTEGER,
            FOREIGN KEY(country_code) REFERENCES countries(country_code)
        )
    """)

    # --- Indexes ---
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_country ON events(country_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_geo ON events(lat, lon)")


    # --- views ---
    cur.execute("DROP VIEW IF EXISTS vw_events_enriched")
    cur.execute("""
       CREATE VIEW vw_events_enriched AS
       SELECT
          e.event_id,
          e.name as event_name,
          e.long_name,
          e.location,
          e.seriesid,
          e.lat,
          e.lon,
          c.country_code,
          c.country_name,
          c.iso_code,
          c.flag_emoji
       FROM events e
       LEFT JOIN countries c
           ON e.country_code = c.country_code;
       """)

    cur.execute("DROP VIEW IF EXISTS vw_country_event_counts")
    cur.execute("""
       CREATE VIEW IF NOT EXISTS vw_country_event_counts AS
       SELECT
          c.country_name,
          c.iso_code,
          c.flag_emoji,

          COUNT(CASE WHEN e.seriesid = 1 THEN 1 END) AS standard_events,
          COUNT(CASE WHEN e.seriesid = 2 THEN 1 END) AS junior_events

       FROM countries c
       LEFT JOIN events e
           ON e.country_code = c.country_code

       GROUP BY c.country_name, c.iso_code, c.flag_emoji
       ORDER BY c.country_name;
       """)

    # --- Upsert countries ---
    for country in countries:
        cur.execute("""
            INSERT INTO countries (
                country_code, domain, country_name, iso_code, flag_emoji,
                min_lon, min_lat, max_lon, max_lat
            ) VALUES (
                :country_code, :domain, :country_name, :iso_code, :flag_emoji,
                :min_lon, :min_lat, :max_lon, :max_lat
            )
            ON CONFLICT(country_code) DO UPDATE SET
                domain=excluded.domain,
                country_name=excluded.country_name,
                iso_code=excluded.iso_code,
                flag_emoji=excluded.flag_emoji,
                min_lon=excluded.min_lon,
                min_lat=excluded.min_lat,
                max_lon=excluded.max_lon,
                max_lat=excluded.max_lat
        """, country)

    # --- Upsert events ---
    for event in events:
        cur.execute("""
            INSERT INTO events (
                event_id, name, long_name, short_name, country_code,
                location, lat, lon, seriesid
            ) VALUES (
                :event_id, :name, :long_name, :short_name, :country_code,
                :location, :lat, :lon, :seriesid
            )
            ON CONFLICT(event_id) DO UPDATE SET
                name=excluded.name,
                long_name=excluded.long_name,
                short_name=excluded.short_name,
                country_code=excluded.country_code,
                location=excluded.location,
                lat=excluded.lat,
                lon=excluded.lon,
                seriesid=excluded.seriesid
        """, event)

    conn.commit()
    conn.close()
    print(f"SQLite DB updated successfully: {db_path}")

# ---- Main execution ----
if __name__ == "__main__":
    countries, events = fetch_and_normalize()
    store_to_sqlite(DB_PATH, countries, events)
