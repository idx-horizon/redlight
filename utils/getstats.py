import requests
from bs4 import BeautifulSoup

def get_parkrun_stats(location_slug):
    """
    Fetches summary statistics for a given parkrun location.
    
    :param location_slug: The URL slug for the event (e.g., 'abbotswood', 'eastbourne', 'brooklands')
    """
    # Clean the slug for the URL format
    location_slug = location_slug.lower().replace("’", "").replace("'", "").replace(" ", "")
    url = f"https://www.parkrun.org.uk/{location_slug}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            print(f"Error: Location '{location_slug}' not found (404). Check the slug name.")
            return None
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the footer stats container
        stats_container = soup.find('div', id='footerStats')
        if not stats_container:
            print("Could not find the statistics block on this page.")
            return None
            
        stats = {}
        
        # Extract the event name safely from the heading
        heading = stats_container.find('h3')
        if heading:
            stats['Location Name'] = heading.text.replace("event statistics", "").strip()
            
        # Iterate through each stat card block
        for stat_div in stats_container.find_all('div', class_='aStat'):
            text = stat_div.text
            num_span = stat_div.find('span', class_='num')
            
            if num_span:
                # Extract the metric name (e.g., "Events", "Finishers")
                metric_name = text.split(':')[0].strip()
                # Extract the numerical value
                metric_value = num_span.text.strip()
                stats[metric_name] = metric_value
                
        # Extract the "last updated" timestamp if available
        last_updated_div = stats_container.find('div', class_='lastupdated')
        if last_updated_div:
            stats['Last Updated'] = last_updated_div.text.replace('Stats last updated:', '').strip()
            
        return stats

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the page: {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # You can supply standard slugs like "abbotswood", "eastbourne", or "brooklands"
    target_location = "abbotswood" 
    
    print(f"Fetching stats for {target_location}...")
    results = get_parkrun_stats(target_location)
    
    if results:
        print("\n--- Extracted Data ---")
        for key, value in results.items():
            print(f"{key}: {value}")
