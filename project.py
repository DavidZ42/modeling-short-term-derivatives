import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from matplotlib.lines import Line2D

# --- 1. Real Data Setup ---
# Load the actual data from your CSV
df = pd.read_csv("./polymarket_btc_up_prices.csv")

# Parse the 'Time (ET)' column into proper datetime objects
# We prepend '2026-' to match your target year
df['Time'] = pd.to_datetime('2026-' + df['Time (ET)'])

# Set expiry to the exact final minute in the dataset
expiry_time = df['Time'].iloc[-1]

# SDE parameters derived directly from the real data's starting point
start_time = df['Time'].iloc[0]
P0 = df['Price'].iloc[0]

# --- 2. Simulation Setup ---
# Total time from start to expiry in seconds and years
T_total_seconds = (expiry_time - start_time).total_seconds()
SECONDS_IN_YEAR = 365 * 24 * 3600
T = T_total_seconds / SECONDS_IN_YEAR

# Align simulation steps to the total minutes in the timeframe
N_steps = int(T_total_seconds / 60)
M_paths = 10 
dt = T / N_steps

# Create a time grid for the simulation (in seconds), map to datetimes for plotting
time_grid_seconds = np.linspace(0, T_total_seconds, N_steps + 1)
sim_times = start_time + pd.to_timedelta(time_grid_seconds, unit='s')

paths = np.zeros((N_steps + 1, M_paths))
paths[0] = P0
eps = 1e-6 

# --- 3. Euler-Maruyama Simulation ---
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

# --- 4. Visualization ---
plt.figure(figsize=(14, 7))

# Plot simulated paths 
plt.plot(sim_times, paths, color='steelblue', alpha=0.5, linewidth=1)

# Plot actual empirical data on top
plt.plot(df['Time'], df['Price'], color='black', linewidth=2.0, label='Actual Historical Path')

# Formatting
plt.title('24H EOD BTC Contract: SDE Simulations vs. Actual Data', fontsize=14)
plt.xlabel('Time (ET)', fontsize=12)
plt.ylabel('Contract Price (Probability)', fontsize=12)
plt.ylim(-0.05, 1.05)
plt.axhline(1.0, color='black', linestyle='--', alpha=0.3)
plt.axhline(0.0, color='black', linestyle='--', alpha=0.3)

# Format the X-axis to clearly show the day transition
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)

# Add a custom legend
handles, labels = plt.gca().get_legend_handles_labels()
sim_line = Line2D([0], [0], color='steelblue', alpha=0.8, label='Simulated Paths (SDE)')
handles.append(sim_line)
plt.legend(handles=handles, loc='upper left')

plt.tight_layout()
plt.show()