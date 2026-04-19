import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm
from matplotlib.lines import Line2D

# --- 1. Simulation Parameters ---
# Since the CSV data was removed, we define the start, expiry, and initial price manually.
start_time = pd.Timestamp('2026-04-19 12:00:00') 
expiry_time = start_time + pd.Timedelta(hours=24)
P0 = 0.50  # Starting probability/price

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
plt.plot(sim_times, paths, color='steelblue', alpha=0.7, linewidth=1)

# Formatting
plt.title('24H EOD BTC Contract: SDE Simulations', fontsize=14)
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
sim_line = Line2D([0], [0], color='steelblue', alpha=0.8, label='Simulated Paths (SDE)')
plt.legend(handles=[sim_line], loc='upper left')

plt.tight_layout()
plt.savefig("multi_day_simulated.png")
plt.show()