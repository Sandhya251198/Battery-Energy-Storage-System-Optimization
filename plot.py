# plot.py  -- plots the one-day run. Needs run_day1.csv
import pandas as pd, matplotlib.pyplot as plt

df = pd.read_csv("run_day1.csv")
fig, ax = plt.subplots(4, 1, figsize=(10, 11), sharex=True)

ax[0].plot(df.t, df.solar_mw, label="solar")
ax[0].plot(df.t, df.wind_mw, label="wind")
ax[0].plot(df.t, df.demand_mw, label="demand", linestyle="--")
ax[0].set_ylabel("MW"); ax[0].legend()

ax[1].plot(df.t, df.price, color="red"); ax[1].set_ylabel("price")

ax[2].plot(df.t, df.soc1, label="BESS-1")
ax[2].plot(df.t, df.soc2, label="BESS-2")
ax[2].set_ylabel("battery level"); ax[2].legend()

ax[3].plot(df.t, df.buy, label="buy")
ax[3].plot(df.t, df.sell, label="sell")
ax[3].plot(df.t, df.curtail, label="curtail")
ax[3].set_ylabel("MW"); ax[3].legend()

for a in ax:
    a.axvspan(44, 56, alpha=0.1, color="gray")    # cloud
    a.axvspan(72, 80, alpha=0.1, color="red")     # price spike
    a.axvspan(84, 92, alpha=0.1, color="orange")  # demand surge
plt.xlabel("15-min step"); plt.tight_layout()
plt.savefig("demo_plot.png", dpi=150); plt.show()
