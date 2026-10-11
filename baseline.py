# baseline.py  -- no-battery comparison. Run run_loop.py first (needs run_day1.csv)
import pandas as pd
from sim import *
from optimizer import DT, SELL_FACTOR, GRID_CARBON_T_PER_MWH

events = [
    Event(44, 56, "cloud", 0.35),
    Event(72, 80, "price_spike", 60),
    Event(30, 60, "battery_outage", target="BESS-2"),
    Event(84, 92, "demand_surge", 40),
]
sim = Simulator(days=1, events=events)

cost = carbon = unserved = 0
for _ in range(STEPS_PER_DAY):
    obs = sim.observe()
    sim.forecast(horizon=16)          # keeps the random numbers identical to run_loop.py
    net = obs["demand_mw"] - obs["solar_mw"] - obs["wind_mw"]
    if net > 0:
        buy = min(net, obs["line_limit_mw"]); sell = 0
        unserved += (net - buy) * DT
    else:
        buy = 0; sell = min(-net, obs["line_limit_mw"])
    cost += buy * obs["price"] * DT - sell * obs["price"] * SELL_FACTOR * DT
    carbon += buy * DT * GRID_CARBON_T_PER_MWH
    sim.step()

opt = pd.read_csv("run_day1.csv")
print("BASELINE  cost:", round(cost, 1), " carbon:", round(carbon, 1), " unserved:", round(unserved, 2))
print("OPTIMIZER cost:", round(opt.cost.sum(), 1), " carbon:", round(opt.carbon.sum(), 1))
print("Cost saved:", round(cost - opt.cost.sum(), 1))

# fair correction: the optimizer also spent energy that was stored in the batteries
start_mwh = 0.5 * 100 + 0.5 * 60
end_mwh = opt.soc1.iloc[-1] * 100 + opt.soc2.iloc[-1] * 60
used = start_mwh - end_mwh
print("Battery energy used up:", round(used, 1), "MWh")
print("Fair saving:", round(cost - opt.cost.sum() - used * 50, 1))
