import requests
import json
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

for i in range(2,28):
    # --- Configuration ---
    EVENT_SLUG = f"bitcoin-up-or-down-on-march-{i}-2026"
    TZ = ZoneInfo("America/New_York")

    # Target dates: March 26, 2026 12:00 PM ET to March 27, 2026 12:00 PM ET
    START_TIME = datetime(2026, 3, i-1, 12, 0, tzinfo=TZ)
    END_TIME = datetime(2026, 3, i, 12, 0, tzinfo=TZ)

    # Standard browser user-agent to avoid basic API blocking
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def get_token_id(slug):
        """Fetches the CLOB Token ID for the 'Up' outcome using Polymarket's Gamma API."""
        gamma_url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        response = requests.get(gamma_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError(f"No event found for slug: {slug}")
            
        # The primary market is typically the first item in the markets array
        market = data[0]["markets"][0]
        
        # clobTokenIds and outcomes are returned as stringified JSON lists
        token_ids = json.loads(market["clobTokenIds"])
        outcomes = json.loads(market["outcomes"])
        
        # Locate the index for "Up" (or fallback to index 0)
        up_index = 0
        for i, outcome in enumerate(outcomes):
            if "Up" in outcome or "Yes" in outcome:
                up_index = i
                break
                
        return token_ids[up_index]

    def get_price_history(token_id, start_dt, end_dt):
        """Fetches minutely price history from Polymarket's CLOB API."""
        # Convert datetime objects to Unix timestamps (seconds)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        
        clob_url = "https://clob.polymarket.com/prices-history"
        params = {
            "market": token_id,
            "startTs": start_ts,
            "endTs": end_ts,
            "fidelity": 1  # 1-minute granularity
        }
        
        response = requests.get(clob_url, params=params, headers=HEADERS)
        response.raise_for_status()
        
        return response.json().get("history", [])

    def write_to_csv(history_data, filename=f"polymarket_btc_up_prices_{i}.csv"):
        """Writes the history array to a CSV, formatting timestamps cleanly."""
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # Including MM-DD in the header/output since the data spans two different days
            writer.writerow(["Time (ET)", "Price"])
            
            for point in history_data:
                # point['t'] is the Unix timestamp, point['p'] is the price
                dt_utc = datetime.fromtimestamp(point['t'], tz=ZoneInfo("UTC"))
                dt_et = dt_utc.astimezone(TZ)
                
                # Formats as '03-26 12:00' to easily distinguish between noon on the 26th vs 27th
                time_str = dt_et.strftime("%m-%d %H:%M")
                writer.writerow([time_str, point['p']])

    def main():
        print(f"Resolving Token ID for event: {EVENT_SLUG}...")
        try:
            token_id = get_token_id(EVENT_SLUG)
            print(f"Token ID found: {token_id}")
            
            print(f"Fetching 1-minute price history from {START_TIME.strftime('%Y-%m-%d %H:%M %Z')} to {END_TIME.strftime('%Y-%m-%d %H:%M %Z')}...")
            history = get_price_history(token_id, START_TIME, END_TIME)
            
            if not history:
                print("No price history returned. (The Polymarket API sometimes returns empty arrays for resolved markets with specific timeframe slices).")
                return
                
            write_to_csv(history)
            print(f"Success! {len(history)} minutely data points saved to polymarket_btc_up_prices_{i}.csv")
            
        except Exception as e:
            print(f"An error occurred: {e}")

    if __name__ == "__main__":
        main()