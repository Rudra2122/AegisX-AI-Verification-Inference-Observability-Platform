# backend/inferopt/server.py
import time, numpy as np, torch
from .model import load_model
from .tuner import BanditTuner

CPU_COST_PER_HOUR = 0.04  # toy model for cost
REQS_ACCUM_WINDOW = 60.0  # seconds

class InferService:
    def __init__(self):
        self.model = load_model()
        self.tuner = BanditTuner(policy="ucb1")
        self._req_count = 0
        self._window_start = time.time()
        self.utilization = 0.0
        self.cost_per_1k = 0.0

    def _update_window(self, latency_ms, batch):
        self._req_count += batch
        now = time.time()
        dt = now - self._window_start
        if dt >= REQS_ACCUM_WINDOW:
            rps = self._req_count / dt
            # toy utilization: assume 100 rps max capacity
            self.utilization = min(100.0, (rps / 100.0) * 100.0)
            # cost per 1k requests = hourly_cost / (rps*3600/1000)
            denom = max(1e-6, (rps * 3600.0 / 1000.0))
            self.cost_per_1k = CPU_COST_PER_HOUR / denom
            self._req_count = 0
            self._window_start = now

    def infer_once(self, batch=4, workers=1, in_dim=64):
        x = torch.from_numpy(np.random.randn(batch, in_dim).astype("float32"))
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = self.model(x)
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        self._update_window(latency_ms, batch)
        return {
            "batch": batch, "workers": workers, "latency_ms": latency_ms,
            "utilization_percent": self.utilization, "cost_per_1k_requests": self.cost_per_1k
        }

    def auto_infer(self, trials=20):
        results=[]
        for _ in range(trials):
            arm = self.tuner.select_arm()
            out = self.infer_once(batch=arm["batch"], workers=arm["workers"])
            self.tuner.update(arm, out["latency_ms"])
            results.append(out)
        return {"results": results, "tuner": self.tuner.snapshot()}
