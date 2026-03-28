import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

SYMBOL = "BTCUSDT"
MARKET = "spot"
INTERVAL = "1s"

# Inclusive start date, inclusive end date, both in UTC.
START_DATE = "2026-03-10"
END_DATE = "2026-03-12"

# Save output next to this script.
OUTPUT_FILE = Path(__file__).resolve().parent / f"{SYMBOL}_{INTERVAL}_{START_DATE}_to_{END_DATE}.csv"

BASE_URL = "https://data.binance.vision/data"


def parse_date_utc(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def daterange(start_dt: datetime, end_dt: datetime):
    curr = start_dt
    while curr <= end_dt:
        yield curr
        curr += timedelta(days=1)


def kline_zip_url(symbol: str, day: datetime) -> str:
    yyyy_mm_dd = day.strftime("%Y-%m-%d")
    return (
        f"{BASE_URL}/{MARKET}/daily/klines/"
        f"{symbol}/{INTERVAL}/{symbol}-{INTERVAL}-{yyyy_mm_dd}.zip"
    )


def unix_to_iso_utc(ts: int) -> str:
    # Binance public-data repo notes spot timestamps from 2025-01-01 onward are in microseconds.
    # Older files are commonly milliseconds.
    if ts > 10**15:  # microseconds
        dt = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    else:  # milliseconds
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return dt.isoformat()


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

        # Binance daily ZIPs normally contain exactly one CSV.
        csv_name = next((n for n in names if n.endswith(".csv")), names[0])

        with zf.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", newline="")
            reader = csv.reader(text)
            rows = []
            for row in reader:
                if not row:
                    continue
                # Skip possible header rows if present
                if row[0].lower() in {"open_time", "open_time_ms"}:
                    continue
                rows.append(row)
            return rows


def write_output_header(writer: csv.writer):
    writer.writerow([
        "open_time_raw",
        "open_time_iso",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time_raw",
        "close_time_iso",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ])


def normalize_row(row: list[str]) -> list[str]:
    # Standard Binance kline row:
    # 0 open time
    # 1 open
    # 2 high
    # 3 low
    # 4 close
    # 5 volume
    # 6 close time
    # 7 quote asset volume
    # 8 number of trades
    # 9 taker buy base asset volume
    # 10 taker buy quote asset volume
    # 11 ignore
    open_time = int(row[0])
    close_time = int(row[6])

    return [
        row[0],
        unix_to_iso_utc(open_time),
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        unix_to_iso_utc(close_time),
        row[7],
        row[8],
        row[9],
        row[10],
        row[11] if len(row) > 11 else "",
    ]


def main():
    start_dt = parse_date_utc(START_DATE)
    end_dt = parse_date_utc(END_DATE)
    if end_dt < start_dt:
        raise ValueError("END_DATE must be on or after START_DATE")

    total_rows = 0
    missing_days = []

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)
        write_output_header(writer)

        for day in daterange(start_dt, end_dt):
            url = kline_zip_url(SYMBOL, day)
            print(f"Downloading {url}")

            zip_bytes = download_zip_bytes(url)
            if zip_bytes is None:
                print(f"  Missing archive for {day.date()}")
                missing_days.append(day.strftime("%Y-%m-%d"))
                continue

            raw_rows = extract_csv_rows_from_zip(zip_bytes)
            if not raw_rows:
                print(f"  No rows found for {day.date()}")
                continue

            for row in raw_rows:
                writer.writerow(normalize_row(row))

            total_rows += len(raw_rows)
            print(f"  Wrote {len(raw_rows)} rows")

    print(f"\nDone. Wrote {total_rows} rows to:")
    print(OUTPUT_FILE)

    if missing_days:
        print("\nDays not found in archive:")
        for d in missing_days:
            print(f"  {d}")


if __name__ == "__main__":
    main()