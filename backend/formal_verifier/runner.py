# backend/formal_verifier/runner.py
import subprocess, shutil, uuid, shutil as _shutil
from pathlib import Path
from .templates import (
    harness_sva, harness_sva_fsm, sby_file, sby_file_cover, write_file
)
from .coverage import parse_status_and_coverage

# Docker fallback image (only used if local sby not found / fails)
DOCKER_IMAGE = "ghcr.io/yosyshq/oss-cad-suite:latest"  # harmless if unreachable

def _run_local_sby(work_dir: Path):
    sby_bin = _shutil.which("sby") or "/opt/homebrew/bin/sby"
    if not Path(sby_bin).exists():
        return None, None, False
    proc = subprocess.run([sby_bin, "-f", "job.sby"],
                          cwd=str(work_dir), capture_output=True, text=True, timeout=600)
    return proc.stdout[-2000:], proc.stderr[-2000:], (proc.returncode == 0)

# At top or near _run_sby()
USE_DOCKER_FALLBACK = False

def _run_docker_sby(work_dir: Path):
    if not _shutil.which("docker"):
        return "", "docker not installed", False
    # Try to pull (ignore errors), then run sby from the toolkit path
    subprocess.run(["docker", "pull", DOCKER_IMAGE], capture_output=True, text=True)
    cmd = [
        "docker","run","--rm",
        "-v", f"{work_dir.resolve()}:/work",
        "-w","/work",
        DOCKER_IMAGE, "bash","-lc","/opt/oss-cad-suite/bin/sby -f job.sby"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return proc.stdout[-2000:], proc.stderr[-2000:], (proc.returncode == 0)

def _run_sby(work_dir: Path):
    # 1) Prefer local Homebrew sby
    out, err, ok = _run_local_sby(work_dir)
    if ok:
        return out or "", err or "", True
    # 2) Fallback to docker image (if reachable)
    out2, err2, ok2 = _run_docker_sby(work_dir)
    return (out2 or out or ""), (err2 or err or ""), ok2

def run_formal(rtl_path: str, top="counter", clk="clk", rst="rst", mode="prove"):
    run_id = str(uuid.uuid4())[:8]
    work_dir = Path("data/tmp") / f"formal_{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(rtl_path, work_dir / "design.sv")

    if top == "fsm_buggy":
        harness = harness_sva_fsm(top_module=top, clk=clk, rst=rst)
        sby = sby_file_cover(top_tb=f"{top}_tb", design_sv="design.sv", harness_sv="harness.sv")
    else:
        harness = harness_sva(top_module=top, clk=clk, rst=rst)
        sby = sby_file(top_tb=f"{top}_tb", design_sv="design.sv", harness_sv="harness.sv")

    write_file(work_dir / "harness.sv", harness)
    write_file(work_dir / "job.sby", sby)

    out, err, ok = _run_sby(work_dir)

    jobdir = work_dir / "job"
    logfile = jobdir / "logfile.txt"

    if logfile.exists():
        metrics = parse_status_and_coverage(logfile)
    else:
        metrics = {
            "status": "ERROR" if not ok else "UNKNOWN",
            "proved": 0, "failed": 0, "covered": 0, "undetermined": 0, "walltime": None
        }

    artifacts = []
    if jobdir.exists():
        for p in jobdir.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".vcd", ".txt"}:
                artifacts.append(str(p.relative_to(Path("data"))))

    return {"run_id": run_id, "stdout": out, "stderr": err, "artifacts": artifacts, **metrics}
