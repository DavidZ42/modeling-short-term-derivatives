import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# params
S0 = 65000
T_total = 1/365
n_steps = 1440
dt = T_total / n_steps
hours = np.linspace(0, 24, n_steps)
t_axis = np.linspace(0, T_total, n_steps)

# the volatilites
sigmas = [0.3, 0.7, 1.1] # 30%, 70%, 110%
colors = ['green', 'orange', 'purple']

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# dW = sqrt(dt) * Z
np.random.seed(42)
Z = np.random.normal(0, 1, n_steps)

for sigma, color in zip(sigmas, colors):
    S = np.zeros(n_steps)
    S[0] = S0
    
    for i in range(1, n_steps):
        dW = np.sqrt(dt) * Z[i-1]
        S[i] = S[i-1] + sigma * S[i-1] * dW
    
    # tau = T - t
    tau = T_total - t_axis
    tau[tau <= 0] = 1e-9
    
    # pricing func
    d = (np.log(S / S0) - 0.5 * (sigma**2) * tau) / (sigma * np.sqrt(tau))
    prob_path = norm.cdf(d)
    
    ax1.plot(hours, S, color=color, alpha=0.8, label=f'BTC Price ($\sigma$={sigma*100}%)')
    ax2.plot(hours, prob_path, color=color, alpha=0.8, label=f'Prob Path ($\sigma$={sigma*100}%)')

ax1.axhline(S0, color='black', linestyle='--', alpha=0.4, label='Strike ($S_0$)')
ax1.set_ylabel("Price (USD)")
ax1.set_title("Euler-Maruyama BTC Simulation & Derivative Value for Different Volatilities")
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.2)

ax2.set_ylabel("Value $P(S_T > S_0)$")
ax2.set_xlabel("Hours")
ax2.set_ylim(-0.05, 1.05)
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.2)

plt.tight_layout()
plt.savefig('multi_sigma_simulation.png')