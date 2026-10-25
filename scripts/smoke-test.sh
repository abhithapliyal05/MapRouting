#!/usr/bin/env bash
# End-to-end checks against a running deployment, through the Ingress.
#   ./scripts/smoke-test.sh                       # defaults: http://127.0.0.1:8088, *.localhost hosts
#   BASE_URL=http://127.0.0.1:8088 ./scripts/smoke-test.sh
# Exits non-zero on the first failed check. Used by CI and runnable locally.
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8088}"
APP_HOST="${APP_HOST:-app.localhost}"
VALHALLA_HOST="${VALHALLA_HOST:-valhalla.localhost}"
ASTAR_HOST="${ASTAR_HOST:-astar.localhost}"
PY="$(command -v python3 || command -v python)" || { echo "python is required" >&2; exit 1; }

# Tokyo Station -> Tokyo Tower: inside the CI fixture and the full dataset.
QUERY='{"locations":[{"lat":35.6812,"lon":139.7671},{"lat":35.6586,"lon":139.7454}]'

pass() { printf '  PASS  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*" >&2; exit 1; }
get()  { curl -fsS -m 20 -H "Host: $1" "$BASE_URL$2"; }

echo "smoke test against $BASE_URL"

code=$(curl -s -o /dev/null -m 20 -w '%{http_code}' -H "Host: $APP_HOST" "$BASE_URL/") || true
[[ "$code" == "200" ]] && pass "frontend serves / (200)" || fail "frontend / returned $code"

cfg=$(get "$APP_HOST" /config.js) || fail "config.js not served"
grep -q "valhallaUrl" <<<"$cfg" && grep -q "astarUrl" <<<"$cfg" && pass "config.js defines valhallaUrl and astarUrl" \
  || fail "config.js is missing expected keys"

get "$VALHALLA_HOST" /status | grep -q '"version"' && pass "valhalla /status" || fail "valhalla /status"
get "$ASTAR_HOST" /health | grep -q '"status": "ok"' && pass "astar /health" || fail "astar /health"

# Route checks assert a plausible distance range (km), not an exact number: the CI fixture is a
# cropped map, so the exact value differs from the full dataset.
route_km() { # host, extra-json
  curl -fsS -m 60 -G -H "Host: $1" "$BASE_URL/route" \
    --data-urlencode "json=${QUERY}$2}" | "$PY" -c "import sys,json; print(json.load(sys.stdin)['trip']['summary']['length'])"
}
in_range() { "$PY" -c "import sys; v=float(sys.argv[1]); sys.exit(0 if float(sys.argv[2])<=v<=float(sys.argv[3]) else 1)" "$@"; }

km=$(route_km "$VALHALLA_HOST" ',"costing":"auto"') || fail "valhalla route request failed"
in_range "$km" 3.5 6.0 && pass "valhalla route ${km} km (expected 3.5-6.0)" || fail "valhalla route ${km} km out of range"

km=$(route_km "$ASTAR_HOST" '') || fail "astar route request failed"
in_range "$km" 3.5 4.2 && pass "astar route ${km} km (expected 3.5-4.2)" || fail "astar route ${km} km out of range"

echo "smoke test OK"
