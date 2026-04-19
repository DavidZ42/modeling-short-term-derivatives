import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from matplotlib.lines import Line2D
import glob
import os

# --- 1. Load and Align Real Data by "Time Elapsed" ---
file_pattern = "./data/polymarket_btc_up_prices_*.csv"
csv_files = glob.glob(file_pattern) 

if len(csv_files) == 0:
    current_dir = os.getcwd()
    raise FileNotFoundError(f"Could not find any files matching '{file_pattern}'.\nPython is currently looking in: {current_dir}")

SECONDS_IN_YEAR = 365 * 24 * 3600
dt_years = 60 / SECONDS_IN_YEAR  
rolling_window = 120

real_vol_paths = []
initial_prices = []

for file in csv_files:
    df = pd.read_csv(file)
    
    if 'Time (ET)' in df.columns:
        df['Time'] = pd.to_datetime('2026-' + df['Time (ET)'])
    else:
        df['Time'] = pd.to_datetime(df['Time'])
        
    df.set_index('Time', inplace=True)
    df = df[~df.index.duplicated(keep='last')]
    
    # Resample to a strict 1-minute grid to ensure perfect alignment
    df = df.resample('1min').ffill()
    initial_prices.append(df['Price'].iloc[0])
    
    # Calculate Standard Rolling Volatility for this specific historical run BEFORE aligning
    dP = df['Price'].diff()
    vol_series = dP.rolling(window=rolling_window).std() / np.sqrt(dt_years)
    vol_df = vol_series.to_frame(name='Volatility')
    
    # Normalize the index: convert absolute datetime to "Minutes Elapsed" (0, 1, 2... N)
    minutes_elapsed = (vol_df.index - vol_df.index[0]).total_seconds() / 60
    vol_df.index = np.round(minutes_elapsed).astype(int)
    
    vol_df.columns = [f'Real_Path_{len(real_vol_paths)}']
    real_vol_paths.append(vol_df)

# Combine all paths using the normalized "Minutes Elapsed" index
real_vol_combined = pd.concat(real_vol_paths, axis=1)

# Calculate the cross-sectional historical average
real_avg_vol = real_vol_combined.mean(axis=1)

# Map the integer index to a "Generic Day" starting at 12:00 PM for clean X-axis formatting
generic_start = pd.to_datetime('2000-01-01 12:00:00')
generic_time_index = generic_start + pd.to_timedelta(real_avg_vol.index, unit='m')

real_avg_vol.index = generic_time_index
real_vol_combined.index = generic_time_index

# --- 2. Run SDE Simulations ---
total_minutes = real_vol_combined.index[-1] - real_vol_combined.index[0]
T_total_seconds = total_minutes.total_seconds()
T = T_total_seconds / SECONDS_IN_YEAR
N_steps = int(T_total_seconds / 60)
M_paths = len(csv_files) #max(500, len(csv_files) * 5) 
dt = T / N_steps

# Use the average starting price of all historical datasets for the simulation
P0 = np.mean(initial_prices)
paths = np.zeros((N_steps + 1, M_paths))
paths[0] = P0
eps = 1e-6 

for i in range(N_steps):
    t_year = (i * 60) / SECONDS_IN_YEAR
    tau = T - t_year
    
    if tau <= 0:
        tau = 1e-10
        
    P_current = paths[i]
    P_clipped = np.clip(P_current, eps, 1 - eps)
    
    volatility = norm.pdf(norm.ppf(P_clipped)) / np.sqrt(tau)
    dW = np.random.normal(0, np.sqrt(dt), M_paths)
    
    P_next = P_current + volatility * dW
    paths[i+1] = np.clip(P_next, 0, 1)

# --- 3. Calculate Standard Volatility for Simulated Data ---
sim_times = generic_start + pd.to_timedelta(np.linspace(0, T_total_seconds, N_steps + 1), unit='s')
sim_df = pd.DataFrame(paths, index=sim_times)

sim_dP = sim_df.diff()
sim_rolling_vol = sim_dP.rolling(window=rolling_window).std() / np.sqrt(dt_years)

sim_avg_vol = sim_rolling_vol.mean(axis=1)
sim_std_vol = sim_rolling_vol.std(axis=1)

# --- 4. Visualization ---
plt.figure(figsize=(14, 7))

# 1. Plot Simulation Bounds and Mean
# plt.fill_between(sim_avg_vol.index, 
#                  sim_avg_vol - sim_std_vol, 
#                  sim_avg_vol + sim_std_vol, 
#                  color='steelblue', alpha=0.3, label=r'Simulated Volatility ($\pm 1 \sigma$)')
plt.plot(sim_avg_vol.index, sim_avg_vol, color='steelblue', linewidth=2.5, label='Simulated SDE Volatility (Mean)')

# 2. Plot the faint historical background paths to show distribution
for col in real_vol_combined.columns:
    plt.plot(real_vol_combined.index, real_vol_combined[col], color='gray', alpha=0.1, linewidth=1.0)

# 3. Plot the thick historical average on top
plt.plot(real_avg_vol.index, real_avg_vol, color='black', linewidth=3.0, label='Average Historical Volatility')

# Formatting
plt.title(f'Intraday Volatility Profile: SDE vs. Historical Average ({rolling_window}-Min Rolling Standard Dev)', fontsize=14)
plt.xlabel('Time of Day (Contract Cycle)', fontsize=12)
plt.ylabel('Annualized Rolling Volatility', fontsize=12)

# Format the X-axis to clearly show the 24-hour cycle crossing midnight
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)

handles, labels = plt.gca().get_legend_handles_labels()
real_line = Line2D([0], [0], color='gray', alpha=0.3, lw=1.5, label='Individual Historical Runs')
handles.insert(2, real_line)
plt.legend(handles=handles, loc='upper left')

# Automatically scale the Y-axis based on the simulation to ignore massive microstructure spikes
max_y_display = min(sim_avg_vol.iloc[:-10].max() * 2.0, 50) 
if not np.isnan(max_y_display):
    plt.ylim(0, max_y_display)

plt.tight_layout()
plt.show()