from flask import Blueprint, render_template, request, current_app, session, redirect
from flask_login import login_required, current_user
import pandas as pd
import os
import math
import sqlite3

from auth import requires_permission
from utils.db import get_db
from utils.user import get_user_settings, update_user_settings

BP="parkrun"
parkrun_bp = Blueprint(BP, __name__, url_prefix=f"/{BP}")

# ---------------------------------------------------
# Paths
# ---------------------------------------------------

PKRGEO_DB_PATH = '/home/redagent/apps/website/data/PKRGEO.DB'
USER_DB_PATH = '/home/redagent/apps/website/users.db'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

DIFFICULTY_CSV = os.path.join(DATA_DIR, "difficulty.csv")
MOSTEVENTS_CSV = os.path.join(DATA_DIR, "mostevents.csv")
HIGHLIGHT_FILE = os.path.join(DATA_DIR, "highlighted_runners.csv")

# ---------------------------------------------------
# Cached datasets (loaded once at startup)
# ---------------------------------------------------

difficulty_df = None
mostevents_df = None
highlight_ids = []
highlight_map = {}


def load_data():
    global difficulty_df, mostevents_df, highlight_ids, highlight_map

    if difficulty_df is None:
        difficulty_df = pd.read_csv(DIFFICULTY_CSV)
        difficulty_df.fillna("", inplace=True)

    if mostevents_df is None:
        df = pd.read_csv(MOSTEVENTS_CSV)
        df.fillna("", inplace=True)

        # Ensure numeric
        df["Runs"] = pd.to_numeric(df["Runs"], errors="coerce").fillna(0)

        # Absolute ranking (whole dataset)
        df = df.sort_values(by="Runs", ascending=False)
        df["AbsoluteRank"] = df["Runs"].rank(method="min", ascending=False).astype(int)

        mostevents_df = df

    if not highlight_ids and os.path.exists(HIGHLIGHT_FILE):
        h = pd.read_csv(HIGHLIGHT_FILE)
        h["RunnerID"] = h["RunnerID"].astype(str)
        highlight_ids = h["RunnerID"].tolist()
        highlight_map = dict(zip(h["RunnerID"], h["Name"]))


# Load once when blueprint is imported
load_data()

# ---------------------------------------------------
# Parkrun Dashboard
# ---------------------------------------------------
# Precompute global min/max for filter defaults
GLOBAL_MIN_DIFF = float(difficulty_df["difficulty"].min())
GLOBAL_MAX_DIFF = float(difficulty_df["difficulty"].max())

@parkrun_bp.route("/", methods=["GET", "POST"])
@login_required
@requires_permission()
def dashboard():

    # ---------- Difficulty summary ----------
    total_parkruns = len(difficulty_df)

    bucket_order = ["Very Easy", "Easy", "Fair", "Hard", "Very Hard"]

    if "bucket_quantile" in difficulty_df.columns:
        bucket_counts = (
            difficulty_df["bucket_quantile"]
            .value_counts()
            .reindex(bucket_order, fill_value=0)
        )
    else:
        bucket_counts = pd.Series([0]*5, index=bucket_order)

    difficulty_labels = bucket_counts.index.tolist()
    difficulty_values = bucket_counts.values.tolist()

    # ---------- Runner dataset summary ----------
    total_runners = len(mostevents_df)
    total_highlighted = len(highlight_ids)

    # ---------- Runs distribution ----------
    runs_bins = [0, 100, 200, 300, 400, 500, 700, 1000]
    runs_labels = [
        "0–100",
        "100–200",
        "200–300",
        "300–400",
        "400–500",
        "500–700",
        "700+"
    ]

    if "Runs" in mostevents_df.columns:
        runs_hist = (
            pd.cut(
                mostevents_df["Runs"],
                bins=runs_bins,
                labels=runs_labels,
                include_lowest=True
            )
            .value_counts()
            .sort_index()
        )
        runs_values = runs_hist.values.tolist()
    else:
        runs_values = [0] * len(runs_labels)

    return render_template(
        "parkrun/parkrun_dashboard.html",
        page_title="parkrun",
        total_parkruns=total_parkruns,
        total_runners=total_runners,
        total_highlighted=total_highlighted,
        difficulty_labels=difficulty_labels,
        difficulty_values=difficulty_values,
        runs_labels=runs_labels,
        runs_values=runs_values
    )


