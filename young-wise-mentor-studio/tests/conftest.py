import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SCRIPT = (
    "Every morning you wake up and the same thing happens. "
    "You pick up your phone and scroll through social media for an hour. "
    "But here's the truth, nobody is coming to save your time. "
    "Listen, you must decide what matters now. "
    "First, protect your mornings. Second, remove the noise."
)


def _tone_bursts(path: Path, plan: list[tuple[str, float]]):
    """Synthetic 'speech': tone bursts separated by silence. Enough to test pause detection (not real speech)."""
    parts, inputs = [], []
    for i, (kind, dur) in enumerate(plan):
        src = f"sine=frequency={180 + 25 * (i % 4)}:duration={dur}" if kind == "tone" else f"anullsrc=r=44100:cl=mono:d={dur}"
        inputs += ["-f", "lavfi", "-i", src + (":sample_rate=44100" if kind == "tone" else "")]
        parts.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=mono[a{i}]")
    cc = "".join(f"[a{i}]" for i in range(len(plan))) + f"concat=n={len(plan)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex",
                    ";".join(parts) + ";" + cc, "-map", "[out]", str(path)], check=True)


@pytest.fixture(scope="session")
def voiceover(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("audio") / "vo.wav"
    plan = [("tone", 5.0), ("sil", 0.8), ("tone", 5.0), ("sil", 0.8), ("tone", 4.0), ("sil", 0.8),
            ("tone", 4.0), ("sil", 0.8), ("tone", 5.0)]
    _tone_bursts(p, plan)
    return p


@pytest.fixture(scope="session")
def script_text() -> str:
    return SCRIPT


@pytest.fixture(scope="session")
def tiny_mp4(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("vid") / "tiny.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=320x568:rate=30:duration=2", "-pix_fmt", "yuv420p", str(p)], check=True)
    return p


@pytest.fixture
def fake_service(tiny_mp4):
    """Local fake implementing the documented fal queue protocol plus a generic submit/poll API."""
    state = {"status_calls": 0, "submitted": [], "headers": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            state["submitted"].append((self.path, body))
            state["headers"].append(dict(self.headers))
            base = f"http://127.0.0.1:{self.server.server_port}"
            if self.path.startswith("/fal-ai/"):
                if self.headers.get("Authorization") != "Key test-key":
                    return self._json({"detail": "unauthorized"}, 401)
                return self._json({"request_id": "r1", "status_url": f"{base}/fal-ai/bytedance/omnihuman/requests/r1/status",
                                   "response_url": f"{base}/fal-ai/bytedance/omnihuman/requests/r1"})
            if self.path == "/v1/jobs":
                return self._json({"id": "job9"})
            self._json({"error": "nope"}, 404)

        def do_GET(self):
            base = f"http://127.0.0.1:{self.server.server_port}"
            if self.path.endswith("/requests/r1/status"):
                state["status_calls"] += 1
                if state["status_calls"] < 2:
                    return self._json({"status": "IN_QUEUE", "queue_position": 1})
                return self._json({"status": "COMPLETED"})
            if self.path.endswith("/requests/r1"):
                return self._json({"video": {"url": f"{base}/video.mp4"}, "duration": 2.0})
            if self.path == "/v1/jobs/job9":
                state["status_calls"] += 1
                return self._json({"status": "done" if state["status_calls"] >= 2 else "running",
                                   "output": [{"url": f"{base}/video.mp4"}]})
            if self.path == "/video.mp4":
                data = tiny_mp4.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._json({"error": "nope"}, 404)

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    state["base"] = f"http://127.0.0.1:{srv.server_port}"
    yield state
    srv.shutdown()
