# explain.py  -- plain-English explanation of the response to each event. Needs run_day1.csv
import pandas as pd

df = pd.read_csv("run_day1.csv")

EVENTS = {
    30: "BESS-2 goes offline",
    44: "cloud cover hits solar",
    72: "electricity price spikes",
    84: "industrial demand surges",
}

def clock(step):
    return f"{step // 4:02d}:{(step % 4) * 15:02d}"

def explain(step, label):
    r = df[df.t == step].iloc[0]
    p = df[df.t == step - 1].iloc[0]
    out = [f"[{clock(step)}] EVENT: {label}."]
    out.append(f"  Situation: solar {p.solar_mw:.0f} -> {r.solar_mw:.0f} MW, "
               f"price {p.price:.0f} -> {r.price:.0f}, demand {p.demand_mw:.0f} -> {r.demand_mw:.0f} MW.")
    if "offline" in label:
        out.append("  Action: BESS-2 excluded from planning; BESS-1 and the grid cover the load.")
    if r.dis > p.dis + 1:
        out.append(f"  Action: discharged batteries ({p.dis:.0f} -> {r.dis:.0f} MW) to avoid buying at a high price.")
    if r.buy > p.buy + 1:
        out.append(f"  Action: bought more from the grid ({p.buy:.0f} -> {r.buy:.0f} MW) to cover the gap.")
    if r.sell < p.sell - 1:
        out.append(f"  Action: stopped selling ({p.sell:.0f} -> {r.sell:.0f} MW) because power was needed locally.")
    if r.unserved == 0:
        out.append("  Result: demand fully served, no blackout.")
    else:
        out.append(f"  Result: {r.unserved:.1f} MW of demand could not be served.")
    return "\n".join(out)

for step, label in EVENTS.items():
    print(explain(step, label))
    print()
