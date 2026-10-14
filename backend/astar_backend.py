import os
import math
import heapq
import urllib.request
import urllib.parse
import json
from xml.etree import ElementTree
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Bounding Box Settings for Tokyo Center ---
MIN_LAT = 35.600
MAX_LAT = 35.750
MIN_LON = 139.650
MAX_LON = 139.850

OSM_FILE_PATH = os.path.join("data", "tokyo_center.osm")
PORT = 8003

# Haversine distance formula to compute edge weights (meters)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# Polyline6 encoder to match MapLibre client decoder
def encode_polyline6(coordinates):
    result = []
    last_lat = 0
    last_lng = 0
    for lon, lat in coordinates:
        lat_val = int(round(lat * 1e6))
        lng_val = int(round(lon * 1e6))
        
        delta_lat = lat_val - last_lat
        delta_lng = lng_val - last_lng
        
        last_lat = lat_val
        last_lng = lng_val
        
        result.append(encode_value(delta_lat))
        result.append(encode_value(delta_lng))
        
    return "".join(result)

def encode_value(value):
    value = ~(value << 1) if value < 0 else (value << 1)
    chunks = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1f)) + 63))
        value >>= 5
    chunks.append(chr(value + 63))
    return "".join(chunks)

class OSMRoutingGraph:
    def __init__(self):
        self.nodes = {}  # node_id -> (lat, lon)
        self.graph = defaultdict(list)  # u_id -> [(v_id, weight_meters, street_name, highway_type)]

    def ensure_osm_data(self):
        if not os.path.exists("data"):
            os.makedirs("data")

        if os.path.exists(OSM_FILE_PATH):
            print(f"[*] Found local OSM cache: {OSM_FILE_PATH}")
            return

        print(f"[!] Local OSM cache not found. Downloading bbox from Overpass API mirrors...")
        # Query matching highways in our Tokyo Center bbox
        overpass_query = f"""[out:xml][timeout:180];
        (
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"]({MIN_LAT},{MIN_LON},{MAX_LAT},{MAX_LON});
        );
        out body;
        >;
        out skel qt;"""

        mirrors = [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://z.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.nchc.org.tw/api/interpreter"
        ]

        success = False
        last_error = None

        for mirror in mirrors:
            url = f"{mirror}?data={urllib.parse.quote(overpass_query)}"
            print(f"[*] Trying mirror: {mirror}")
            req = urllib.request.Request(url, headers={
                'User-Agent': 'TokyoCenterAStarRoutingAgent/1.0 (contact.abhir@routingproject.org)',
                'Accept': 'application/xml, text/xml, */*',
                'Accept-Language': 'en-US,en;q=0.5'
            })
            try:
                # Add a reasonable timeout so we don't hang forever on unresponsive mirrors
                with urllib.request.urlopen(req, timeout=15) as response:
                    osm_data = response.read()
                    with open(OSM_FILE_PATH, "wb") as f:
                        f.write(osm_data)
                print(f"[+] Download complete from mirror: {mirror}")
                success = True
                break
            except Exception as e:
                print(f"[-] Mirror {mirror} failed: {e}")
                last_error = e

        if not success:
            print(f"[-] Failed to download map data from all mirrors.")
            if last_error:
                raise last_error
            else:
                raise Exception("Unknown error downloading map data")

    def build_graph(self):
        self.ensure_osm_data()
        print(f"[*] Parsing OSM XML data from {OSM_FILE_PATH}...")
        
        # Parse XML tree
        tree = ElementTree.parse(OSM_FILE_PATH)
        root = tree.getroot()

        # 1. Parse Nodes
        for node in root.findall('node'):
            node_id = int(node.attrib['id'])
            lat = float(node.attrib['lat'])
            lon = float(node.attrib['lon'])
            self.nodes[node_id] = (lat, lon)

        print(f"[*] Loaded {len(self.nodes)} nodes. Parsing streets and ways...")

        # 2. Parse Ways (Streets)
        way_count = 0
        edge_count = 0
        for way in root.findall('way'):
            # Check tags to identify street properties
            tags = {}
            for tag in way.findall('tag'):
                tags[tag.attrib['k']] = tag.attrib['v']

            if 'highway' not in tags:
                continue
            
            # Skip pedestrian plaza, footway, steps, cycles for auto if needed,
            # but for general routing, we can keep them or classify speeds.
            highway_type = tags['highway']
            street_name = tags.get('name', 'Unnamed Street')
            
            # Determine if street is one-way
            oneway = tags.get('oneway', 'no') in ('yes', '1', 'true')

            # Extract list of node references forming the way
            nd_elements = way.findall('nd')
            way_nodes = [int(nd.attrib['ref']) for nd in nd_elements]

            # Connect consecutive nodes in graph
            for i in range(len(way_nodes) - 1):
                u = way_nodes[i]
                v = way_nodes[i+1]

                # Make sure both nodes exist within our bounding box extract
                if u in self.nodes and v in self.nodes:
                    lat_u, lon_u = self.nodes[u]
                    lat_v, lon_v = self.nodes[v]
                    dist = haversine_distance(lat_u, lon_u, lat_v, lon_v)

                    # Add forward edge
                    self.graph[u].append((v, dist, street_name, highway_type))
                    edge_count += 1

                    # Add backward edge if not one-way
                    if not oneway:
                        self.graph[v].append((u, dist, street_name, highway_type))
                        edge_count += 1
            
            way_count += 1

        print(f"[+] Loaded {way_count} ways forming {edge_count} directed routing edges.")

    def find_nearest_node(self, lat, lon):
        best_node = None
        min_dist = float('inf')
        for node_id, coords in self.nodes.items():
            dist = haversine_distance(lat, lon, coords[0], coords[1])
            if dist < min_dist:
                min_dist = dist
                best_node = node_id
        return best_node, min_dist

    def search_astar(self, start_coords, end_coords):
        # find nearest nodes
        start_node, start_dist = self.find_nearest_node(start_coords['lat'], start_coords['lon'])
        end_node, end_dist = self.find_nearest_node(end_coords['lat'], end_coords['lon'])

        if not start_node or not end_node:
            return None

        # A* priority queue items: (f_score, current_node, g_score)
        open_set = []
        # Push start node
        h_start = haversine_distance(
            self.nodes[start_node][0], self.nodes[start_node][1],
            self.nodes[end_node][0], self.nodes[end_node][1]
        )
        heapq.heappush(open_set, (h_start, start_node, 0.0))

        came_from = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start_node] = 0.0

        visited = set()

        while open_set:
            f, current, current_g = heapq.heappop(open_set)

            if current == end_node:
                return self.reconstruct_path(came_from, current, start_coords, end_coords)

            if current in visited:
                continue
            visited.add(current)

            for neighbor, dist, street_name, highway_type in self.graph[current]:
                tentative_g = current_g + dist

                if tentative_g < g_score[neighbor]:
                    came_from[neighbor] = (current, street_name, dist)
                    g_score[neighbor] = tentative_g
                    
                    h = haversine_distance(
                        self.nodes[neighbor][0], self.nodes[neighbor][1],
                        self.nodes[end_node][0], self.nodes[end_node][1]
                    )
                    f_score = tentative_g + h
                    heapq.heappush(open_set, (f_score, neighbor, tentative_g))

        return None

    def reconstruct_path(self, came_from, current, start_coords, end_coords):
        # Unwind path nodes
        path_nodes = [current]
        maneuver_segments = []  # [(street_name, distance_meters)]

        while current in came_from:
            prev, street, dist = came_from[current]
            maneuver_segments.append((street, dist))
            path_nodes.append(prev)
            current = prev

        path_nodes.reverse()
        maneuver_segments.reverse()

        # Compile precise coordinates list [lon, lat]
        coordinates = []
        # Include original user start click coordinates snapped to start
        coordinates.append([start_coords['lon'], start_coords['lat']])
        
        for node_id in path_nodes:
            lat, lon = self.nodes[node_id]
            coordinates.append([lon, lat])
            
        # Include original user end click coordinates snapped to end
        coordinates.append([end_coords['lon'], end_coords['lat']])

        # Aggregate maneuvers to make nice combined steps
        maneuvers = []
        total_time = 0.0
        total_distance = 0.0

        if maneuver_segments:
            current_street = maneuver_segments[0][0]
            current_dist = 0.0

            for street, dist in maneuver_segments:
                total_distance += dist
                if street == current_street:
                    current_dist += dist
                else:
                    maneuvers.append({
                        "instruction": f"Go along {current_street}",
                        "length": current_dist / 1000.0  # km
                    })
                    current_street = street
                    current_dist = dist
            
            # Add final segment
            maneuvers.append({
                "instruction": f"Go along {current_street}",
                "length": current_dist / 1000.0
            })
            
            # Simple speed estimate to compute duration: ~35 km/h driving
            total_time = (total_distance / 10.0)  # ~10 meters/second
        
        # Append arrival
        maneuvers.append({
            "instruction": "Arrive at destination",
            "length": 0.0
        })

        return {
            "trip": {
                "status": 0,
                "summary": {
                    "length": total_distance / 1000.0,  # km
                    "time": total_time  # seconds
                },
                "legs": [{
                    "shape": encode_polyline6(coordinates),
                    "maneuvers": maneuvers
                }]
            }
        }

