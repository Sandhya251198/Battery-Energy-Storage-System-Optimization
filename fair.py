# fair.py  -- counts unserved energy (blackouts) as a cost. Needs experiment_results.csv
import pandas as pd

df = pd.read_csv("experiment_results.csv")
PENALTY = 200   # $ per MWh of unserved demand (an assumption)

saving = df.saving_pct * df.base_cost / 100
saving_adj = saving + (df.unserved_base - df.unserved_opt) * PENALTY
base_adj = df.base_cost + df.unserved_base * PENALTY
df["saving_pct_fair"] = 100 * saving_adj / base_adj

print(df[["seed", "saving_pct", "saving_pct_fair"]].round(1).to_string(index=False))
print()
print("mean:", round(df.saving_pct_fair.mean(), 1), "%")
print("days optimizer won:", int((df.saving_pct_fair > 0).sum()), "of", len(df))
