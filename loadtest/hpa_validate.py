"""Check that the HPA settings protect the service: offer more load than one replica can take and watch it scale.

    python loadtest/hpa_validate.py astar 5 150       # target, requests/s, seconds

Starts k6, samples the HPA and Deployment every 5 s, then asks Prometheus for the p95 latency timeline measured at
the ingress. Writes loadtest/results/hpa-<target>.json and docs/img/hpa-<target>.png.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROM = "http://localhost:9090"
target, rate, secs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

K6 = shutil.which("k6") or r"C:\Program Files\k6\k6.exe"
KUBECTL = shutil.which("kubectl") or r"C:\Program Files\Docker\Docker\resources\bin\kubectl.exe"


def kube(*args):
    return json.loads(subprocess.run([KUBECTL, "-n", "routing", *args, "-o", "json"],
                                     capture_output=True, text=True, check=True).stdout)


def prom_range(query, start, end, step=5):
    url = f"{PROM}/api/v1/query_range?" + urllib.parse.urlencode(
        {"query": query, "start": start, "end": end, "step": step})
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)["data"]["result"]


summary = Path(tempfile.gettempdir()) / f"k6-hpa-{target}.json"
t0 = time.time()
k6 = subprocess.Popen([K6, "run", "--quiet", f"--summary-export={summary}", "-e", f"TARGET={target}",
                       "-e", f"RATE={rate}", "-e", f"DURATION={secs}s", str(HERE / "route.js")],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
samples = []
while k6.poll() is None:
    hpa = kube("get", "hpa", f"routing-{target}")
    dep = kube("get", "deploy", f"routing-{target}")
    cpu = next((m["resource"]["current"].get("averageUtilization") for m in hpa["status"].get("currentMetrics", [])
                if m.get("resource", {}).get("name") == "cpu"), None)
    samples.append({
        "t": round(time.time() - t0),
        "ready": dep["status"].get("readyReplicas", 0),
        "current": hpa["status"].get("currentReplicas", 0),
        "desired": hpa["status"].get("desiredReplicas", 0),
        "cpu_util_pct": cpu,
    })
    print(json.dumps(samples[-1]), flush=True)
    time.sleep(5)
t1 = time.time()

p95 = prom_range(
    f'histogram_quantile(0.95, sum by (le) (rate(traefik_service_request_duration_seconds_bucket{{service=~".*-{target}-[0-9]+@kubernetes"}}[1m])))',
    t0, t1)  # window must span >= 2 scrapes (Prometheus scrapes every 30 s here), so not [30s]
p95_points = [(float(t) - t0, float(v)) for t, v in (p95[0]["values"] if p95 else []) if v != "NaN"]
m = json.loads(summary.read_text())["metrics"]
out = {
    "started_epoch": t0, "ended_epoch": t1,
    "target": target, "offered_rps": rate, "seconds": secs, "samples": samples, "p95_timeline_s": p95_points,
    "k6": {"achieved_rps": m["http_reqs"]["rate"], "p95_ms": m["http_req_duration"]["p(95)"],
           "error_pct": 100 * m.get("http_req_failed", {}).get("value", 0)},
}
(HERE / "results" / f"hpa-{target}.json").write_text(json.dumps(out, indent=2))

fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
ax[0].step([s["t"] for s in samples], [s["ready"] for s in samples], where="post", label="ready replicas")
ax[0].step([s["t"] for s in samples], [s["desired"] for s in samples], where="post", linestyle="--",
           label="HPA desired replicas")
ax[0].set(ylabel="replicas", title=f"{target}: HPA reacting to {rate} req/s (one replica saturates at ~3)")
ax[0].legend()
ax[0].grid(True, alpha=0.3)
ax[1].plot([p[0] for p in p95_points], [p[1] for p in p95_points], "o-", color="tab:red")
ax[1].set(xlabel="seconds since the load started", ylabel="p95 latency at the ingress (s)")
ax[1].set_yscale("log")
ax[1].grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(HERE.parent / "docs" / "img" / f"hpa-{target}.png", dpi=110)
print("k6:", json.dumps(out["k6"]))
