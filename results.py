import pandas as pd

df = pd.read_csv("experiment_results.csv")
print(df[["unserved_opt", "unserved_base"]].mean().round(2))
print("days:", len(df))
print(df[["unserved_opt", "unserved_base"]].sum().round(1))