import requests
import json
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

for i in range(2,28):
    EVENT_SLUG = f"bitcoin-up-or-down-on-march-{i}-2026"
    TZ = ZoneInfo("America/New_York")

    START_TIME = datetime(2026, 3, i-1, 12, 0, tzinfo=TZ)
    END_TIME = datetime(2026, 3, i, 12, 0, tzinfo=TZ)

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def get_token_id(slug):
        gamma_url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        response = requests.get(gamma_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError(f"no event found for{slug}")
            
        market = data[0]["markets"][0]
        
        # returned as str json lists
        token_ids = json.loads(market["clobTokenIds"])
        outcomes = json.loads(market["outcomes"])
        
        # up index
        up_index = 0
        for i, outcome in enumerate(outcomes):
            if "Up" in outcome or "Yes" in outcome:
                up_index = i
                break
                
        return token_ids[up_index]

    def get_price_history(token_id, start_dt, end_dt):
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        
        clob_url = "https://clob.polymarket.com/prices-history"
        params = {
            "market": token_id,
            "startTs": start_ts,
            "endTs": end_ts,
            "fidelity": 1  # 1 min granularity
        }
        
        response = requests.get(clob_url, params=params, headers=HEADERS)
        response.raise_for_status()
        
        return response.json().get("history", [])

    def write_to_csv(history_data, filename=f"polymarket_btc_up_prices_{i}.csv"):
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            writer.writerow(["Time (ET)", "Price"])
            
            for point in history_data:
                dt_utc = datetime.fromtimestamp(point['t'], tz=ZoneInfo("UTC"))
                dt_et = dt_utc.astimezone(TZ)
                
                time_str = dt_et.strftime("%m-%d %H:%M")
                writer.writerow([time_str, point['p']])

    def main():
        try:
            token_id = get_token_id(EVENT_SLUG)
            history = get_price_history(token_id, START_TIME, END_TIME)
            
            if not history:
                print("no hist found")
                return
                
            write_to_csv(history)
            
        except Exception as e:
            print(f"error: {e}")

    if __name__ == "__main__":
        main()