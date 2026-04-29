import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

SYMBOL = "BTCUSDT"
MARKET = "spot"
INTERVAL = "1m"

#noon start and end dates
START_DATE = "2026-03-14"
END_DATE = "2026-03-27"

EASTERN = ZoneInfo("America/New_York")
BASE_URL = "https://data.binance.vision/data"


def parse_target_date_et(date_str: str) -> datetime:
    y, m, d = map(int, date_str.split("-"))
    return datetime(y, m, d, 12, 0, 0, tzinfo=EASTERN)


def kline_zip_url(symbol: str, utc_day: datetime) -> str:
    day_str = utc_day.strftime("%Y-%m-%d")
    return f"{BASE_URL}/{MARKET}/daily/klines/{symbol}/{INTERVAL}/{symbol}-{INTERVAL}-{day_str}.zip"


def download_zip_bytes(url: str) -> bytes | None:
    r = requests.get(url, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.content


def extract_csv_rows_from_zip(zip_bytes: bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        if not names:
            return []

        csv_name = next((n for n in names if n.endswith(".csv")), names[0])

        with zf.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", newline="")
            reader = csv.reader(text)
            rows = []
            for row in reader:
                if not row:
                    continue
                if row[0] in {"open_time", "open_time_ms"}:
                    continue
                rows.append(row)
            return rows


def raw_ts_to_utc_dt(raw_ts: str) -> datetime:
    ts = int(raw_ts)
    if ts > 10**15:
        return datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


def get_window_start_date(dt_et: datetime):
    if dt_et.hour >= 12:
        return dt_et.date()
    else:
        return dt_et.date() - timedelta(days=1)


def main():
    window_start_et = parse_target_date_et(START_DATE)
    window_end_et = parse_target_date_et(END_DATE)

    window_start_utc = window_start_et.astimezone(timezone.utc)
    window_end_utc = window_end_et.astimezone(timezone.utc)

    # get all the utc days to cover et time window
    current_day_utc = datetime(
        window_start_utc.year, window_start_utc.month, window_start_utc.day, tzinfo=timezone.utc
    )
    end_day_utc_floor = datetime(
        window_end_utc.year, window_end_utc.month, window_end_utc.day, tzinfo=timezone.utc
    )

    days_to_fetch = []
    while current_day_utc <= end_day_utc_floor:
        days_to_fetch.append(current_day_utc)
        current_day_utc += timedelta(days=1)

    print(f"getting {len(days_to_fetch)} utc days")

    total_rows = 0
    missing_days = []
    generated_files = []
    current_window_start = None
    current_file = None
    current_writer = None
    
    base_dir = Path(__file__).resolve().parent

    for day in days_to_fetch:
        url = kline_zip_url(SYMBOL, day)

        zip_bytes = download_zip_bytes(url)
        if zip_bytes is None:
            missing_days.append(day.strftime("%Y-%m-%d"))
            continue

        raw_rows = extract_csv_rows_from_zip(zip_bytes)
        kept = 0

        for row in raw_rows:
            open_dt_utc = raw_ts_to_utc_dt(row[0])
            open_dt_et = open_dt_utc.astimezone(EASTERN)
            
            # filter rows
            if window_start_et <= open_dt_et < window_end_et:
                win_start_date = get_window_start_date(open_dt_et)
                
                #swap files if crossed
                if win_start_date != current_window_start:
                    if current_file is not None:
                        current_file.close()
                    
                    current_window_start = win_start_date
                    win_end_date = current_window_start + timedelta(days=1)
                    
                    file_name = f"{SYMBOL}_Prices_{current_window_start}_to_{win_end_date}.csv"
                    file_path = base_dir / file_name
                    
                    current_file = open(file_path, "w", newline="", encoding="utf-8")
                    current_writer = csv.writer(current_file)
                    current_writer.writerow(["Time (ET)", "Price"])
                    
                    generated_files.append(file_name)
                    print("new file started")

                time_str = open_dt_et.strftime("%Y-%m-%d %H:%M:%S")
                price = row[4]
                current_writer.writerow([time_str, price])
                kept += 1

        total_rows += kept

    if current_file is not None:
        current_file.close()

    print("done")

if __name__ == "__main__":
    main()