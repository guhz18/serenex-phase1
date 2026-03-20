#!/usr/bin/env python3
"""
SereneX — 玩家介入客户端
用法: python3 player_client.py "你的消息"
示例: python3 player_client.py "大家好，我想聊聊量子力学"
"""

import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env
for line in open(".env", encoding="utf-8-sig"):
    k, v = line.strip().split("=", 1)
    os.environ[k] = v

from chat_sandbox import ChatSandbox
from cyber_human import CyberHuman
from personality import create_personality, PersonalityModel, BigFive
from ch_cyber_g_hertz import CH_HERTZ_PROFILE

# 玩家名字
PLAYER_NAME = "你"


def get_or_create_sandbox() -> ChatSandbox:
    """获取或创建当前沙盒实例（含4个CH）"""
    sb = ChatSandbox("SereneX-HertzChat")

    if sb.chs:
        return sb  # 已有CH，直接返回

    # 创建4个CH（首次）
    hertz_bf = BigFive(**CH_HERTZ_PROFILE["big_five"])
    hertz_p = PersonalityModel(
        mbti_type=CH_HERTZ_PROFILE["mbti"],
        big_five=hertz_bf,
    )

    for key, name, uid, mbti in [
        ("xiaoming", "小明",    "user_xm", "ENFP"),
        ("xiaoyu",   "小雨",    "user_xy", "INTJ"),
        ("ahua",     "阿华",    "user_ah", "ISFJ"),
        ("hertz",    "Cyber G. Hertz", "ch_hertz", "INTP"),
    ]:
        ch = CyberHuman(name=name, user_id=uid)
        ch.personality = hertz_p if key == "hertz" else create_personality(persona_key=key)
        sb.add_ch(ch, ch.personality)

    # 预填充关系
    import random
    for ch in sb.chs.values():
        for other in sb.chs.values():
            if ch.id != other.id:
                p = random.uniform(0.25, 0.55)
                ch.relations[other.id] = p
                sb.relation_matrix[(ch.id, other.id)] = p

    return sb


def append_to_history(entry: dict, filepath: str = "/workspace/SereneX/phase1/chat_history.json"):
    """追加聊天记录到文件"""
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {"meta": {}, "conversation": []}
    else:
        data = {"meta": {"chs": {}}, "conversation": []}

    if "player_interventions" not in data:
        data["player_interventions"] = []
    data["player_interventions"].append(entry)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n⚠️  请输入你想说的话，例如：")
        print("   python3 player_client.py '大家好，我想聊聊量子力学'")
        return

    player_message = " ".join(sys.argv[1:])
    print(f"\n👤 你: {player_message}\n")

    sb = get_or_create_sandbox()
    print(f"📡 广播给 {len(sb.chs)} 个CH，等待回应...\n")

    start = time.time()
    responses = sb.player_send(PLAYER_NAME, player_message)
    elapsed = time.time() - start

    # 打印CH回应
    print("─" * 50)
    for r in responses:
        emoji_map = {
            "joy": "😄", "sadness": "😢", "anger": "😠",
            "fear": "😨", "surprise": "😲", "love": "❤️",
            "anxiety": "😰", "anticipation": "🤩", "neutral": "😐",
        }
        emo = r["emotion"]
        emoji = emoji_map.get(emo, "💬")
        print(f"{emoji} {r['speaker']}({r['ch_mbti']}): {r['text']}")
    print("─" * 50)

    # 写入记录
    entry = {
        "timestamp": time.time(),
        "player": PLAYER_NAME,
        "player_message": player_message,
        "responses": [
            {"speaker": r["speaker"], "mbti": r["ch_mbti"],
             "emotion": r["emotion"], "text": r["text"]}
            for r in responses
        ],
        "elapsed_seconds": round(elapsed, 1),
    }
    append_to_history(entry)
    print(f"\n✅ 已记录到 chat_history.json（{len(responses)}条回应，{elapsed:.1f}s）")


if __name__ == "__main__":
    main()
