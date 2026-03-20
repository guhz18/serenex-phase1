#!/usr/bin/env python3
"""
SereneX Phase 1 — 纯 Python 仪表盘（标准库，无第三方依赖）
运行: python3 dashboard_server.py
访问: http://localhost:5000
"""

import http.server, json, socketserver, os, time, threading

PORT = 5000
STATE_FILE = "/tmp/serenex_dashboard.json"
BASE = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE, "dashboard", "templates", "dashboard.html")

# ── HTML Dashboard（内嵌，不依赖 Flask）───────────────────────
DASHBOARD_HTML = open(HTML_FILE, encoding="utf-8").read() if os.path.exists(HTML_FILE) else """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>SereneX Dashboard</title></head>
<body style="background:#0a0e17;color:#e5e7eb;font-family:sans-serif;padding:40px">
<h1>🦞 SereneX Dashboard</h1>
<p>Dashboard HTML file not found at: {f}</p>
</body></html>""".format(f=HTML_FILE)

# Demo fallback data (when no sandbox running)
DEMO_STATE = {
    "live": False,
    "round": 0,
    "timestamp": time.time(),
    "sleep_history": [],
    "chs": [
        {"id":"ch001","name":"小明","state":"idle","emotion":"joy","emotion_val":0.65,
         "brain_activation":0.42,"memories":0,"personality":"ENFP",
         "relations":[{"target":"小雨","prob":0.45},{"target":"阿华","prob":0.38}],
         "big_five":{"openness":0.8,"conscientiousness":0.4,"extraversion":0.9,"agreeableness":0.8,"neuroticism":0.3}},
        {"id":"ch002","name":"小雨","state":"idle","emotion":"neutral","emotion_val":0.50,
         "brain_activation":0.30,"memories":0,"personality":"INTJ",
         "relations":[{"target":"小明","prob":0.45},{"target":"阿华","prob":0.35}],
         "big_five":{"openness":0.7,"conscientiousness":0.9,"extraversion":0.2,"agreeableness":0.5,"neuroticism":0.2}},
        {"id":"ch003","name":"阿华","state":"idle","emotion":"neutral","emotion_val":0.50,
         "brain_activation":0.35,"memories":0,"personality":"ISFJ",
         "relations":[{"target":"小明","prob":0.38},{"target":"小雨","prob":0.35}],
         "big_five":{"openness":0.4,"conscientiousness":0.7,"extraversion":0.4,"agreeableness":0.9,"neuroticism":0.3}},
    ]
}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/status" or self.path == "/api/sandbox_info":
            state = self._load_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode("utf-8"))

        elif self.path.startswith("/api/personality/"):
            ch_id = self.path.split("/")[-1]
            personas = {
                "ch001": {"mbti":"ENFP","mbti_desc":"热情追梦人","big_five":{"openness":0.8,"conscientiousness":0.4,"extraversion":0.9,"agreeableness":0.8,"neuroticism":0.3},
                           "style":{"initiates_topics":True,"emotional_or_rational":"emotional"}},
                "ch002": {"mbti":"INTJ","mbti_desc":"独立战略家","big_five":{"openness":0.7,"conscientiousness":0.9,"extraversion":0.2,"agreeableness":0.5,"neuroticism":0.2},
                           "style":{"initiates_topics":False,"emotional_or_rational":"rational"}},
                "ch003": {"mbti":"ISFJ","mbti_desc":"温暖守护者","big_five":{"openness":0.4,"conscientiousness":0.7,"extraversion":0.4,"agreeableness":0.9,"neuroticism":0.3},
                           "style":{"initiates_topics":False,"emotional_or_rational":"emotional"}},
            }
            data = personas.get(ch_id, {})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif self.path.startswith("/api/memories/"):
            name = self.path.split("/")[-1]
            demos = {
                "小明": [{"text":"今天的聊天很开心","emotion":"joy","importance":0.72,"age":"2m前"},
                         {"text":"讨论人生理想","emotion":"anticipation","importance":0.65,"age":"5m前"}],
                "小雨": [{"text":"理性分析问题","emotion":"neutral","importance":0.60,"age":"3m前"},
                         {"text":"逻辑思考让我满足","emotion":"joy","importance":0.58,"age":"7m前"}],
                "阿华": [{"text":"听朋友聊天很温暖","emotion":"love","importance":0.70,"age":"1m前"},
                         {"text":"陪伴是最大的支持","emotion":"joy","importance":0.68,"age":"4m前"}],
            }
            mems = demos.get(name, [])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ch_name":name,"memories":mems}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except:
                pass
        return DEMO_STATE


def start_server(port=PORT):
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"  🌐 Dashboard → http://localhost:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    print(f"""
╔═══════════════════════════════════════════╗
║    SereneX Dashboard  http://localhost:{port}  ║
╚═══════════════════════════════════════════╝
""")
    start_server()
