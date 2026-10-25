// k6 load test for one routing engine through the Ingress.
//
//   k6 run -e TARGET=astar -e RATE=4 -e DURATION=40s loadtest/route.js
//
// constant-arrival-rate keeps the request rate fixed no matter how slowly the server answers. That is what finds
// saturation: a fixed number of virtual users would slow down together with the server and hide the overload.
import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { check } from 'k6';

const points = new SharedArray('points', () => JSON.parse(open('./points.json')));

const TARGET = __ENV.TARGET || 'astar'; // astar | valhalla
const RATE = parseInt(__ENV.RATE || '2', 10); // requests per second
const DURATION = __ENV.DURATION || '40s';
const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8088';

export const options = {
  scenarios: {
    load: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: Math.max(20, RATE * 2),
      maxVUs: 400, // headroom so k6 itself is not the bottleneck; dropped_iterations reports if it is
    },
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const loc = points[Math.floor(Math.random() * points.length)];
  const body = TARGET === 'valhalla' ? { locations: loc, costing: 'auto' } : { locations: loc };
  const res = http.get(`${BASE}/route?json=${encodeURIComponent(JSON.stringify(body))}`, {
    headers: { Host: `${TARGET}.localhost` },
    timeout: '30s',
  });
  check(res, {
    'status 200': (r) => r.status === 200,
    'has a route': (r) => {
      try {
        return r.json('trip.summary') !== undefined;
      } catch (e) {
        return false;
      }
    },
  });
}
