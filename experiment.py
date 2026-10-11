import numpy as np, pandas as pd
from sim import *
from optimizer import optimize, DT, SELL_FACTOR, GRID_CARBON_T_PER_MWH

AVG_PRICE = 50  # rough value used to correct for battery energy used up

def random_events(seed):
    r = np.random.default_rng(1000 + seed)
    ev = []
    s = int(r.integers(36, 60))
    ev.append(Event(s, s + int(r.integers(8, 17)), "cloud", float(r.uniform(0.2, 0.6))))
    s = int(r.integers(64, 84))
    ev.append(Event(s, s + int(r.integers(4, 13)), "price_spike", float(r.uniform(30, 80))))
    s = int(r.integers(20, 60))
    ev.append(Event(s, s + int(r.integers(12, 33)), "battery_outage",
                    target=str(r.choice(["BESS-1", "BESS-2"]))))
    s = int(r.integers(60, 88))
    ev.append(Event(s, s + int(r.integers(4, 13)), "demand_surge", float(r.uniform(20, 60))))
    return ev

def stored_mwh(sim):
    return sum(b.soc * b.capacity_mwh for b in sim.batteries)

def run_optimizer(seed, events, weights_fn=None):
    sim = Simulator(days=1, seed=seed, events=events)
    start = stored_mwh(sim)
    cost = carbon = unserved = curtail = 0.0
    for _ in range(STEPS_PER_DAY):
        obs = sim.observe()
        fc = sim.forecast(horizon=16)
        w = weights_fn(obs) if weights_fn else None
        act = optimize(obs, fc, sim.batteries, weights=w)
        if act["status"] != "Optimal":
            return None
        for b in sim.batteries:
            c, d = act["charge_mw"][b.name], act["discharge_mw"][b.name]
            b.soc += (c * b.efficiency * DT - d / b.efficiency * DT) / b.capacity_mwh
        cost += act["step_cost"]
        carbon += act["step_carbon_t"]
        unserved += act["unserved_mw"] * DT
        curtail += (act["curtail_solar_mw"] + act["curtail_wind_mw"]) * DT
        sim.step()
    return {"cost": cost, "carbon": carbon, "unserved": unserved,
            "curtail": curtail, "used_mwh": start - stored_mwh(sim)}

def run_baseline(seed, events):
    sim = Simulator(days=1, seed=seed, events=events)
    cost = carbon = unserved = 0.0
    for _ in range(STEPS_PER_DAY):
        obs = sim.observe()
        sim.forecast(horizon=16)   # keeps random numbers identical to the optimizer run
        net = obs["demand_mw"] - obs["solar_mw"] - obs["wind_mw"]
        if net > 0:
            buy = min(net, obs["line_limit_mw"]); sell = 0
            unserved += (net - buy) * DT
        else:
            buy = 0; sell = min(-net, obs["line_limit_mw"])
        cost += buy * obs["price"] * DT - sell * obs["price"] * SELL_FACTOR * DT
        carbon += buy * DT * GRID_CARBON_T_PER_MWH
        sim.step()
    return {"cost": cost, "carbon": carbon, "unserved": unserved}

def run_experiment(n=20, weights_fn=None, label="optimizer"):
    rows = []
    for seed in range(n):
        ev = random_events(seed)
        o = run_optimizer(seed, ev, weights_fn)
        b = run_baseline(seed, ev)
        if o is None:
            print("solver problem, seed", seed); continue
        fair_cost_saving = b["cost"] - o["cost"] - o["used_mwh"] * AVG_PRICE
        fair_carbon = o["carbon"] + o["used_mwh"] * GRID_CARBON_T_PER_MWH
        rows.append({
            "seed": seed,
            "base_cost": b["cost"], "opt_cost": o["cost"],
            "saving_pct": 100 * fair_cost_saving / b["cost"],
            "carbon_saving_pct": 100 * (b["carbon"] - fair_carbon) / b["carbon"],
            "unserved_opt": o["unserved"], "unserved_base": b["unserved"],
            "curtail": o["curtail"],
        })
        print(f"{label} seed {seed}: saving {rows[-1]['saving_pct']:.1f}%")
    return pd.DataFrame(rows)

if __name__ == "__main__":
    df = run_experiment(20)
    df.to_csv("experiment_results.csv", index=False)
    print()
    print(df[["saving_pct", "carbon_saving_pct", "unserved_opt", "unserved_base", "curtail"]].describe().round(2))
    print("Days where optimizer beat baseline:", int((df.saving_pct > 0).sum()), "of", len(df))

df = pd.read_csv("experiment_results.csv")
print(df.sort_values("saving_pct")[["seed", "saving_pct", "unserved_opt", "unserved_base"]].head(6))
print(df.sort_values("unserved_opt", ascending=False)[["seed", "saving_pct", "unserved_opt", "unserved_base"]].head(6))