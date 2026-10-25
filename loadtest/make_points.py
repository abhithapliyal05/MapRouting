"""Generate loadtest/points.json: random trips that BOTH routing engines can route.

Samples pairs of road nodes 2-6 km apart from the OSM extract, then keeps only the pairs that the A* backend and
Valhalla both answer successfully through the Ingress, so that later failures mean overload, not bad input.

    python loadtest/make_points.py            # needs the stack running at http://127.0.0.1:8088
"""
import json
import math
import random
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
OSM = ROOT / "data" / "tokyo_center.osm"
OUT = Path(__file__).resolve().parent / "points.json"
BASE = "http://127.0.0.1:8088"
WANT = 300
random.seed(20261025)  # fixed seed: the same points every run


def haversine_km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def load_road_nodes():
    root = ElementTree.parse(OSM).getroot()
    coords = {int(n.get("id")): (float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
    used = set()
    for way in root.findall("way"):
        if any(t.get("k") == "highway" and t.get("v") in ("primary", "secondary", "tertiary", "residential", "trunk")
               for t in way.findall("tag")):
            used.update(int(nd.get("ref")) for nd in way.findall("nd"))
    return [coords[i] for i in used if i in coords]


def route_ok(host, query):
    url = f"{BASE}/route?json=" + urllib.parse.quote(json.dumps(query))
    req = urllib.request.Request(url, headers={"Host": host})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            trip = json.load(r).get("trip", {})
            return trip.get("status", 0) == 0 and "summary" in trip
    except Exception:
        return False


nodes = load_road_nodes()
print(f"{len(nodes)} road nodes")
pairs = []
tries = 0
while len(pairs) < WANT and tries < WANT * 12:
    tries += 1
    a, b = random.choice(nodes), random.choice(nodes)
    if not 2.0 <= haversine_km(a, b) <= 6.0:
        continue
    loc = [{"lat": round(a[0], 6), "lon": round(a[1], 6)}, {"lat": round(b[0], 6), "lon": round(b[1], 6)}]
    if route_ok("astar.localhost", {"locations": loc}) and route_ok(
            "valhalla.localhost", {"locations": loc, "costing": "auto"}):
        pairs.append(loc)
        if len(pairs) % 50 == 0:
            print(f"  {len(pairs)}/{WANT} verified ({tries} tried)")

OUT.write_text(json.dumps(pairs, separators=(",", ":")))
print(f"wrote {OUT} with {len(pairs)} pairs ({OUT.stat().st_size // 1024} KB)")
