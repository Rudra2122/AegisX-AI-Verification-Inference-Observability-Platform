# # backend/api/main.py
# from fastapi import FastAPI, UploadFile, Form, Request
# from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from pydantic import BaseModel
# from pathlib import Path
# import shutil

# from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# from backend.formal_verifier.runner import run_formal
# from backend.inferopt.server import InferService

# app = FastAPI(title="AegisX")
# app.mount("/static", StaticFiles(directory="backend/static"), name="static")
# templates = Jinja2Templates(directory="backend/templates")

# infer = InferService()

# # Prometheus metrics
# infer_latency = Histogram("aegis_infer_latency_ms","Latency (ms)")
# infer_requests = Counter("aegis_infer_requests_total","Total inference requests")
# current_batch = Gauge("aegis_current_batch","Current batch size")
# cost_per_1k = Gauge("aegis_cost_per_1k_requests","Cost per 1000 requests ($)")
# util_pct = Gauge("aegis_utilization_percent","Utilization percent")

# class FormalReq(BaseModel):
#     rtl_path: str
#     top: str = "counter"
#     clk: str = "clk"
#     rst: str = "rst"

# @app.get("/", response_class=HTMLResponse)
# def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.get("/health") 
# def health(): return {"status":"ok"}

# @app.get("/metrics")
# def metrics():
#     return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# @app.post("/formal/run")
# def formal_run(req: FormalReq):
#     p = Path(req.rtl_path)
#     if not p.exists(): return JSONResponse({"error":"rtl_path not found"}, status_code=400)
#     result = run_formal(rtl_path=str(p), top=req.top, clk=req.clk, rst=req.rst)
#     return result

# @app.post("/formal/upload")
# async def formal_upload(file: UploadFile):
#     dst = Path("data/rtl_samples") / file.filename
#     with dst.open("wb") as f: shutil.copyfileobj(file.file, f)
#     return {"saved_as": str(dst)}

# @app.get("/artifact")
# def artifact(rel_path: str):
#     p = Path("data") / rel_path
#     if p.exists() and p.is_file(): return FileResponse(p)
#     return JSONResponse({"error":"artifact not found"}, status_code=404)

# @app.post("/infer/once")
# def infer_once(batch: int = Form(4), workers: int = Form(1)):
#     current_batch.set(batch)
#     with infer_latency.time():
#         out = infer.infer_once(batch=batch, workers=workers)
#     infer_requests.inc(batch)
#     cost_per_1k.set(out["cost_per_1k_requests"])
#     util_pct.set(out["utilization_percent"])
#     return out

# @app.post("/infer/auto")
# def infer_auto(trials: int = Form(20)):
#     r = infer.auto_infer(trials=trials)
#     # push last seen metrics
#     if r["results"]:
#         last = r["results"][-1]
#         cost_per_1k.set(last["cost_per_1k_requests"])
#         util_pct.set(last["utilization_percent"])
#         current_batch.set(last["batch"])
#     return r

# @app.get("/infer/tuner")
# def infer_tuner(): return infer.tuner.snapshot()

# @app.post("/infer/tuner/enable")
# def tuner_enable(enable: bool = Form(True)):
#     infer.tuner.enabled = enable; return infer.tuner.snapshot()

# @app.post("/infer/tuner/policy")
# def tuner_policy(policy: str = Form("ucb1")):
#     infer.tuner.policy = policy; return infer.tuner.snapshot()



# backend/api/main.py
from fastapi import FastAPI, UploadFile, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import shutil
import time

from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

# ---- project-local imports ----
from backend.formal_verifier.runner import run_formal
from backend.inferopt.server import InferService

# -----------------------------------------------------------------------------
# App, static, templates
# -----------------------------------------------------------------------------
app = FastAPI(title="AegisX")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="backend/templates")

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "rtl_samples"   # contains counter.sv, fsm_buggy.sv, etc.

infer = InferService()

# -----------------------------------------------------------------------------
# Prometheus: request-level + domain metrics
# -----------------------------------------------------------------------------
# HTTP layer
AEGIS_REQUESTS = Counter(
    "aegis_requests_total", "Total HTTP requests", ["path", "method", "status"]
)
AEGIS_LATENCY  = Histogram(
    "aegis_latency_ms", "Request latency (ms)",
    buckets=[5,10,25,50,100,200,400,800,1600]
)

# Inference
infer_latency  = Histogram("aegis_infer_latency_ms", "Latency (ms)")
infer_requests = Counter("aegis_infer_requests_total", "Total inference requests")
current_batch  = Gauge("aegis_current_batch", "Current batch size")
cost_per_1k    = Gauge("aegis_cost_per_1k_requests", "Cost per 1000 requests ($)")
util_pct       = Gauge("aegis_utilization_percent", "Utilization percent")