# ---------------------------------------------------
# Difficulty Route
# ---------------------------------------------------

@parkrun_bp.route("/difficulty")
@login_required
@requires_permission()
def difficulty():
    # Make a copy of your master difficulty DataFrame
    df = difficulty_df.copy()

    # ---------------- Filters ----------------
    # Event name filter
    name_filter = request.args.get("name", "").strip().lower()

    # Difficulty range filter
    try:
        min_diff = float(request.args.get("min_diff", df["difficulty"].min()))
        max_diff = float(request.args.get("max_diff", df["difficulty"].max()))
    except ValueError:
        min_diff = df["difficulty"].min()
        max_diff = df["difficulty"].max()

    # Apply name filter
    if name_filter:
        df = df[df["name"].astype(str).str.lower().str.contains(name_filter)]

    # Apply difficulty filter
    df = df[(df["difficulty"] >= min_diff) & (df["difficulty"] <= max_diff)]

    # ---------------- Compute dataset min/max for form inputs ----------------
    # After filtering by name, we can still compute actual min/max for the remaining data
    dataset_min = df["difficulty"].min() if not df.empty else 0
    dataset_max = df["difficulty"].max() if not df.empty else 0

    # ---------------- Sorting ----------------
    sort_col = request.args.get("sort_col", "difficulty")
    sort_dir = request.args.get("sort_dir", "asc")

    if sort_col in df.columns:
        df = df.sort_values(by=sort_col, ascending=(sort_dir == "asc"))

    # ---------------- Pagination ----------------
    page = int(request.args.get("page", 1))
    per_page = 50
    total_rows = len(df)
    total_pages = max((total_rows - 1) // per_page + 1, 1)

    start = (page - 1) * per_page
    end = start + per_page
    page_df = df.iloc[start:end]

    # ---------------- Convert to dict for template ----------------
    table_data = page_df.to_dict(orient="records")
    columns = list(page_df.columns)

    # ---------------- Render template ----------------
    return render_template(
        "parkrun/difficulty.html",
        page_title="Difficulty",
        table_data=table_data,
        columns=columns,
        name=name_filter,
        min_diff=min_diff,
        max_diff=max_diff,
        global_min=dataset_min,   # actual min for form
        global_max=dataset_max,   # actual max for form
        page=page,
        total_pages=total_pages,
        total_rows=total_rows,
        sort_col=sort_col,
        sort_dir=sort_dir
    )

# ---------------------------------------------------
# Most Events Route (pagination + dual rank)
# ---------------------------------------------------

@parkrun_bp.route("/mostevents")
@login_required
@requires_permission()
def mostevents():
    df = mostevents_df.copy()

    runner_filter = request.args.get("runner_id", "").strip()
    age_filter = request.args.get("age_category", "").strip().lower()

    if runner_filter:
        df = df[df["RunnerID"].astype(str) == runner_filter]

    if age_filter:
        df["AgeCategory"] = df["AgeCategory"].astype(str)
        df = df[df["AgeCategory"].str.lower().str.contains(age_filter)]

    # Filtered ranking
    df = df.sort_values(by="Runs", ascending=False)
    df["FilteredRank"] = df["Runs"].rank(method="min", ascending=False).astype(int)

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 50

    total_rows = len(df)
    total_pages = max(1, math.ceil(total_rows / per_page))

    start = (page - 1) * per_page
    end = start + per_page

    page_df = df.iloc[start:end]

    table_data = page_df.to_dict(orient="records")
    columns = page_df.columns

    return render_template(
        "parkrun/mostevents.html",
        page_title="Most Events",
        table_data=table_data,
        columns=columns,
        runner_id=runner_filter,
        age_category=age_filter,
        page=page,
        total_pages=total_pages,
        total_rows=total_rows,
        highlight_ids=highlight_ids,
        highlight_map=highlight_map
    )

def get_countries_with_event_counts():
    conn = sqlite3.connect(PKRGEO_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
    SELECT 
        c.country_name,
        c.iso_code,
        c.flag_emoji,
        SUM(CASE WHEN e.seriesid=1 THEN 1 ELSE 0 END) AS standard_events,
        SUM(CASE WHEN e.seriesid=2 THEN 1 ELSE 0 END) AS junior_events
    FROM countries c
    LEFT JOIN events e
        ON c.country_code = e.country_code
    GROUP BY c.country_code
    ORDER BY c.country_name
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return rows

@parkrun_bp.route("/countries")
def countries():
    countries_data = get_countries_with_event_counts()
    return render_template(
                "parkrun/countries.html",
                 page_title="Countries",
                 countries=countries_data)

from utils.geo import sqlite_distance_expr

@parkrun_bp.route("/events")
@login_required
def events():
    db = get_db(PKRGEO_DB_PATH)
    user_db = get_db(USER_DB_PATH)
    settings = get_user_settings(user_db, current_user.username)

    home = settings.get("home",{})
    user_lat = home.get("lat", 51.5074)
    user_lon = home.get("lon",-0.1278)

    country = request.args.get("country") 
    # default to UK if nothing provided
    if not country:
       selected_country = "United Kingdom"

    series = request.args.get("series") or "standard"
    search = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 25
    offset = (page - 1) * per_page

    # SQLite snippet for distance
    distance_sql = sqlite_distance_expr(user_lat, user_lon)

    # Base query
    query = f"""
        SELECT *, {distance_sql}
        FROM vw_events_enriched
        WHERE 1=1
    """
    params = []

    if country:
        query += " AND country_name = ?"
        params.append(country)

    if series == "standard":
        query += " AND seriesid = 1"
    elif series == "junior":
        query += " AND seriesid = 2"

    if search:
        search_pattern = search.replace("*", "%") + "%"
        query += " AND LOWER(long_name) LIKE LOWER(?)"
        params.append(search_pattern)

    # Count total rows
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_rows = db.execute(count_query, params).fetchone()[0]

    # Order by distance
    query += " ORDER BY distance_km ASC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    events = db.execute(query, params).fetchall()
    total_pages = (total_rows + per_page - 1) // per_page

    country_rows = db.execute("""
        SELECT DISTINCT country_name
        FROM vw_events_enriched
        ORDER BY country_name
    """).fetchall()

    countries = [row["country_name"] for row in country_rows]
    
    countries = sorted(countries, key=lambda c: (c != "United Kingdom", c))

    # Add All at the end
    countries.append("All")
    current_app.logger.info(countries)

    return render_template(
        "parkrun/events.html",
        page_title="Events",
        events=events,
        countries=countries,
        selected_country=country,
        selected_series=series,
        search=search,
        page=page,
        total_pages=total_pages,
        total_events=total_rows,
        settings_home=home
    )

@parkrun_bp.route("/set-home-event", methods=["POST"])
@login_required
def set_home_event():
    geo_db = get_db(PKRGEO_DB_PATH)
    username = current_user.username
    event_id = int(request.form["event_id"])

    event = geo_db.execute("""
        SELECT event_id, lat, lon, long_name
        FROM vw_events_enriched
        WHERE event_id = ?
    """, (event_id,)).fetchone()

    if not event:
#        flash("Event not found", "danger")
        return redirect(url_for("parkrun.events"))

    # load settings
    user_db=get_db(USER_DB_PATH)
    settings = get_user_settings(user_db, username)

    settings["home"] = {
        "event_id": event["event_id"],
        "lat": event["lat"],
        "lon": event["lon"]
    }

    update_user_settings(user_db, username, settings)

    # keep session in sync
    session["home_lat"] = event["lat"]
    session["home_lon"] = event["lon"]

#    flash(f"Home parkrun set to {event['EventLongName']}", "success")
    return redirect(request.referrer or url_for("parkrun.events"))

from flask import render_template_string
import folium

@parkrun_bp.route("/xxviewmap")
def xxviewmap():
    m = folium.Map(location=[51.5, -0.12], zoom_start=10)
    folium.Marker([51.5, -0.12], popup="London").add_to(m)

    return m._repr_html_()



from flask import render_template
import folium
from folium.plugins import MarkerCluster, HeatMap, Fullscreen
from folium import FeatureGroup, GeoJson, Choropleth, CircleMarker

@parkrun_bp.route("/viewmap")
def viewmap():
    current_app.logger.info('** Building map')
    # --- Center map ---
    m = folium.Map(location=[51.5, -0.12], zoom_start=12, tiles=None)

    # --- Base layers (with proper attribution where needed) ---
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='CartoDB Positron', attr='Map tiles by Carto, © OpenStreetMap contributors').add_to(m)

    # --- Fullscreen button ---
    Fullscreen(position='topright').add_to(m)

    # --- Overlay Layer 1: Marker Cluster (user events) ---
    cluster_group = FeatureGroup(name='Event Locations')
    cluster = MarkerCluster().add_to(cluster_group)

    user_events = [{'lat': 51.5, 'lon': -0.12, 'name': 'Bromley', 'num_runs': 5},]
    
    # Example event data
    for event in user_events:  # user_events = list of objects with lat, lon, name, num_runs
        folium.Marker(
            location=[event["lat"], event["lon"]],
            popup=f'{event["name"]}<br>Runs: {event["num_runs"]}'
        ).add_to(cluster)

    cluster_group.add_to(m)

    # --- Overlay Layer 2: CircleMarkers (optional styling per event) ---
    circle_group = FeatureGroup(name='Event Circles')
    for event in user_events:
        CircleMarker(
            location=[event["lat"], event["lon"]],
            radius=5 + event["num_runs"]*0.5,  # size proportional to runs
            color='blue',
            fill=True,
            fill_opacity=0.6,
            popup=f'{event["name"]}<br>Runs: {event["num_runs"]}'
        ).add_to(circle_group)
    circle_group.add_to(m)

    # --- Overlay Layer 3: HeatMap (density of events) ---
#    heat_group = FeatureGroup(name='Event HeatMap')
#    heat_data = [[event["lat"], event["lon"]] for event in user_events]
#    HeatMap(heat_data, radius=25).add_to(heat_group)
#    heat_group.add_to(m)

    # --- Overlay Layer 4: GeoJSON (example countries overlay) ---
    # Assuming you have a GeoJSON object `countries_geojson`
    # GeoJson(countries_geojson, name='Countries').add_to(m)

    # --- Overlay Layer 5: Choropleth (example counts per country) ---
    # Assuming you have `country_counts` dict: {country_code: count}
    # Choropleth(
    #     geo_data=countries_geojson,
    #     data=country_counts,
    #     columns=['country', 'count'],
    #     key_on='feature.properties.iso_a3',
    #     fill_color='YlGn',
    #     fill_opacity=0.6,
    #     line_opacity=0.4,
    #     legend_name='Number of Events',
    #     name='Country Counts'
    # ).add_to(m)

    # --- Layer Control ---
    folium.LayerControl(collapsed=False, position='topleft').add_to(m)

    # --- Generate HTML for template ---
    rep_map_html = m._repr_html_()
#    current_app.logger.info(f"\n** REPR: {rep_map_html[:500]} - END")
#    map_html = m.get_root().render()
#    map_html = m.get_root().html.render()
#    map_script = m.get_root().script.render()
#    map_header = m.get_root().header.render()

#    current_app.logger.info(f"\n** ROOT: {map_html[:500]} - END**")

    return render_template("parkrun/viewmap.html", page_title="Map", map_html=rep_map_html)
#    return render_template(
#        "parkrun/viewmap.html",
#        map_html=map_html,
#        map_script=map_script,
#        map_header=map_header
#    )

