import os
import math
from bs4 import BeautifulSoup
import requests
import sqlite3
from flask import current_app
from flask_login import current_user

from utils.user import get_user_settings

def get(url):

    headers = {
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:68.0) Gecko/20100101 Firefox/68.0"
    }

    session = requests.Session()
    session.headers.update(headers)
    return session.get(url)

def get_map_uk_notrun(runner_id):

    PKRGEO_DB_PATH = os.environ['DB_PKRGEO']

    conn = sqlite3.connect(PKRGEO_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
      SELECT
        e.long_name,
        e.short_name AS name,
        e.lat,
        e.lon
      FROM events AS e
      WHERE e.country_code = 97
        AND e.seriesID = 1
        AND NOT EXISTS (
                 SELECT 1
                 FROM runs AS r
                 WHERE r.runner_id = ?
                   AND r.short_name = e.short_name
                )
      ORDER BY e.long_name;
     """

    cur.execute(query, (runner_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def  get_map_user_events(runner_id):

    PKRGEO_DB_PATH = os.environ['DB_PKRGEO']

#    settings = get_user_settings(current_user.username)
#    runner_id = settings.get('runner_id')
    
    conn = sqlite3.connect(PKRGEO_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = """
    SELECT
        e.long_name,
        e.short_name as name,
        lat,
        lon,
        count(*) as num_runs
    FROM events as e
    LEFT JOIN runs as r
        ON e.name = r.short_name
    WHERE  runner_id =  ?
    GROUP BY e.long_name
    ORDER BY e.long_name
    """
    cur.execute(query, (runner_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_cancellations():

    URL='https://www.parkrun.org.uk/cancellations'
    data = get(URL).text

    soup = BeautifulSoup(data,'html.parser')

    content = soup.find("div", {"id": "content", "role": "main"})
    sections = {}
    for h2 in content.find_all("h2"):
        ul=h2.find_next_sibling("ul")
        if ul:
            items = [li.get_text(strip=True) for li in ul.find_all("li")]
            sections[h2.get_text(strip=True)] = items

    return sections

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance in kilometers between two points using the Haversine formula.
    """
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def sqlite_distance_expr(user_lat, user_lon):
    """
    Returns a SQLite SQL snippet to compute distance_km dynamically in a query.
    """
    return f"""(
        6371 * acos(
            cos(radians({user_lat})) * cos(radians(lat)) *
            cos(radians(lon) - radians({user_lon})) +
            sin(radians({user_lat})) * sin(radians(lat))
        )
    ) AS distance_km"""


