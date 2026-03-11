import requests
import json
import pprint as pp
from datetime import datetime, date
import os
#os.chdir('utils')
from utils.db import get_db
#os.chdir('..')
DB_PKRGEO = 'data/PKRGEO.DB'

# === Weather code mapping ===
weather_code_map = {
    0: {"desc": "Clear sky", "icon": "☀️"},
    1: {"desc": "Mainly clear", "icon": "🌤"},
    2: {"desc": "Partly cloudy", "icon": "⛅"},
    3: {"desc": "Overcast", "icon": "☁️"},
    45: {"desc": "Fog", "icon": "🌫"},
    48: {"desc": "Depositing rime fog", "icon": "🌫"},
    51: {"desc": "Light drizzle", "icon": "🌦"},
    53: {"desc": "Moderate drizzle", "icon": "🌦"},
    55: {"desc": "Dense drizzle", "icon": "🌧"},
    56: {"desc": "Light freezing drizzle", "icon": "🌧"},
    57: {"desc": "Dense freezing drizzle", "icon": "🌧"},
    61: {"desc": "Slight rain", "icon": "🌦"},
    63: {"desc": "Moderate rain", "icon": "🌧"},
    65: {"desc": "Heavy rain", "icon": "🌧🌧"},
    66: {"desc": "Light freezing rain", "icon": "🌧"},
    67: {"desc": "Heavy freezing rain", "icon": "🌧🌧"},
    71: {"desc": "Slight snow fall", "icon": "❄️"},
    73: {"desc": "Moderate snow fall", "icon": "❄️"},
    75: {"desc": "Heavy snow fall", "icon": "❄️"},
    77: {"desc": "Snow grains", "icon": "❄️"},
    80: {"desc": "Slight rain showers", "icon": "🌦"},
    81: {"desc": "Moderate rain showers", "icon": "🌧"},
    82: {"desc": "Violent rain showers", "icon": "⛈"},
    85: {"desc": "Slight snow showers", "icon": "❄️"},
    86: {"desc": "Heavy snow showers", "icon": "❄️"},
    95: {"desc": "Thunderstorm", "icon": "⛈"},
    96: {"desc": "Thunderstorm with slight hail", "icon": "⛈"},
    99: {"desc": "Thunderstorm with heavy hail", "icon": "⛈"},
}

def get_weather(event_name, run_dt):
    yyyy_mm_dd = datetime.strptime(run_dt, '%d/%m/%Y').strftime('%Y-%m-%d'),

    db = get_db(DB_PKRGEO)
    weather = db.execute("""
        SELECT * FROM weather_cache
        WHERE event_name = ? AND run_dt = ?
    """, (event_name, run_dt)).fetchone()

    if weather:
        return json.loads(weather['payload'])

    params = get_lat_lon(event_name)

    if params:
        params['run_dt']  = yyyy_mm_dd
        try:
            weather = json.dumps(call_weather_api(**params))
        except:
            print(f'Failure to call weather api - event:  {event_name}')
            return {}
        db.execute("""
            INSERT INTO weather_cache (event_name, run_dt, payload)
            VALUES (?,?,?)
        """, (event_name, run_dt, weather))

        db.commit()

        return weather

def call_weather_api(lat, lon, run_dt, event=None, timezone="auto"):
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": run_dt,
        "end_date": run_dt,
        "hourly": "temperature_2m,precipitation,weathercode,wind_speed_10m",
        "timezone": timezone
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        times = data["hourly"]["time"]
        temps = data["hourly"]["temperature_2m"]
        precs = data["hourly"]["precipitation"]
        codes = data["hourly"]["weathercode"]
        winds = data["hourly"]["wind_speed_10m"]

        for i, time_str in enumerate(times):
            dt = datetime.fromisoformat(time_str)
            if dt.hour == 9:
                temp = temps[i]
                precip = precs[i]
                code = codes[i]
                wind = winds[i]
                description = weather_code_map.get(code, f"Unknown code: {code}")['desc']
                return {'dt': dt.strftime('%d-%b-%Y %H:%M'),
                        'temp': temp,
                        'precip': precip,
                        'wind': wind,
                        'description': weather_code_map.get(code, {}).get("desc", "Unknown"),
                        'icon': weather_code_map.get(code, {}).get("icon", "❓")
                }
    else:
        print("Request failed:", response.status_code, response.text)
        return {}

def get_lat_lon(event_name):
    db = get_db(DB_PKRGEO)
    row = db.execute('select lat, lon from events where name = ?', (event_name,)).fetchone()
    if row:
        return {'lat': row['lat'], 'lon': row['lon'] } 
    else:
        return None

def build_event_list():
    db = get_db(DB_PKRGEO)
    row = db.execute('select name, lat, lon from events').fetchall()
    data = {'lat': r['lat'], 'lon': r['lon'] }

    return data


if __name__ == "__main__":
#     === Example usage ===
#    lon, lat = [-0.148616, 50.841557]
#    data = get_weather(event_name='Test', lat=lat, lon=lon, run_dt="2026-01-04")  # London
#    print(data)

    with open('data/runners/184594.json','r',encoding='utf-8') as f:
        runner_runs = json.loads(f.read())[1]['runs'][0:1000]

    print(runner_runs[0])

    for r in runner_runs:
        print(get_weather(r['short_name'], r['Run Date']))
