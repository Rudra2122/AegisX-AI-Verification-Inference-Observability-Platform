# backend/inferopt/model.py
import torch, torch.nn as nn
class TinyNet(nn.Module):
    def __init__(self, in_dim=64, hidden=128, out_dim=10):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, out_dim)
        )
    def forward(self, x): return self.net(x)

def load_model():
    m = TinyNet(); 
    m.eval(); 
    return m
