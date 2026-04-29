import pandas as pd
import matplotlib.pyplot as plt
import glob

files = glob.glob("polymarket_btc_up_prices_*.csv")
files.sort()

plt.figure(figsize=(12, 7))

# add all the files to plot
for file in files:
    df = pd.read_csv(file)
    day_label = file.split('_')[-1].replace('.csv', '')
    plt.plot(df.index, df['Price'], label=f"Day {day_label}", alpha=0.7)

plt.title('Comparison of BTC "Up" Derivative Prices Across Multiple Days', fontsize=14)
plt.xlabel('Minutes into 24-Hour Window', fontsize=12)
plt.ylabel('Price (Probability)', fontsize=12)

plt.xticks(range(0, 1441, 120), [f"{h}h" for h in range(0, 25, 2)])

plt.ylim(0, 1)
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend(title="Dataset", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()

plt.savefig('multi_day_comparison.png')
plt.show()