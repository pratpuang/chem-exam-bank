# -*- coding: utf-8 -*-
"""Tiny local server so the LIVE chem bank site can open the original scans on Prat's PC.
Serves ONLY source/ on 127.0.0.1:8765 (loopback: nothing outside this PC can reach it). The site's paper sheet
pings /ping; if it answers, the cards get the swipe-up -> PDF. Started at Windows login by a .vbs in the
Startup folder (chem-bank-pdf-server.vbs); delete that file to stop it auto-starting. Built 2026-11-10."""
import os, json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
PORT = 8765
ALLOW = {"https://chem-exam-bank.vercel.app", "http://localhost", "null"}

class H(SimpleHTTPRequestHandler):
    def cors(self):
        o = self.headers.get("Origin")
        if o in ALLOW or (o or "").startswith("http://localhost:") or (o or "").startswith("http://127.0.0.1:"):
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Vary", "Origin")
    def end_headers(self):
        self.cors(); super().end_headers()
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Methods", "GET"); self.end_headers()
    def do_GET(self):
        if self.path.split("?")[0] == "/ping":
            b = json.dumps({"ok": True, "app": "chem-bank-pdf"}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(b); return
        if not self.path.lower().split("?")[0].endswith(".pdf"):
            self.send_error(404); return
        super().do_GET()
    def list_directory(self, path):
        self.send_error(404); return None
    def log_message(self, *a): pass

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), partial(H, directory=SRC)).serve_forever()
