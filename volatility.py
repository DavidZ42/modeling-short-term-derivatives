import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from matplotlib.lines import Line2D
import glob
import os

file_pattern = "polymarket_btc_up_prices_*.csv"
csv_files = glob.glob(file_pattern) 

if len(csv_files) == 0:
    current_dir = os.getcwd()
    print("file not found")

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
    
    # resample to 1min grid
    df = df.resample('1min').ffill()
    initial_prices.append(df['Price'].iloc[0])
    
    # rolling vol
    dP = df['Price'].diff()
    vol_series = dP.rolling(window=rolling_window).std() / np.sqrt(dt_years)
    vol_df = vol_series.to_frame(name='Volatility')
    
    minutes_elapsed = (vol_df.index - vol_df.index[0]).total_seconds() / 60
    vol_df.index = np.round(minutes_elapsed).astype(int)
    
    vol_df.columns = [f'Real_Path_{len(real_vol_paths)}']
    real_vol_paths.append(vol_df)

real_vol_combined = pd.concat(real_vol_paths, axis=1)

real_avg_vol = real_vol_combined.mean(axis=1)

generic_start = pd.to_datetime('2000-01-01 12:00:00')
generic_time_index = generic_start + pd.to_timedelta(real_avg_vol.index, unit='m')

real_avg_vol.index = generic_time_index
real_vol_combined.index = generic_time_index

total_minutes = real_vol_combined.index[-1] - real_vol_combined.index[0]
T_total_seconds = total_minutes.total_seconds()
T = T_total_seconds / SECONDS_IN_YEAR
N_steps = int(T_total_seconds / 60)
M_paths = len(csv_files)
dt = T / N_steps

#just use avg starting price for sim
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

sim_times = generic_start + pd.to_timedelta(np.linspace(0, T_total_seconds, N_steps + 1), unit='s')
sim_df = pd.DataFrame(paths, index=sim_times)

sim_dP = sim_df.diff()
sim_rolling_vol = sim_dP.rolling(window=rolling_window).std() / np.sqrt(dt_years)

sim_avg_vol = sim_rolling_vol.mean(axis=1)
sim_std_vol = sim_rolling_vol.std(axis=1)

plt.figure(figsize=(14, 7))

plt.plot(sim_avg_vol.index, sim_avg_vol, color='steelblue', linewidth=2.5, label='Simulated SDE Volatility (Mean)')

for col in real_vol_combined.columns:
    plt.plot(real_vol_combined.index, real_vol_combined[col], color='gray', alpha=0.1, linewidth=1.0)

plt.plot(real_avg_vol.index, real_avg_vol, color='black', linewidth=3.0, label='Average Historical Volatility')

plt.title(f'Intraday Volatility Profile: SDE vs. Historical Average ({rolling_window}-Min Rolling Standard Dev)', fontsize=14)
plt.xlabel('Time of Day (Contract Cycle)', fontsize=12)
plt.ylabel('Annualized Rolling Volatility', fontsize=12)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)

handles, labels = plt.gca().get_legend_handles_labels()
real_line = Line2D([0], [0], color='gray', alpha=0.3, lw=1.5, label='Individual Historical Runs')
handles.insert(2, real_line)
plt.legend(handles=handles, loc='upper left')

# scaling axes
max_y_display = min(sim_avg_vol.iloc[:-10].max() * 2.0, 50) 
if not np.isnan(max_y_display):
    plt.ylim(0, max_y_display)

plt.tight_layout()
plt.show()