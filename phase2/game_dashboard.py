#!/usr/bin/env python3
"""SereneX Phase 2 — 游戏 Web 仪表盘 http://localhost:5002"""
import os, json, time
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)
STATE_FILE = "/tmp/serenex_game.json"

HTML = open(os.path.join(os.path.dirname(__file__), "dashboard.html")).read() if os.path.exists(os.path.join(os.path.dirname(__file__), "dashboard.html")) else """
<h1>请先运行几轮 tick 生成数据</h1>
<script>setTimeout(()=>location.reload(), 5000)</script>
"""

@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/api/state")
def api_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: return jsonify(json.load(f))
    return jsonify({"live": False})

if __name__ == "__main__":
    print("SereneX Phase 2 仪表盘：http://localhost:5002")
    app.run(host="0.0.0.0", port=5002, debug=False, threaded=True)
