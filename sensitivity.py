import pandas as pd

df = pd.read_csv("experiment_results.csv")
for pen in [0, 50, 200, 1000]:
    saving = df.saving_pct * df.base_cost / 100 + (df.unserved_base - df.unserved_opt) * pen
    base = df.base_cost + df.unserved_base * pen
    fair = 100 * saving / base
    print(f"penalty {pen:>5}: mean {fair.mean():.1f}%  wins {int((fair > 0).sum())}/20")