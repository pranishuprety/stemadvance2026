"""Local dev server for the intervention prototype.

Serves the static page and proxies live ADS-B aircraft from the OpenSky Network
(Schaefer et al., 2014 - reference [7] in the proposal) so the browser can pull
real-time traffic without running into CORS restrictions.
"""
import json
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Northeast corridor bounding box (lat/lon)
BBOX = dict(lamin=38.3, lomin=-80.6, lamax=43.4, lomax=-70.2)
OPENSKY = ("https://opensky-network.org/api/states/all"
           "?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}").format(**BBOX)

_cache = {"t": 0, "payload": None}
CACHE_SECONDS = 12  # be polite to the public OpenSky endpoint


def fetch_live_traffic():
    now = time.time()
    if _cache["payload"] and now - _cache["t"] < CACHE_SECONDS:
        return _cache["payload"]
    req = urllib.request.Request(OPENSKY, headers={"User-Agent": "stem-advance-prototype"})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = json.loads(r.read().decode("utf-8"))
    aircraft = []
    for s in raw.get("states") or []:
        lon, lat = s[5], s[6]
        if lon is None or lat is None:
            continue
        aircraft.append({
            "id": s[0],
            "callsign": (s[1] or "").strip(),
            "country": s[2],
            "lon": lon,
            "lat": lat,
            "alt": s[7],
            "onground": bool(s[8]),
            "vel": s[9],
            "track": s[10] or 0,
        })
    payload = {"time": raw.get("time", int(now)), "count": len(aircraft), "aircraft": aircraft}
    _cache.update(t=now, payload=payload)
    return payload


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/traffic"):
            try:
                payload = fetch_live_traffic()
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                msg = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
            return
        return super().do_GET()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Serving on http://localhost:8000  (live traffic at /api/traffic)")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
