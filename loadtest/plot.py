"""Draw the capacity charts from loadtest/results/<target>.json into docs/img/capacity-<target>.png.

    python loadtest/plot.py astar valhalla
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

for target in sys.argv[1:]:
    rows = json.loads((HERE / "results" / f"{target}.json").read_text())
    offered = [r["offered_rps"] for r in rows]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))

    ax[0].plot(offered, [r["p50_ms"] for r in rows], "o-", label="p50")
    ax[0].plot(offered, [r["p95_ms"] for r in rows], "o-", label="p95")
    ax[0].plot(offered, [r["p99_ms"] for r in rows], "o-", label="p99")
    ax[0].set(title="Latency vs offered load", xlabel="offered requests/s", ylabel="response time (ms)")
    ax[0].set_yscale("log")
    ax[0].legend()
    ax[0].grid(True, alpha=0.3)

    ax[1].plot(offered, offered, "k--", alpha=0.5, label="ideal (achieved = offered)")
    ax[1].plot(offered, [r["achieved_rps"] for r in rows], "o-", label="achieved")
    ax[1].set(title="Throughput", xlabel="offered requests/s", ylabel="completed requests/s")
    ax2 = ax[1].twinx()
    # error_pct (HTTP failures/timeouts) and check_fail_pct count the same failed requests: take the larger, never the sum
    ax2.bar(offered, [max(r["error_pct"], r["check_fail_pct"]) for r in rows], width=0.35, alpha=0.25, color="red")
    ax2.set_ylabel("errors (%)", color="red")
    ax[1].legend(loc="upper left")
    ax[1].grid(True, alpha=0.3)

    cpu = [(r["achieved_rps"], r["cpu_cores_avg"]) for r in rows if r["cpu_cores_avg"] is not None]
    ax[2].plot([c[0] for c in cpu], [c[1] for c in cpu], "o-")
    ax[2].set(title="CPU used by the pod(s)", xlabel="completed requests/s", ylabel="CPU cores (average)")
    ax[2].grid(True, alpha=0.3)

    fig.suptitle(f"{target}: capacity of one replica (k6, 45 s per step, local kind cluster)")
    fig.tight_layout()
    path = OUT / f"capacity-{target}.png"
    fig.savefig(path, dpi=110)
    print("wrote", path)