# --- HTTP Request Handler ---
class AStarHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress spamming stdout on map ticks
        pass

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Access-Control-Allow-Headers')
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == "/route":
            query_params = urllib.parse.parse_qs(parsed_url.query)
            json_param = query_params.get('json', [None])[0]

            if not json_param:
                self.send_error_response("Missing json parameter")
                return

            try:
                query = json.loads(json_param)
                locations = query.get("locations", [])
                if len(locations) < 2:
                    self.send_error_response("Must provide start and end locations")
                    return

                start = locations[0]
                end = locations[1]

                # Run custom A* routing
                result = routing_graph.search_astar(start, end)

                if result:
                    self.send_success_response(result)
                else:
                    self.send_success_response({
                        "trip": {
                            "status": 1,
                            "status_message": "No path found between coordinates in Tokyo Center"
                        }
                    })

            except Exception as e:
                print(f"[-] Routing execution error: {e}")
                self.send_error_response(f"Server error: {str(e)}")
        elif parsed_url.path == "/health":
            # Liveness/readiness probe: only reachable once the graph is built
            self.send_success_response({"status": "ok", "nodes": len(routing_graph.nodes)})
        else:
            self.send_response(404)
            self.end_headers()

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))

# Global routing graph instance
routing_graph = OSMRoutingGraph()

def run_server():
    routing_graph.build_graph()
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, AStarHTTPHandler)
    print(f"\n[+] Custom A* Pathfinding Server running on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Shutting down A* Server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
