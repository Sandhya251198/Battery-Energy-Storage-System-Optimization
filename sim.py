import numpy as np
from dataclasses import dataclass , field

STEPS_PER_DAY = 96

@dataclass
class Battery:
    name : str
    capacity_mwh : float
    max_rate_mwh : float
    efficiency : float = 0.92
    soc : float = 0.5
    available : bool = True

@dataclass 
class Event:
    start : int
    end : int
    kind :str
    value : float = 0.0
    target : str = ""

class Simulator:
    def __init__(self , days =3, seed = 0, events = None):
        self.rng = np.random.default_rng(seed)
        self.t = 0
        self.n = days * STEPS_PER_DAY
        self.solar_caps = [40,35,50,30,45]
        self.wind_caps = [60,45,55]
        self.line_limit = 120.0
        self.batteries = [Battery("BESS-1",100,25),Battery("BESS-2",60,15)]
        self.events = events or []
        w = np.zeros(self.n);w[0] = 0.5
        for i in range(1,self.n):
            w[i] = np.clip(0.97 * w[i-1] + 0.03 * 0.5 + self.rng.normal(0,0.04),0,1)
        self.wind_cf = w
        
    def _hour(self, t):
        return (t % STEPS_PER_DAY) / 4

    def base_solar(self , t):
        h = self._hour(t)
        cf = max(0, np.sin(np.pi * (h - 6) /12 )) if 6 <= h <=18 else 0 
        return sum(self.solar_caps)* cf 

    def base_wind(self , t):
        return sum(self.wind_caps) * self.wind_cf[min(t, self.n-1)]

    def base_price(self , t):
        h = self._hour(t)
        return 40 + 25 * np.exp(-((h-19)**2)/4) + 10*np.exp(-((h-8)**2)/3)

    def base_demand(self , t):
        h = self._hour(t)
        return 150 + 40 * np.sin(np.pi * (h-8) / 12)


    def activate(self , kind):
        return [e for e in self.events if e.kind == kind and e.start <= self.t < e.end]

    def observe(self):
        t = self.t 
        cloud = min([e.value for e in self.activate("cloud")],default = 1.0)
        spike = sum(e.value for e in self.activate("price_spike"))
        surge = sum(e.value for e in self.activate("demand_surge"))
        derate = min([e.value for e in self.activate("line_derate")], default = 1.0)
        down = {e.target for e in self.activate("battery_outage")}
        for b in self.batteries:
            b.available = b.name not in down 
        return { 
            "t" : t , "hour" : self._hour(t),
            "solar_mw" : self.base_solar(t) * cloud,
            "wind_mw" : self.base_wind(t),
            "demand_mw" : self.base_demand(t) + surge + self.rng.normal(0,2),
            "price" : self.base_price(t) + spike,
            "line_limit_mw" : self.line_limit * derate,
            "batteries" : [(b.name , round(b.soc, 2), b.available) for b in self.batteries],
            "activate_events" : [e.kind for e in self.events if e.start <= t < e.end],}

    def forecast(self, horizon = 16):
            out = []
            for k in range(1, horizon + 1):
                t = self.t + k
                err = 0.02 * k 
                out.append({
                    "t" : t ,
                    "solar_mw" : max(0,self.base_solar(t) * (1 + self.rng.normal(0,err))),
                    "wind_mw" : max(0, self.base_wind(t) * (1 + self.rng.normal(0,err))),
                    "demand_mw" : self.base_demand(t) * (1 + self.rng.normal(0,err / 2)),
                    "price" : self.base_price(t),
                })
            return out 

    def step(self):
            self.t += 1