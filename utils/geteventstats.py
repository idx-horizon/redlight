import sqlite3
import requests
import time
import random
from bs4 import BeautifulSoup

def get_parkrun_stats_by_url(url):
    """
    Fetches and parses summary statistics for a given parkrun location URL.
    """
    url = url.strip()
    if not url.endswith('/'):
        url += '/'
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            return {"Status": "404 Not Found"}
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        stats_container = soup.find('div', id='footerStats')
        if not stats_container:
            return {"Status": "Footer stats component not found"}
            
        # Initialize dictionary with default safe values
        stats = {
            "Status": "Success",
            "Location Name": None,
            "Events": 0,
            "Finishers": 0,
            "Finishes": 0,
            "Volunteers": 0,
            "PBs": 0,
            "Average finish time": "00:00:00",
            "Groups": 0,
            "Stats Last Updated": None
        }
        
        # Extract location display name
        heading = stats_container.find('h3')
        if heading:
            stats['Location Name'] = heading.text.replace("event statistics", "").strip()
        else:
            title_tag = soup.find('title')
            if title_tag:
                stats['Location Name'] = title_tag.text.split('|')[1].strip() if '|' in title_tag.text else title_tag.text.strip()
            
        # Map the text metrics to our dictionary keys
        for stat_div in stats_container.find_all('div', class_='aStat'):
            text = stat_div.text
            num_span = stat_div.find('span', class_='num')
            if num_span:
                raw_metric = text.split(':')[0].strip()
                val = num_span.text.strip()
                
                # Clean integers (remove commas like '1,154' -> '1154')
                if raw_metric in ["Events", "Finishers", "Finishes", "Volunteers", "PBs", "Groups"]:
                    stats[raw_metric] = int(val.replace(',', ''))
                else:
                    stats[raw_metric] = val
                    
        # Extract the footer update timestamp string
        last_updated_div = stats_container.find('div', class_='lastupdated')
        if last_updated_div:
            stats['Stats Last Updated'] = last_updated_div.text.replace('Stats last updated:', '').strip()
            
        return stats

    except Exception as e:
        return {"Status": f"Failed: {e}"}

def test_scraper(db_path, max_records=10):
    """
    Runs the scraper against the database URLs, limited to max_records for testing.
    """
    url_query = """
      SELECT e.event_id, 'https://' || c.domain || '/' || e.name 
      FROM events e 
      LEFT JOIN countries c ON (c.country_code = e.country_code)
      LEFT JOIN event_stats s ON (e.event_id = s.event_id)
      WHERE s.event_id IS NULL
      AND e.country_code = 97
      AND e.seriesid = 1
      """

    
    insert_query = """
    INSERT OR REPLACE INTO event_stats (
        event_id, display_name, events_count, finishers, finishes, 
        volunteers, pbs, average_time, groups_count, stats_last_updated, last_updated
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """
    
    try:
        conn = sqlite3.connect(db_path)
        # Explicitly enable foreign keys to support cascade actions if needed
        conn.execute("PRAGMA foreign_keys = ON;")
        
        cursor = conn.cursor()
        cursor.execute(url_query)
        rows = cursor.fetchall()
        
        total_available = len(rows)
        run_count = min(max_records, total_available)
        
        print(f"Found {total_available} total URLs. Testing with the first {run_count} records...\n")
        
        for index in range(run_count):
            event_id, url = rows[index]
            print(f"[{index + 1}/{run_count}] Fetching Event ID {event_id}: {url}")
            
            result = get_parkrun_stats_by_url(url)
            
            if result["Status"] == "Success":
                # Execute the database write
                cursor.execute(insert_query, (
                    event_id,
                    result["Location Name"],
                    result["Events"],
                    result["Finishers"],
                    result["Finishes"],
                    result["Volunteers"],
                    result["PBs"],
                    result["Average finish time"],
                    result["Groups"],
                    result["Stats Last Updated"]
                ))
                conn.commit()
                print(f" -> Successfully saved: {result['Location Name']} (Events: {result['Events']})")
            else:
                print(f" -> Skipped: {result['Status']}")
                
            # Pause briefly after each request (except the absolute last one)
            if index < run_count - 1:
                pause_duration = random.uniform(1.0, 3.0)  # Sleep between 2 and 4 seconds
                print(f"    Pausing for {pause_duration:.2f} seconds...")
                time.sleep(pause_duration)
                
        print("\nTest completed successfully. Database updated.")
        
    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# --- Execution ---
if __name__ == "__main__":
    DATABASE_FILE = "data/PKRGEO.DB"
    test_scraper(DATABASE_FILE, max_records=20)
