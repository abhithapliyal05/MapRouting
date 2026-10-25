#!/usr/bin/env bash
# Regenerates the small map fixtures used by CI from a full Tokyo-center OSM XML file.
#   ./ci/make-fixture.sh path/to/tokyo_center.osm
# Needs Docker. Output: ci/data/fixture.osm.pbf (Valhalla input) and ci/data/tokyo_center.osm (A* input),
# covering lon 139.74-139.775, lat 35.655-35.69 (Tokyo Station to Tokyo Tower and a margin).
set -euo pipefail
src="$(cd "$(dirname "${1:?usage: $0 path/to/tokyo_center.osm}")" && pwd)/$(basename "$1")"
out="$(cd "$(dirname "$0")" && pwd)/data"
mkdir -p "$out"
docker run --rm -v "$src:/in/source.osm:ro" -v "$out:/out" ubuntu:24.04 bash -c '
  set -e
  apt-get update -qq >/dev/null && apt-get install -y -qq osmium-tool >/dev/null
  # Overpass lists ways before nodes; osmium needs nodes first, so sort before extracting.
  osmium sort /in/source.osm -o /tmp/sorted.osm.pbf --overwrite
  osmium extract -b 139.74,35.655,139.775,35.69 /tmp/sorted.osm.pbf -o /out/fixture.osm.pbf --overwrite
  osmium cat /out/fixture.osm.pbf -o /out/tokyo_center.osm --overwrite
'
ls -l "$out"
