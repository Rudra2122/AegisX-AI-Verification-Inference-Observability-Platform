from pathlib import Path
import re

def parse_status_and_coverage(logfile_path: Path):
    text = Path(logfile_path).read_text(errors="ignore")

    status = "UNKNOWN"
    proved = failed = covered = undetermined = 0
    walltime = None

    # Map SBY end banners
    if "DONE (PASS" in text or "successful proof" in text or "returned pass" in text:
        status = "PASSED"
        proved = 1
    elif "DONE (COVER" in text or re.search(r"reached cover", text, re.I):
        status = "COVERED"
        covered = 1
    elif "DONE (FAIL" in text or "unreached cover" in text:
        status = "FAILED"
        failed = 1

    # Optional: extract elapsed time if present
    m = re.search(r"Elapsed (?:clock|process) time.*?([0-9:.]+)", text)
    if m:
        walltime = m.group(1)

    return {
        "status": status,
        "proved": proved,
        "failed": failed,
        "covered": covered,
        "undetermined": undetermined,
        "walltime": walltime,
    }
