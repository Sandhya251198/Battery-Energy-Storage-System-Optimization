import pandas as pd
from sim import *
from optimizer import optimize, DT
#%run sim.ipynb
#%run optimizer.ipynb
events = [
    Event(44, 56, "cloud", 0.35),
    Event(72, 80, "price_spike", 60),
    Event(30, 60, "battery_outage", target="BESS-2"),
    Event(84, 92, "demand_surge", 40),
]
sim = Simulator(days=1, events=events)
log = []

for _ in range(STEPS_PER_DAY):
    obs = sim.observe()
    fc = sim.forecast(horizon=16)
    act = optimize(obs, fc, sim.batteries)
    if act["status"] != "Optimal":
        print("solver problem at", sim.t, act); break

    # apply the action to the batteries
    for b in sim.batteries:
        c, d = act["charge_mw"][b.name], act["discharge_mw"][b.name]
        b.soc += (c * b.efficiency * DT - d / b.efficiency * DT) / b.capacity_mwh

    log.append({**{k: obs[k] for k in ["t", "solar_mw", "wind_mw", "demand_mw", "price"]},
                "buy": act["buy_mw"], "sell": act["sell_mw"],
                "chg": sum(act["charge_mw"].values()),
                "dis": sum(act["discharge_mw"].values()),
                "curtail": act["curtail_solar_mw"] + act["curtail_wind_mw"],
                "unserved": act["unserved_mw"],
                "soc1": sim.batteries[0].soc, "soc2": sim.batteries[1].soc,
                "cost": act["step_cost"], "carbon": act["step_carbon_t"]})
    sim.step()

df = pd.DataFrame(log)
print(df[["cost", "carbon", "curtail", "unserved"]].sum())
df.to_csv("run_day1.csv", index=False)