# Formal
formal_runs = Counter(
    "aegis_formal_runs_total", "Formal runs by result", ["kind", "result"]
)

@app.middleware("http")
async def _prom_mw(request: Request, call_next):
    t0 = time.time()
    resp = await call_next(request)
    dt_ms = (time.time() - t0) * 1000.0
    try:
        AEGIS_REQUESTS.labels(request.url.path, request.method, str(resp.status_code)).inc()
        AEGIS_LATENCY.observe(dt_ms)
    except Exception:
        pass
    return resp

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class FormalReq(BaseModel):
    # Backwards-compatible with your UI:
    # - can send explicit rtl_path/top/clk/rst
    # - OR omit rtl_path and let us choose a built-in sample (via kind)
    rtl_path: str | None = None
    top: str | None = None
    clk: str | None = None
    rst: str | None = None
    kind: str = "prove"           # "prove" | "cover" (used when rtl_path is omitted)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ---------- FORMAL ----------
@app.post("/formal/run")
def formal_run(req: FormalReq):
    """
    If req.rtl_path is provided, run formal on that RTL (your current behavior).
    If not, run using built-in samples based on req.kind:
      - prove  => counter.sv (top='counter')
      - cover  => fsm_buggy.sv (runner generates/uses the right harness on your side)
    """
    kind = (req.kind or "prove").lower()
    if kind not in {"prove", "cover"}:
        raise HTTPException(status_code=400, detail="kind must be 'prove' or 'cover'")

    # Decide RTL
    if req.rtl_path:
        rtl_path = Path(req.rtl_path)
        if not rtl_path.is_absolute():
            rtl_path = ROOT / req.rtl_path
    else:
        rtl_path = SAMPLES / ("counter.sv" if kind == "prove" else "fsm_buggy.sv")

    if not rtl_path.exists():
        return JSONResponse({"error": f"rtl_path not found: {rtl_path}"}, status_code=400)

    # Sensible defaults that match your demos
    top = req.top or ("counter" if kind == "prove" else "fsm_buggy_tb")
    clk = req.clk or "clk"
    rst = req.rst or "rst_n"

    # ---- IMPORTANT FIX ----
    # Do NOT pass `kind` into run_formal (runner doesn't accept it).
    result = run_formal(
        rtl_path=str(rtl_path),
        top=top,
        clk=clk,
        rst=rst,
    )

    # Increment formal metrics (still labeled by the UI's intended kind)
    try:
        status = str(result.get("status", "UNKNOWN")).lower()
        formal_runs.labels(kind=kind, result=status).inc()
    except Exception:
        pass

    return result

# Small convenience aliases for buttons that POST without a body
@app.post("/formal/prove")
def formal_prove():
    return formal_run(FormalReq(kind="prove"))

@app.post("/formal/cover")
def formal_cover():
    return formal_run(FormalReq(kind="cover"))

@app.post("/formal/upload")
async def formal_upload(file: UploadFile):
    dst = SAMPLES / file.filename
    with dst.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"saved_as": str(dst)}

@app.get("/artifact")
def artifact(rel_path: str):
    p = ROOT / "data" / rel_path
    if p.exists() and p.is_file():
        return FileResponse(p)
    return JSONResponse({"error": "artifact not found"}, status_code=404)

# ---------- INFERENCE ----------
@app.post("/infer/once")
def infer_once(batch: int = Form(4), workers: int = Form(1)):
    current_batch.set(batch)
    with infer_latency.time():
        out = infer.infer_once(batch=batch, workers=workers)
    infer_requests.inc(batch)
    cost_per_1k.set(out["cost_per_1k_requests"])
    util_pct.set(out["utilization_percent"])
    return out

@app.post("/infer/auto")
def infer_auto(trials: int = Form(20)):
    r = infer.auto_infer(trials=trials)
    if r.get("results"):
        last = r["results"][-1]
        cost_per_1k.set(last["cost_per_1k_requests"])
        util_pct.set(last["utilization_percent"])
        current_batch.set(last["batch"])
    return r

@app.get("/infer/tuner")
def infer_tuner():
    return infer.tuner.snapshot()

@app.post("/infer/tuner/enable")
def tuner_enable(enable: bool = Form(True)):
    infer.tuner.enabled = enable
    return infer.tuner.snapshot()

@app.post("/infer/tuner/policy")
def tuner_policy(policy: str = Form("ucb1")):
    infer.tuner.policy = policy
    return infer.tuner.snapshot()
