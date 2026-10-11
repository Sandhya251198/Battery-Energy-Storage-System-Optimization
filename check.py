# check.py  -- exact averages of the 20-day file
import pandas as pd

df = pd.read_csv("experiment_results.csv")
print(df[["saving_pct", "carbon_saving_pct", "unserved_opt", "unserved_base", "curtail"]].mean().round(2))
print("days:", len(df))
print("days optimizer beat baseline:", int((df.saving_pct > 0).sum()))
