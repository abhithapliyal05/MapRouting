"""Step-load one routing engine and record latency, errors and pod resource use for each rate.

    python loadtest/run.py astar   2 4 6 8 10 12
    python loadtest/run.py valhalla 10 20 40 60 80

For every request rate it runs k6 for a fixed time, then asks Prometheus what CPU and memory the target pods used
during exactly that window. Results go to loadtest/results/<target>.json and .csv.
Needs: k6 on PATH, the stack up on http://127.0.0.1:8088, Prometheus on http://localhost:9090.
"""
import csv
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROM = "http://localhost:9090"
DURATION_S = 45
COOLDOWN_S = 20

K6 = shutil.which("k6") or next(
    (p for p in (r"C:\Program Files\k6\k6.exe", "/usr/local/bin/k6", "/usr/bin/k6") if Path(p).exists()), None)
if K6 is None:
    sys.exit("k6 not found: install it (https://grafana.com/docs/k6/latest/set-up/install-k6/) or put it on PATH")

target = sys.argv[1]
rates = [int(r) for r in sys.argv[2:]]
container = {"astar": "astar", "valhalla": "valhalla"}[target]
pod_re = f"routing-{target}-.*"


def prom_range(query, start, end, step=5):
    url = f"{PROM}/api/v1/query_range?" + urllib.parse.urlencode(
        {"query": query, "start": start, "end": end, "step": step})
    with urllib.request.urlopen(url, timeout=30) as r:
        series = json.load(r)["data"]["result"]
    return [float(v) for s in series for _, v in s["values"]]


rows = []
for rate in rates:
    out = Path(tempfile.gettempdir()) / f"k6-{target}-{rate}.json"
    t0 = time.time()
    proc = subprocess.run(
        [K6, "run", "--quiet", f"--summary-export={out}", "-e", f"TARGET={target}", "-e", f"RATE={rate}",
         "-e", f"DURATION={DURATION_S}s", str(HERE / "route.js")],
        capture_output=True, text=True)
    t1 = time.time()
    m = json.loads(out.read_text())["metrics"]
    dur = m["http_req_duration"]
    # skip the first 10 s (ramp-up / JIT / cache warm-up) when averaging resource use
    cpu = prom_range(
        f'sum(rate(container_cpu_usage_seconds_total{{namespace="routing",pod=~"{pod_re}",container="{container}"}}[30s]))',
        t0 + 10, t1)
    mem = prom_range(
        f'sum(container_memory_working_set_bytes{{namespace="routing",pod=~"{pod_re}",container="{container}"}})',
        t0 + 10, t1)
    checks = m.get("checks", {})
    row = {
        "target": target,
        "offered_rps": rate,
        "achieved_rps": round(m["http_reqs"]["rate"], 2),
        "p50_ms": round(dur["med"], 1),
        "p95_ms": round(dur["p(95)"], 1),
        "p99_ms": round(dur["p(99)"], 1),
        "max_ms": round(dur["max"], 1),
        "error_pct": round(100 * m.get("http_req_failed", {}).get("value", 0), 2),
        "check_fail_pct": round(100 * (1 - checks.get("value", 1)), 2) if checks else 0,
        "dropped": m.get("dropped_iterations", {}).get("count", 0),
        "cpu_cores_avg": round(statistics.mean(cpu), 3) if cpu else None,
        "cpu_cores_max": round(max(cpu), 3) if cpu else None,
        "mem_mib_max": round(max(mem) / 1048576, 1) if mem else None,
    }
    rows.append(row)
    print(json.dumps(row), flush=True)
    time.sleep(COOLDOWN_S)

res = HERE / "results"
res.mkdir(exist_ok=True)
(res / f"{target}.json").write_text(json.dumps(rows, indent=2))
with open(res / f"{target}.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print("wrote", res / f"{target}.csv")
