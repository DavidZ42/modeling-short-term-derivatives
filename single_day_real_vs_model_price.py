import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from datetime import date, timedelta
from pathlib import Path
import sys

# --- 1. Model Parameters ---
sigma = 0.50  # Assumed annualized volatility of BTC (50%)
SECONDS_IN_YEAR = 365 * 24 * 3600

# THE FIX: Manually input the official Polymarket strike price for days that resolve incorrectly.
# Set to None to default back to using the first row of your Binance CSV.
strike_price_override = None 

# Target a specific day for the plot
target_date = date(2026, 3, 24)
next_date = target_date + timedelta(days=1)
day_str = target_date.strftime('%d') # Extracts '15'
next_day_str = next_date.strftime('%d')

# --- 2. File Paths ---
base_dir = Path('data') 
btc_file_path = base_dir / f"BTCUSDT_Prices_{target_date}_to_{next_date}.csv"
poly_file_path = base_dir / f"polymarket_btc_up_prices_{next_day_str}.csv"

# --- 3. Visualization Setup ---
plt.figure(figsize=(12, 6))

try:
    # --- 4. Process Model Data (from actual BTC underlying) ---
    if not btc_file_path.exists():
        print(f"❌ ERROR: Cannot find the BTC data file at {btc_file_path}")
        sys.exit(1)
        
    btc_df = pd.read_csv(btc_file_path)
    btc_df['Time (ET)'] = pd.to_datetime(btc_df['Time (ET)'])
    
    # --- STRIKE PRICE FIX LOGIC ---
    if strike_price_override is not None:
        S0 = strike_price_override
        print(f"🎯 Using manual strike price override: ${S0:,.2f}")
    else:
        S0 = btc_df['Price'].iloc[0]
        print(f"🎯 Using Binance CSV starting price as strike: ${S0:,.2f}")
        
    final_price = btc_df['Price'].iloc[-1]
    print(f"🏁 Binance CSV final settlement price: ${final_price:,.2f}")
    print(f"⚖️ Model Resolution (UP if final > strike): {'UP (1.0)' if final_price > S0 else 'DOWN (0.0)'}\n")
    
    # Set expiry exactly 24H after the targeted 12:00 PM start
    actual_start_time = btc_df['Time (ET)'].iloc[0].replace(hour=12, minute=0, second=0, microsecond=0)
    expiry_time = actual_start_time + timedelta(days=1)
    
    # Calculate tau
    time_to_expiry_sec = (expiry_time - btc_df['Time (ET)']).dt.total_seconds()
    time_to_expiry_sec = np.clip(time_to_expiry_sec, 1e-6, None) 
    tau = time_to_expiry_sec / SECONDS_IN_YEAR
    
    # Calculate implied price P using real underlying prices
    S_t = btc_df['Price']
    d = (np.log(S_t / S0) - 0.5 * (sigma**2) * tau) / (sigma * np.sqrt(tau))
    P_model = norm.cdf(d)
    
    # Plot Model Data 
    plt.plot(btc_df['Time (ET)'], P_model, color='steelblue', alpha=0.9, linewidth=1.5, label=rf'Model Implied Price ($\sigma$={sigma})')

    # --- 5. Process Real Polymarket Data ---
    if not poly_file_path.exists():
        print(f"❌ ERROR: Cannot find the Polymarket data file at {poly_file_path}")
    else:
        poly_df = pd.read_csv(poly_file_path)
        
        if 'Time (ET)' in poly_df.columns and 'Price' in poly_df.columns:
            poly_df['Time (ET)'] = pd.to_datetime(poly_df['Time (ET)'], format='mixed', errors='coerce')
            poly_df = poly_df.dropna(subset=['Time (ET)'])
            
            # Align the Polymarket dates to the graph window 
            poly_start_time = poly_df['Time (ET)'].iloc[0].replace(hour=12, minute=0, second=0, microsecond=0)
            time_offset = actual_start_time - poly_start_time
            poly_df['Aligned Time'] = poly_df['Time (ET)'] + time_offset

            # Plot Polymarket Data using the aligned time
            plt.plot(poly_df['Aligned Time'], poly_df['Price'], color='darkorange', alpha=0.8, linewidth=1.5, label='Real Polymarket Price')
            
            poly_final_price = poly_df['Price'].iloc[-1]
            print(f"📊 Real Polymarket final traded price: {poly_final_price}")
        else:
            print("❌ ERROR: Polymarket CSV headers don't match 'Time (ET)' and 'Price'.")

except Exception as e:
    print(f"Error loading files: {e}")

# --- 6. Formatting ---
plt.title(f'24H EOD BTC Contract: Model vs Real Polymarket Price ({target_date})', fontsize=14)
plt.xlabel('Time (ET)', fontsize=12)
plt.ylabel('Contract Price (Probability)', fontsize=12)
plt.ylim(-0.05, 1.05)

# Force the X-axis to span exactly 24 hours
plt.xlim(actual_start_time, expiry_time)

plt.axhline(1.0, color='black', linestyle='--', alpha=0.3)
plt.axhline(0.5, color='gray', linestyle=':', alpha=0.5) 
plt.axhline(0.0, color='black', linestyle='--', alpha=0.3)

# Format the X-axis for a continuous 24-hour scale
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

# Generate tick locations every 3 hours
tick_locations = [actual_start_time + timedelta(hours=3*i) for i in range(9)]
plt.xticks(tick_locations, rotation=45)

plt.grid(True, alpha=0.3)
plt.legend(loc='upper left')
plt.tight_layout()

plt.savefig(f"model_vs_real_{target_date}.png")
plt.show()