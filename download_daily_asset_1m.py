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

# set this to whatever day is neededd
TARGET_DATE = "2026-03-10"

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


def row_in_window(row: list[str], window_start_et: datetime, window_end_et: datetime) -> bool:
    open_dt_utc = raw_ts_to_utc_dt(row[0])
    open_dt_et = open_dt_utc.astimezone(EASTERN)
    return window_start_et <= open_dt_et < window_end_et


def normalize_row(row: list[str]) -> list[str]:
    open_dt_utc = raw_ts_to_utc_dt(row[0])
    close_dt_utc = raw_ts_to_utc_dt(row[6])

    open_dt_et = open_dt_utc.astimezone(EASTERN)
    close_dt_et = close_dt_utc.astimezone(EASTERN)

    return [
        row[0],
        open_dt_utc.isoformat(),
        open_dt_et.isoformat(),
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],# volume
        row[6],
        close_dt_utc.isoformat(),
        close_dt_et.isoformat(),
        row[7],
        row[8],
        row[9],
        row[10],
        row[11] if len(row) > 11 else "",
    ]


def main():
    window_start_et = parse_target_date_et(TARGET_DATE)
    window_end_et = window_start_et + timedelta(days=1)

    window_start_utc = window_start_et.astimezone(timezone.utc)
    window_end_utc = window_end_et.astimezone(timezone.utc)

    start_day_utc = datetime(
        window_start_utc.year, window_start_utc.month, window_start_utc.day, tzinfo=timezone.utc
    )
    end_day_utc = datetime(
        window_end_utc.year, window_end_utc.month, window_end_utc.day, tzinfo=timezone.utc
    )

    days_to_fetch = [start_day_utc]
    if end_day_utc != start_day_utc:
        days_to_fetch.append(end_day_utc)

    output_file = (
        Path(__file__).resolve().parent
        / f"{SYMBOL}_{INTERVAL}_{window_start_et.strftime('%Y-%m-%d_%I%M%p_ET')}_to_{window_end_et.strftime('%Y-%m-%d_%I%M%p_ET')}.csv"
    )

    print("utc window:", window_start_utc.isoformat(), "to", window_end_utc.isoformat())

    total_rows = 0
    missing_days = []

    with output_file.open("w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)
        writer.writerow([
            "open_time_raw",
            "open_time_utc",
            "open_time_eastern",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time_raw",
            "close_time_utc",
            "close_time_eastern",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ])

        for day in days_to_fetch:
            url = kline_zip_url(SYMBOL, day)

            zip_bytes = download_zip_bytes(url)
            if zip_bytes is None:
                missing_days.append(day.strftime("%Y-%m-%d"))
                continue

            raw_rows = extract_csv_rows_from_zip(zip_bytes)
            kept = 0

            for row in raw_rows:
                if row_in_window(row, window_start_et, window_end_et):
                    writer.writerow(normalize_row(row))
                    kept += 1

            total_rows += kept
    print(output_file)


if __name__ == "__main__":
    main()