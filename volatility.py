import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
import glob

# --- 1. Load and Align Real Data ---
# Find all CSV files matching your naming convention (adjust path as needed)
csv_files = glob.glob("./polymarket_btc_up_prices*.csv") 
# Example fallback if glob finds nothing: csv_files = ['file1.csv', 'file2.csv']

real_paths = []
start_time = None
expiry_time = None

for file in csv_files:
    df = pd.read_csv(file)
    # Ensure standard datetime parsing, assuming a standard 24h EOD contract format
    # Note: Adjust the year logic if your CSVs span multiple different dates/years
    if 'Time (ET)' in df.columns:
        df['Time'] = pd.to_datetime('2026-' + df['Time (ET)'])
    else:
        df['Time'] = pd.to_datetime(df['Time'])
        
    df.set_index('Time', inplace=True)
    real_paths.append(df['Price'])

# Combine all real paths into a single DataFrame, aligned by minute
# Using forward fill for any missing minute ticks in specific files
real_df = pd.concat(real_paths, axis=1).ffill()
real_df.columns = [f'Real_Path_{i}' for i in range(len(real_paths))]

# Determine universal start and expiry for the simulation based on the real data bounds
start_time = real_df.index[0]
expiry_time = real_df.index[-1]
P0 = real_df.iloc[0].mean() # Use average starting price for the simulation

# --- 2. Calculate Realized Volatility for Historical Data ---
SECONDS_IN_YEAR = 365 * 24 * 3600
dt_years = 60 / SECONDS_IN_YEAR  # 1 minute in years

# Calculate minute-by-minute differences
real_dP = real_df.diff()

# Calculate 30-minute rolling standard deviation, annualized
rolling_window = 30
real_rolling_vol = real_dP.rolling(window=rolling_window).std() / np.sqrt(dt_years)

# Average the volatility across all historical paths at each minute
real_avg_vol = real_rolling_vol.mean(axis=1)

# --- 3. Run SDE Simulations ---
T_total_seconds = (expiry_time - start_time).total_seconds()
T = T_total_seconds / SECONDS_IN_YEAR
N_steps = int(T_total_seconds / 60)
M_paths = max(50, len(csv_files) * 5) # Simulate a healthy number of paths
dt = T / N_steps

time_grid_seconds = np.linspace(0, T_total_seconds, N_steps + 1)
sim_times = start_time + pd.to_timedelta(time_grid_seconds, unit='s')

paths = np.zeros((N_steps + 1, M_paths))
paths[0] = P0
eps = 1e-6 

for i in range(N_steps):
    t_year = time_grid_seconds[i] / SECONDS_IN_YEAR
    tau = T - t_year
    
    if tau <= 0:
        tau = 1e-10
        
    P_current = paths[i]
    P_clipped = np.clip(P_current, eps, 1 - eps)
    
    volatility = norm.pdf(norm.ppf(P_clipped)) / np.sqrt(tau)
    dW = np.random.normal(0, np.sqrt(dt), M_paths)
    
    P_next = P_current + volatility * dW
    paths[i+1] = np.clip(P_next, 0, 1)

# --- 4. Calculate Realized Volatility for Simulated Data ---
sim_df = pd.DataFrame(paths, index=sim_times)
sim_dP = sim_df.diff()
sim_rolling_vol = sim_dP.rolling(window=rolling_window).std() / np.sqrt(dt_years)
sim_avg_vol = sim_rolling_vol.mean(axis=1)

# --- 5. Visualization ---
plt.figure(figsize=(14, 7))

# Plot the average rolling volatility
plt.plot(sim_avg_vol.index, sim_avg_vol, color='steelblue', linewidth=2.5, label='Simulated SDE Volatility (Mean)')
plt.plot(real_avg_vol.index, real_avg_vol, color='black', linewidth=2.5, label='Actual Historical Volatility (Mean)')

# Add confidence intervals for the simulated volatility (1 standard deviation across paths)
sim_std_vol = sim_rolling_vol.std(axis=1)
plt.fill_between(sim_avg_vol.index, 
                 sim_avg_vol - sim_std_vol, 
                 sim_avg_vol + sim_std_vol, 
                 color='steelblue', alpha=0.2, label='Simulated Volatility ($\pm 1 \sigma$)')

# Formatting
plt.title('Volatility Comparison: SDE vs. Real Order Book Data (30-Min Rolling)', fontsize=14)
plt.xlabel('Time (ET)', fontsize=12)
plt.ylabel('Annualized Rolling Volatility', fontsize=12)

# Format the X-axis to clearly show the day transition
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.legend(loc='upper left')

# Automatically scale the Y-axis to ignore the massive infinity spike in the very last minute
max_y_display = min(sim_avg_vol.iloc[:-10].max() * 1.5, 50) 
if not np.isnan(max_y_display):
    plt.ylim(0, max_y_display)

plt.tight_layout()
plt.show()