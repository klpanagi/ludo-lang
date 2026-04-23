#!/usr/bin/env python3
# Usage: python ui/server.py
# Then open http://localhost:8765 in your browser

import http.server
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLES_DIR = ROOT / "examples"
OUTPUT_DIR = ROOT / "output"
UI_DIR = ROOT / "ui"
GENERATOR = ROOT / "generator" / "generate.py"
PORT = 8765


def parse_game_type(filepath):
    """Quickly extract game type from a .ludo file without textX."""
    try:
        text = pathlib.Path(filepath).read_text()
        m = re.search(r"type\s*:\s*(\w+)", text)
        return m.group(1) if m else "unknown"
    except Exception:
        return "unknown"


def parse_game_name(filepath):
    """Extract the game name string from a .ludo file."""
    try:
        text = pathlib.Path(filepath).read_text()
        m = re.search(r'game\s+"([^"]+)"', text)
        return m.group(1) if m else pathlib.Path(filepath).stem
    except Exception:
        return pathlib.Path(filepath).stem


def cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


class GameDSLHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default noisy logging
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        cors_headers(self)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file(UI_DIR / "index.html", "text/html")

        elif path == "/api/games":
            games = []
            for f in sorted(EXAMPLES_DIR.glob("*.ludo")):
                games.append(
                    {
                        "filename": f.name,
                        "stem": f.stem,
                        "name": parse_game_name(f),
                        "type": parse_game_type(f),
                    }
                )
            self._json(games)

        elif path.startswith("/api/games/"):
            stem = path[len("/api/games/") :]
            game_file = EXAMPLES_DIR / f"{stem}.ludo"
            if game_file.exists():
                self._text(game_file.read_text())
            else:
                self._error(404, f"Game not found: {stem}")

        elif path.startswith("/output/"):
            name = path[len("/output/") :]
            out_file = OUTPUT_DIR / name
            if out_file.exists():
                self._serve_file(out_file, "text/html")
            else:
                self._error(404, f"Output not found: {name}")

        else:
            self._error(404, "Not found")

    def do_POST(self):
        if self.path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._error(400, "Invalid JSON")
                return

            source = data.get("source", "")
            if not source.strip():
                self._json({"success": False, "error": "Empty source"})
                return

            # Write to temp file in examples dir (so relative paths in model work)
            tmp_path = EXAMPLES_DIR / "_temp_preview.ludo"
            try:
                tmp_path.write_text(source)
                result = subprocess.run(
                    [sys.executable, str(GENERATOR), str(tmp_path)],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=str(ROOT),
                )
                if result.returncode == 0:
                    # Find the output file from stdout
                    out_match = re.search(r"Generated:\s*(.+\.html)", result.stdout)
                    if out_match:
                        out_file = pathlib.Path(out_match.group(1).strip())
                        output_html = out_file.read_text()
                        # Get the filename for iframe src
                        out_name = out_file.name
                        self._json(
                            {
                                "success": True,
                                "output_name": out_name,
                                "stdout": result.stdout.strip(),
                            }
                        )
                    else:
                        self._json(
                            {"success": False, "error": result.stdout + result.stderr}
                        )
                else:
                    self._json(
                        {"success": False, "error": result.stderr or result.stdout}
                    )
            except subprocess.TimeoutExpired:
                self._json({"success": False, "error": "Generator timed out"})
            except Exception as e:
                self._json({"success": False, "error": str(e)})
            finally:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
        else:
            self._error(404, "Not found")

    def _serve_file(self, path, content_type):
        try:
            data = pathlib.Path(path).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            cors_headers(self)
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._error(404, f"File not found: {path}")

    def _json(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        cors_headers(self)
        self.end_headers()
        self.wfile.write(data)

    def _text(self, text):
        data = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        cors_headers(self)
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, msg):
        data = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        cors_headers(self)
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    host = os.environ.get("HOST", "0.0.0.0")
    server = HTTPServer((host, PORT), GameDSLHandler)
    print(f"🎮 Game DSL Studio running at http://{host}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
