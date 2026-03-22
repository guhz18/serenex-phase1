#!/usr/bin/env python3
"""SereneX: 10轮聊天+完整聊天记录写入文件"""
import sys, os, time, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# load env
for line in open(".env", encoding="utf-8-sig"):
    line = line.strip()
    if line and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

from cyber_human import CyberHuman
from chat_sandbox import ChatSandbox
from personality import create_personality, PersonalityModel, BigFive
from ch_cyber_g_hertz import CH_HERTZ_PROFILE

# create sandbox
sb = ChatSandbox("SereneX-HertzChat")

hertz_bf = BigFive(**CH_HERTZ_PROFILE["big_five"])
hertz_p = PersonalityModel(mbti_type=CH_HERTZ_PROFILE["mbti"], big_five=hertz_bf)

for key, name, uid, mbti in [
    ("xiaoming", "小明",    "user_xm", "ENFP"),
    ("xiaoyu",   "小雨",    "user_xy", "INTJ"),
    ("ahua",     "阿华",    "user_ah", "ISFJ"),
    ("hertz",    "Cyber G. Hertz", "ch_hertz", "INTP"),
]:
    ch = CyberHuman(name=name, user_id=uid)
    ch.personality = hertz_p if key == "hertz" else create_personality(persona_key=key)
    sb.add_ch(ch, ch.personality)

# init relations
for ch in sb.chs.values():
    for other in sb.chs.values():
        if ch.id != other.id:
            p = random.uniform(0.25, 0.55)
            ch.relations[other.id] = p
            sb.relation_matrix[(ch.id, other.id)] = p

ROUND_FILE = "/workspace/SereneX/phase1/chat_history.json"
all_turns = []
MAX_ROUNDS = 10

print(f"开始 {MAX_ROUNDS} 轮聊天\n{'='*55}")

for i in range(1, MAX_ROUNDS + 1):
    print(f"\n【Round {i}/{MAX_ROUNDS}】")
    events = sb.tick()

    for (ida, idb), session in list(sb.active_sessions.items()):
        if (ida, idb) != (session.ch_a, session.ch_b):
            continue
        for speaker, text in session.turns:
            speaker_ch = None
            for c in sb.chs.values():
                if c.name == speaker:
                    speaker_ch = c
                    break
            emotion = speaker_ch.emotion.dominant_tag().value if speaker_ch else "neutral"
            all_turns.append({
                "round": i, "session_id": session.id,
                "speaker": speaker, "emotion": emotion,
                "text": text,
            })
            print(f"  {speaker}: {text[:65]}{'...' if len(text)>65 else ''}")

    if not all_turns or all_turns[-1]["round"] != i:
        pass
    time.sleep(0.3)

# save
record = {
    "meta": {
        "ch_count": 4, "total_rounds": MAX_ROUNDS, "total_turns": len(all_turns),
        "chs": {
            "小明":    {"mbti": "ENFP"},
            "小雨":    {"mbti": "INTJ"},
            "阿华":    {"mbti": "ISFJ"},
            "Cyber G. Hertz": {"mbti": "INTP", "source": "紧扣的dagger/B站UID408650016"},
        },
    },
    "conversation": all_turns,
}

with open(ROUND_FILE, "w", encoding="utf-8") as f:
    json.dump(record, f, ensure_ascii=False, indent=2)

print(f"\n{'='*55}")
print(f"✅ {MAX_ROUNDS}轮完成！共 {len(all_turns)} 条对话")
print(f"📄 记录: {ROUND_FILE}")
for ch in sb.chs.values():
    p = ch.personality
    print(f"  {ch.name}({p.mbti_type}) 记忆={ch.episodic_memory_count} 情绪={ch.emotion.dominant_tag().value}")
