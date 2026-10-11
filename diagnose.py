# diagnose.py  -- shows the worst days. Needs experiment_results.csv
import pandas as pd

df = pd.read_csv("experiment_results.csv")
cols = ["seed", "saving_pct", "unserved_opt", "unserved_base"]

print("WORST 6 DAYS BY SAVING")
print(df.sort_values("saving_pct")[cols].head(6).round(1))
print()
print("WORST 6 DAYS BY UNSERVED ENERGY")
print(df.sort_values("unserved_opt", ascending=False)[cols].head(6).round(1))
