import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# --- 1. Simulation Parameters ---
P0 = 0.50               # Initial contract price (Start of day, At-the-money)
hours_to_expiry = 24     # Time to resolution in hours
T = hours_to_expiry / (24 * 365) # Convert to years (standard for SDEs)

N_steps = 500           # Number of discrete time steps
M_paths = 5            # Number of paths to simulate

dt = T / N_steps
time_grid = np.linspace(0, T, N_steps + 1)

# Initialize an array to hold all simulated paths
# Rows = time steps, Columns = individual paths
paths = np.zeros((N_steps + 1, M_paths))
paths[0] = P0

# Epsilon to prevent norm.ppf(0) or norm.ppf(1) from returning -inf / +inf
eps = 1e-6 

# --- 2. Euler-Maruyama Simulation ---
for i in range(N_steps):
    t = time_grid[i]
    tau = T - t
    
    # Prevent division by zero at the exact moment of expiry
    if tau <= 0:
        tau = 1e-10
        
    P_current = paths[i]
    
    # Clip prices to avoid math domain errors in the inverse CDF
    P_clipped = np.clip(P_current, eps, 1 - eps)
    
    # Calculate the instantaneous volatility from the SDE: phi(N^-1(P)) / sqrt(tau)
    volatility = norm.pdf(norm.ppf(P_clipped)) / np.sqrt(tau)
    
    # Generate random Brownian increments (dW)
    dW = np.random.normal(0, np.sqrt(dt), M_paths)
    
    # Calculate the next step
    P_next = P_current + volatility * dW
    
    # Enforce the strict [0, 1] bounds of the binary contract
    paths[i+1] = np.clip(P_next, 0, 1)

# --- 3. Visualization ---
# Convert the time grid back to minutes for a readable X-axis
time_grid_minutes = time_grid * (24 * 365 * 60)

plt.figure(figsize=(12, 7))

# Plot all paths
plt.plot(time_grid_minutes, paths, alpha=0.6, linewidth=1.5)

# Formatting
plt.title(f'Simulated EOD BTC Up/Down Contract Paths\n({M_paths} Paths, {hours_to_expiry} Hours to Expiry, Initial Price = {P0})', fontsize=14)
plt.xlabel('Minutes Elapsed', fontsize=12)
plt.ylabel('Contract Price (Probability)', fontsize=12)
plt.ylim(-0.05, 1.05)
plt.axhline(1.0, color='black', linestyle='--', alpha=0.5)
plt.axhline(0.0, color='black', linestyle='--', alpha=0.5)
plt.grid(True, alpha=0.3)

plt.show()