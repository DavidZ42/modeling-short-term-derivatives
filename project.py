import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from matplotlib.lines import Line2D
from datetime import date, timedelta
from pathlib import Path

# --- 1. Model Parameters ---
sigma = 0.50  # Assumed annualized volatility of BTC (50%)
SECONDS_IN_YEAR = 365 * 24 * 3600

# Define the date range matching your downloaded files
start_date = date(2026, 3, 14)
end_date = date(2026, 3, 27)

# --- 2. Visualization Setup ---
plt.figure(figsize=(10, 6)) # Slightly wider format fits 24h overlays well

# --- 3. Process Data and Calculate P(S,t) ---
current_date = start_date
files_processed = 0

# Base directory where the CSVs are located
base_dir = Path('./') 

# Define a fixed dummy start date to align all paths on the same 24-hour X-axis
dummy_start_time = pd.Timestamp('2026-03-14 12:00:00')

while current_date < end_date:
    next_date = current_date + timedelta(days=1)
    file_name = f"data/BTCUSDT_Prices_{current_date}_to_{next_date}.csv"
    file_path = base_dir / file_name
    
    try:
        # Load the real BTC price data
        df = pd.read_csv(file_path)
        files_processed += 1
    except FileNotFoundError:
        # Skip if the file for this day doesn't exist
        current_date = next_date
        print("skipped!")
        continue
        
    # Convert time to datetime objects
    df['Time (ET)'] = pd.to_datetime(df['Time (ET)'])
    
    # Identify the exact 12:00 PM start time for this specific day's contract
    actual_start_time = df['Time (ET)'].iloc[0].replace(hour=12, minute=0, second=0, microsecond=0)
    
    # Normalize the time so every file starts at dummy_start_time and spans 24H
    normalized_time = dummy_start_time + (df['Time (ET)'] - actual_start_time)
    
    # S0 is the starting price at 12:00 PM for this specific 24H contract
    S0 = df['Price'].iloc[0]
    
    # Expiry time is exactly 24 hours after the intended 12:00 PM start
    expiry_time = actual_start_time + timedelta(days=1)
    
    # Calculate tau (time to expiry in years)
    time_to_expiry_sec = (expiry_time - df['Time (ET)']).dt.total_seconds()
    
    # Clip tau to prevent division by zero at the exact moment of expiry
    time_to_expiry_sec = np.clip(time_to_expiry_sec, 1e-6, None) 
    tau = time_to_expiry_sec / SECONDS_IN_YEAR
    
    # Extract S_t
    S_t = df['Price']
    
    # Calculate d based on your derived equation
    d = (np.log(S_t / S0) - 0.5 * (sigma**2) * tau) / (sigma * np.sqrt(tau))
    
    # Calculate derivative price P (Probability)
    P = norm.cdf(d)
    
    # Plot this day's theoretical derivative price path on the shared axis
    plt.plot(normalized_time, P, color='steelblue', alpha=0.4, linewidth=1.5)
    
    current_date = next_date

if files_processed == 0:
    print("Warning: No CSV files found. Check your file paths and names.")

# --- 4. Formatting ---
plt.title(f'24H EOD BTC Contracts: Overlay of Daily Paths ($\sigma$={sigma})', fontsize=14)
plt.xlabel('Time of Day (ET)', fontsize=12)
plt.ylabel('Contract Price (Probability P)', fontsize=12)
plt.ylim(-0.05, 1.05)
plt.axhline(1.0, color='black', linestyle='--', alpha=0.3)
plt.axhline(0.5, color='gray', linestyle=':', alpha=0.5) 
plt.axhline(0.0, color='black', linestyle='--', alpha=0.3)

# Format the X-axis to just show the hour/minute of the day (e.g., 12:00 PM)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

# Ensure ticks cover the 24 hour range properly (every 3 hours)
tick_locations = [dummy_start_time + timedelta(hours=3*i) for i in range(9)]
plt.xticks(tick_locations, rotation=45)

plt.grid(True, alpha=0.3)

# Add a custom legend
data_line = Line2D([0], [0], color='steelblue', alpha=0.6, linewidth=1.5, label='Theoretical Derivative Price')
plt.legend(handles=[data_line], loc='upper left')

plt.tight_layout()
plt.savefig("multi_day_overlay_implied_price.png")
plt.show()