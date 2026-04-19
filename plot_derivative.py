import pandas as pd
import matplotlib.pyplot as plt
import glob

# 1. Find all files matching the pattern
files = glob.glob("polymarket_btc_up_prices_*.csv")
files.sort()  # Sorts them numerically/alphabetically

plt.figure(figsize=(12, 7))

# 2. Loop through each file and add it to the plot
for file in files:
    df = pd.read_csv(file)
    
    # We use df.index as the X-axis so every day starts at "Minute 0"
    # This makes the patterns comparable across different days.
    day_label = file.split('_')[-1].replace('.csv', '')
    plt.plot(df.index, df['Price'], label=f"Day {day_label}", alpha=0.7)

# 3. Formatting the plot
plt.title('Comparison of BTC "Up" Derivative Prices Across Multiple Days', fontsize=14)
plt.xlabel('Minutes into 24-Hour Window', fontsize=12)
plt.ylabel('Price (Probability)', fontsize=12)

# Set x-ticks to represent hours (every 120 minutes = 2 hours)
plt.xticks(range(0, 1441, 120), [f"{h}h" for h in range(0, 25, 2)])

plt.ylim(0, 1)
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend(title="Dataset", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()

# Save the comparison chart
plt.savefig('multi_day_comparison.png')
plt.show()