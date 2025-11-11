# backend/inferopt/tuner.py
import math, random
from collections import defaultdict

class BanditTuner:
    """
    Supports epsilon-greedy, UCB1, Thompson Sampling over discrete arms.
    Reward = -latency_ms.
    """
    def __init__(self, arms=None, policy="ucb1", epsilon=0.2):
        self.arms = arms or [
            {"batch":1,"workers":1}, {"batch":4,"workers":1},
            {"batch":8,"workers":2}, {"batch":16,"workers":2}
        ]
        self.policy = policy
        self.epsilon = epsilon
        self.n = defaultdict(int)
        self.sum_reward = defaultdict(float)
        self.sum_sq = defaultdict(float)
        self.t = 0
        self.enabled = True
        self.current = self.arms[0]

    def _avg(self, arm): 
        k=str(arm); return self.sum_reward[k]/self.n[k] if self.n[k]>0 else -9999.0

    def select_arm(self):
        if not self.enabled: return self.current
        self.t += 1
        if self.policy == "epsilon":
            if random.random()<self.epsilon: self.current=random.choice(self.arms)
            else:
                self.current=max(self.arms, key=self._avg)
        elif self.policy == "thompson":
            # Gaussian Thompson Sampling
            best=None; best_s=-1e9
            for a in self.arms:
                k=str(a)
                mu = self._avg(a) if self.n[k]>0 else -50.0
                var = (self.sum_sq[k]/self.n[k] - (mu**2)) if self.n[k]>1 else 25.0
                sample = random.gauss(mu, math.sqrt(max(var,1e-6)))
                if sample>best_s: best_s=sample; best=a
            self.current = best
        else: # UCB1
            def ucb(a):
                k=str(a)
                if self.n[k]==0: return float("inf")
                mu=self._avg(a); return mu + math.sqrt(2*math.log(self.t)/self.n[k])
            self.current = max(self.arms,key=ucb)
        return self.current

    def update(self, arm, latency_ms):
        k=str(arm); r = -float(latency_ms)
        self.n[k]+=1; self.sum_reward[k]+=r; self.sum_sq[k]+=r*r

    def snapshot(self):
        return {
            "enabled": self.enabled, "policy": self.policy,
            "current": self.current,
            "stats": {str(a): {"trials": self.n[str(a)], "avg_reward": (self.sum_reward[str(a)]/self.n[str(a)]) if self.n[str(a)]>0 else None}
                      for a in self.arms}
        }
