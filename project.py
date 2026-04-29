import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from matplotlib.lines import Line2D
from datetime import date, timedelta
from pathlib import Path

sigma = 0.44 # vol, try changing it around
SECONDS_IN_YEAR = 365 * 24 * 3600

start_date = date(2026, 3, 14)
end_date = date(2026, 3, 27)

plt.figure(figsize=(10, 6))
current_date = start_date
files_processed = 0
base_dir = Path('./') 
dummy_start_time = pd.Timestamp('2026-03-14 12:00:00')

while current_date < end_date:
    next_date = current_date + timedelta(days=1)
    file_name = f"BTCUSDT_Prices_{current_date}_to_{next_date}.csv"
    file_path = base_dir / file_name
    
    try:
        df = pd.read_csv(file_path)
        files_processed += 1
    except FileNotFoundError:
        current_date = next_date
        print("skipped")
        continue
        
    df['Time (ET)'] = pd.to_datetime(df['Time (ET)'])
    
    actual_start_time = df['Time (ET)'].iloc[0].replace(hour=12, minute=0, second=0, microsecond=0)
    
    # normalize time
    normalized_time = dummy_start_time + (df['Time (ET)'] - actual_start_time)
    
    S0 = df['Price'].iloc[0]
    
    expiry_time = actual_start_time + timedelta(days=1)
    
    # calc tau
    time_to_expiry_sec = (expiry_time - df['Time (ET)']).dt.total_seconds()
    # clip it so no div by 0
    time_to_expiry_sec = np.clip(time_to_expiry_sec, 1e-6, None) 
    tau = time_to_expiry_sec / SECONDS_IN_YEAR
    S_t = df['Price']
    # calc d from our derived pricing func
    d = (np.log(S_t / S0) - 0.5 * (sigma**2) * tau) / (sigma * np.sqrt(tau))
    P = norm.cdf(d)
    
    plt.plot(normalized_time, P, color='steelblue', alpha=0.4, linewidth=1.5)
    
    current_date = next_date

plt.title(f'24H EOD BTC Contracts: Overlay of Daily Paths ($\sigma$={sigma})', fontsize=14)
plt.xlabel('Time of Day (ET)', fontsize=12)
plt.ylabel('Contract Price (Probability P)', fontsize=12)
plt.ylim(-0.05, 1.05)
plt.axhline(1.0, color='black', linestyle='--', alpha=0.3)
plt.axhline(0.5, color='gray', linestyle=':', alpha=0.5) 
plt.axhline(0.0, color='black', linestyle='--', alpha=0.3)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
tick_locations = [dummy_start_time + timedelta(hours=3*i) for i in range(9)]
plt.xticks(tick_locations, rotation=45)
plt.grid(True, alpha=0.3)
data_line = Line2D([0], [0], color='steelblue', alpha=0.6, linewidth=1.5, label='Theoretical Derivative Price')
plt.legend(handles=[data_line], loc='upper left')
plt.tight_layout()
plt.savefig("multi_day_overlay_implied_price.png")
plt.show()