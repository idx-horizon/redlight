import json
from utils.db import get_db

def get_runner_results(runner_id=184594):
    with open(f'data/runners/{runner_id}.pkr','r',encoding='utf-8') as f:
        data = json.loads(f.read())

#    Add weather data for runs
    for r in data[1]['runs']:
        r['weather']=get_weather(r['short_name'],r['Run Date'])
    
    return data[1]['runs'], data[1]['title'], data[1]['last_seen_age']
