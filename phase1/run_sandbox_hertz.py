#!/usr/bin/env python3
"""SereneX — 4CH沙盒（含Cyber G. Hertz）+ DeepSeek真实对话"""
import sys, os, time, random, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env
for line in open(".env", encoding="utf-8-sig"):
    k, v = line.strip().split("=", 1)
    os.environ[k] = v

from cyber_human import CyberHuman
from chat_sandbox import ChatSandbox
from personality import create_personality
from ch_cyber_g_hertz import CH_HERTZ_PROFILE
from llm_interface import get_llm


def create_hertz_personality():
    from personality import PersonalityModel, BigFive
    bf_vals = CH_HERTZ_PROFILE["big_five"]
    bf = BigFive(**bf_vals)
    return PersonalityModel(mbti_type=CH_HERTZ_PROFILE["mbti"], big_five=bf)


def main():
    print("\n🦞 SereneX Phase 1 — 4 CH 真实对话（含Cyber G. Hertz）\n")

    llm = get_llm()
    print(f"LLM: {llm.provider.upper()}\n")

    sandbox = ChatSandbox("SereneX-4CH")

    # 4个CH配置
    ch_configs = [
        ("xiaoming", "小明",    "user_xm", "ENFP"),
        ("xiaoyu",   "小雨",    "user_xy", "INTJ"),
        ("ahua",     "阿华",    "user_ah", "ISFJ"),
        ("hertz",    "Cyber G. Hertz", "ch_hertz", "INTP"),
    ]

    for key, name, uid, mbti in ch_configs:
        ch = CyberHuman(name=name, user_id=uid)
        if key == "hertz":
            ch.personality = create_hertz_personality()
        else:
            ch.personality = create_personality(persona_key=key)
        sandbox.add_ch(ch, ch.personality)
        bf = ch.personality.big_five
        print(f"  🦞 {name} ({mbti}) 外向={bf.extraversion:.1f} 共情={ch.personality.empathy_score():.2f}")

    # 预填充关系
    for ch in sandbox.chs.values():
        for other in sandbox.chs.values():
            if ch.id != other.id:
                p = random.uniform(0.20, 0.50)
                ch.relations[other.id] = p
                sandbox.relation_matrix[(ch.id, other.id)] = p

    print(f"\n预填充关系:")
    for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
        if ida < idb:
            na = sandbox.chs[ida].name; nb = sandbox.chs[idb].name
            print(f"  {na} → {nb}: {prob:.2f}")

    print(f"\n{'='*55}")
    print(f"▶ 开始3轮对话（DeepSeek真实LLM）...\n")

    for i in range(1, 4):
        print(f"{'─'*55}")
        print(f"【Round {i}/3】")
        events = sandbox.tick()
        if events:
            for e in events:
                print(e)
        else:
            states = [(ch.name, ch.state.value) for ch in sandbox.chs.values()]
            print(f"  (平静: {', '.join(f'{n}={s}' for n,s in states)})")
        time.sleep(0.5)

    print(f"\n{'='*55}")
    print(f"最终状态:")
    for ch in sandbox.chs.values():
        p = ch.personality
        print(f"  {ch.name}({p.mbti_type}) 记忆={ch.episodic_memory_count} 情绪={ch.emotion.dominant_tag().value} 大脑={sum(ch.brain.activation.values()):.3f}")

    print(f"\n✅ 完成！")
    print(f"   仪表盘: http://localhost:5000")


if __name__ == "__main__":
    main()
