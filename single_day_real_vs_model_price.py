import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from datetime import date, timedelta
from pathlib import Path
import sys

sigma = 0.44  # volatility (fluctuates, so we just used the one for that year)
SECONDS_IN_YEAR = 365 * 24 * 3600

strike_price_override = None 

# input the day
target_date = date(2026, 3, 24)
next_date = target_date + timedelta(days=1)
day_str = target_date.strftime('%d')
next_day_str = next_date.strftime('%d')

base_dir = Path('data') 
btc_file_path = base_dir / f"BTCUSDT_Prices_{target_date}_to_{next_date}.csv"
poly_file_path = base_dir / f"polymarket_btc_up_prices_{next_day_str}.csv"

plt.figure(figsize=(12, 6))

try:
    if not btc_file_path.exists():
        sys.exit(1)
        
    btc_df = pd.read_csv(btc_file_path)
    btc_df['Time (ET)'] = pd.to_datetime(btc_df['Time (ET)'])
    
    if strike_price_override is not None:
        S0 = strike_price_override
    else:
        S0 = btc_df['Price'].iloc[0]
        
    final_price = btc_df['Price'].iloc[-1]
    
    actual_start_time = btc_df['Time (ET)'].iloc[0].replace(hour=12, minute=0, second=0, microsecond=0)
    expiry_time = actual_start_time + timedelta(days=1)
    
    # calc tau
    time_to_expiry_sec = (expiry_time - btc_df['Time (ET)']).dt.total_seconds()
    time_to_expiry_sec = np.clip(time_to_expiry_sec, 1e-6, None) 
    tau = time_to_expiry_sec / SECONDS_IN_YEAR
    
    # calc implied price using real underlying prices
    S_t = btc_df['Price']
    d = (np.log(S_t / S0) - 0.5 * (sigma**2) * tau) / (sigma * np.sqrt(tau))
    P_model = norm.cdf(d)
    
    plt.plot(btc_df['Time (ET)'], P_model, color='steelblue', alpha=0.9, linewidth=1.5, label=rf'Model Implied Price ($\sigma$={sigma})')

    if not poly_file_path.exists():
        print("error: no data")
    else:
        poly_df = pd.read_csv(poly_file_path)
        
        if 'Time (ET)' in poly_df.columns and 'Price' in poly_df.columns:
            poly_df['Time (ET)'] = pd.to_datetime(poly_df['Time (ET)'], format='mixed', errors='coerce')
            poly_df = poly_df.dropna(subset=['Time (ET)'])
            
            # align dates to graph window
            poly_start_time = poly_df['Time (ET)'].iloc[0].replace(hour=12, minute=0, second=0, microsecond=0)
            time_offset = actual_start_time - poly_start_time
            poly_df['Aligned Time'] = poly_df['Time (ET)'] + time_offset

            plt.plot(poly_df['Aligned Time'], poly_df['Price'], color='darkorange', alpha=0.8, linewidth=1.5, label='Real Polymarket Price')
            
            poly_final_price = poly_df['Price'].iloc[-1]

except Exception as e:
    print(f"error: {e}")

plt.title(f'24H EOD BTC Contract: Model vs Real Polymarket Price ({target_date})', fontsize=14)
plt.xlabel('Time (ET)', fontsize=12)
plt.ylabel('Contract Price (Probability)', fontsize=12)
plt.ylim(-0.05, 1.05)

plt.xlim(actual_start_time, expiry_time)

plt.axhline(1.0, color='black', linestyle='--', alpha=0.3)
plt.axhline(0.5, color='gray', linestyle=':', alpha=0.5) 
plt.axhline(0.0, color='black', linestyle='--', alpha=0.3)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

tick_locations = [actual_start_time + timedelta(hours=3*i) for i in range(9)]
plt.xticks(tick_locations, rotation=45)

plt.grid(True, alpha=0.3)
plt.legend(loc='upper left')
plt.tight_layout()

plt.savefig(f"model_vs_real_{target_date}.png")
plt.show()