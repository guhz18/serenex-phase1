"""
SereneX Phase 1 — Web 可视化仪表盘
运行方式: python3 dashboard_app.py
访问: http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request
import threading
import time
import random
import json
import os
import sys

# ── 共享状态 ──────────────────────────────────────────────────
# 为了简单，单进程模式下直接 import sandbox 状态
# 多进程模式下用 JSON 文件做 IPC
STATE_FILE = "/tmp/serenex_dashboard.json"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, template_folder="dashboard/templates")

# ── 颜色主题 ──────────────────────────────────────────────────
COLORS = {
    "小明": "#FF6B6B",
    "小雨": "#4ECDC4",
    "阿华": "#45B7D1",
}
EMOTION_COLORS = {
    "joy": "#FFD93D",
    "sadness": "#6BCB77",
    "anger": "#FF6B6B",
    "fear": "#C490D1",
    "surprise": "#F7B801",
    "disgust": "#A8D8EA",
    "love": "#FF9A8B",
    "anxiety": "#FFB88C",
    "anticipation": "#B5EAD7",
    "neutral": "#AAAAAA",
}
STATE_ICONS = {
    "idle": "💤",
    "initiating": "📩",
    "waiting": "⏳",
    "pending": "📥",
    "in_chat": "💬",
}

# ── 模拟/实时数据接口 ─────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return None

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    state = load_state()
    if state:
        return jsonify(state)
    return jsonify({"live": False})

@app.route("/api/sandbox_info")
def api_sandbox_info():
    """沙盒实时信息（每 2 秒更新一次）"""
    state = load_state()
    if state:
        return jsonify(state)

    # Fallback: 生成模拟数据（Dashboard未连接时展示）
    chs = [
        {"id": "ch_001", "name": "小明", "state": "idle", "emotion": "joy",
         "brain_activation": 0.42, "memories": 9, "relations": [
             {"target": "小雨", "prob": 0.55}, {"target": "阿华", "prob": 0.38}]},
        {"id": "ch_002", "name": "小雨", "state": "in_chat", "emotion": "curious",
         "brain_activation": 0.31, "memories": 6, "relations": [
             {"target": "小明", "prob": 0.55}, {"target": "阿华", "prob": 0.41}]},
        {"id": "ch_003", "name": "阿华", "state": "idle", "emotion": "neutral",
         "brain_activation": 0.38, "memories": 7, "relations": [
             {"target": "小明", "prob": 0.38}, {"target": "小雨", "prob": 0.41}]},
    ]
    return jsonify({
        "live": False,
        "round": 12,
        "chs": chs,
        "timestamp": time.time(),
    })

@app.route("/api/personality/<ch_id>")
def api_personality(ch_id):
    personas = {
        "ch_001": {"mbti": "ENFP", "mbti_desc": "热情洋溢的追梦人",
                   "big_five": {"openness": 0.8, "conscientiousness": 0.4,
                                "extraversion": 0.9, "agreeableness": 0.8, "neuroticism": 0.3},
                   "style": {"initiates_topics": True, "emotional_or_rational": "emotional"}},
        "ch_002": {"mbti": "INTJ", "mbti_desc": "独立战略家",
                   "big_five": {"openness": 0.7, "conscientiousness": 0.9,
                                "extraversion": 0.2, "agreeableness": 0.5, "neuroticism": 0.2},
                   "style": {"initiates_topics": False, "emotional_or_rational": "rational"}},
        "ch_003": {"mbti": "ISFJ", "mbti_desc": "温暖守护者",
                   "big_five": {"openness": 0.4, "conscientiousness": 0.7,
                                "extraversion": 0.4, "agreeableness": 0.9, "neuroticism": 0.3},
                   "style": {"initiates_topics": False, "emotional_or_rational": "emotional"}},
    }
    return jsonify(personas.get(ch_id, {}))

@app.route("/api/memories/<ch_name>")
def api_memories(ch_name):
    """模拟记忆数据"""
    return jsonify({
        "ch_name": ch_name,
        "memories": [
            {"text": "今天的聊天很愉快", "emotion": "joy", "importance": 0.72, "age": "2m前"},
            {"text": "讨论人生意义的话题", "emotion": "anticipation", "importance": 0.65, "age": "5m前"},
            {"text": "被问到生活节奏", "emotion": "curious", "importance": 0.58, "age": "8m前"},
        ]
    })


if __name__ == "__main__":
    port = 5000
    print(f"""
╔═══════════════════════════════════════════╗
║   SereneX 仪表盘  http://localhost:{port}   ║
╚═══════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
