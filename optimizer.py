import pulp

DT = 0.25  # hours per step

DEFAULT_WEIGHTS = {
    "cost": 1.0,        # electricity cost / revenue
    "carbon": 1.0,      # emissions cost
    "curtailment": 1.0, # wasted renewable energy
    "degradation": 1.0, # battery wear
}

# economic constants (tweak freely)
GRID_CARBON_T_PER_MWH = 0.7
CARBON_PRICE = 30.0      # $/tCO2
SELL_FACTOR = 0.9        # you sell at 90% of the market price
CURTAIL_PENALTY = 20.0   # $/MWh of wasted renewable energy
DEGRADATION_COST = 4.0   # $/MWh of battery throughput
UNSERVED_PENALTY = 1000  # $/MWh, makes blackouts a last resort


def optimize(obs, forecast, batteries, weights=None, reserve_frac=0.10):
    """Plan over [now + forecast], return the action for the current step."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    # index 0 = current observation, 1..H = forecast
    solar = [obs["solar_mw"]] + [f["solar_mw"] for f in forecast]
    wind = [obs["wind_mw"]] + [f["wind_mw"] for f in forecast]
    demand = [obs["demand_mw"]] + [f["demand_mw"] for f in forecast]
    price = [obs["price"]] + [f["price"] for f in forecast]
    line = obs["line_limit_mw"]
    T = range(len(solar))
    B = range(len(batteries))

    m = pulp.LpProblem("dispatch", pulp.LpMinimize)

    s_used = pulp.LpVariable.dicts("s_used", T, 0)
    w_used = pulp.LpVariable.dicts("w_used", T, 0)
    buy = pulp.LpVariable.dicts("buy", T, 0, line)
    sell = pulp.LpVariable.dicts("sell", T, 0, line)
    unserved = pulp.LpVariable.dicts("unserved", T, 0)
    chg = pulp.LpVariable.dicts("chg", (B, T), 0)
    dis = pulp.LpVariable.dicts("dis", (B, T), 0)
    soc = pulp.LpVariable.dicts("soc", (B, range(len(solar) + 1)), 0)  # MWh

    for t in T:
        m += s_used[t] <= solar[t]
        m += w_used[t] <= wind[t]
        # energy balance
        m += (s_used[t] + w_used[t] + buy[t] + unserved[t]
              + pulp.lpSum(dis[b][t] for b in B)
              == demand[t] + sell[t] + pulp.lpSum(chg[b][t] for b in B))

    for b in B:
        bat = batteries[b]
        rate = bat.max_rate_mwh if bat.available else 0
        m += soc[b][0] == bat.soc * bat.capacity_mwh
        for t in T:
            m += chg[b][t] <= rate
            m += dis[b][t] <= rate
            m += soc[b][t + 1] == (soc[b][t]
                                   + chg[b][t] * bat.efficiency * DT
                                   - dis[b][t] / bat.efficiency * DT)
        for t in range(len(solar) + 1):
            if t > 0:
                m += soc[b][t] >= reserve_frac * bat.capacity_mwh
                m += soc[b][t] <= 0.95 * bat.capacity_mwh

    avg_price = sum(price) / len(price)

    cost = pulp.lpSum(buy[t] * price[t] * DT - sell[t] * price[t] * SELL_FACTOR * DT
                      for t in T)
    carbon = pulp.lpSum(buy[t] * DT * GRID_CARBON_T_PER_MWH * CARBON_PRICE for t in T)
    curt = pulp.lpSum(((solar[t] - s_used[t]) + (wind[t] - w_used[t])) * DT * CURTAIL_PENALTY
                      for t in T)
    degr = pulp.lpSum((chg[b][t] + dis[b][t]) * DT * DEGRADATION_COST for b in B for t in T)
    blackout = pulp.lpSum(unserved[t] * DT * UNSERVED_PENALTY for t in T)
    # leftover energy in batteries at the end is worth something
    terminal = pulp.lpSum(soc[b][len(solar)] for b in B) * avg_price * 0.8

    m += (w["cost"] * cost + w["carbon"] * carbon + w["curtailment"] * curt
          + w["degradation"] * degr + blackout - terminal)

    m.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[m.status]
    if status != "Optimal":
        return {"status": status}

    v = lambda x: round(x.value() or 0.0, 3)
    return {
        "status": status,
        "buy_mw": v(buy[0]),
        "sell_mw": v(sell[0]),
        "charge_mw": {batteries[b].name: v(chg[b][0]) for b in B},
        "discharge_mw": {batteries[b].name: v(dis[b][0]) for b in B},
        "curtail_solar_mw": round(solar[0] - v(s_used[0]), 3),
        "curtail_wind_mw": round(wind[0] - v(w_used[0]), 3),
        "unserved_mw": v(unserved[0]),
        "step_cost": round(v(buy[0]) * price[0] * DT - v(sell[0]) * price[0] * SELL_FACTOR * DT, 2),
        "step_carbon_t": round(v(buy[0]) * DT * GRID_CARBON_T_PER_MWH, 3),
    }