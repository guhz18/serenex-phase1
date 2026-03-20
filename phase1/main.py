#!/usr/bin/env python3
"""
SereneX Phase 1 — 主运行脚本
Chat Sandbox + 仪表盘 + 人格模型 + 睡眠整合
"""

import sys, os, time, random, threading, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cyber_human import CyberHuman
from chat_sandbox import ChatSandbox
from memory_system import MemorySystem
from personality import create_personality, PRESET_PERSONAS
from emotion_tag import infer_emotions


# ── 内置 HTTP 仪表盘（标准库，无第三方依赖）──────────────
def run_dashboard(port=5000):
    from dashboard_server import start_server
    start_server(port)

def start_dashboard():
    t = threading.Thread(target=run_dashboard, daemon=True)
    t.start()
    return t


def intro():
    return """
╔═══════════════════════════════════════════════════╗
║      SereneX Phase 1 — Chat Sandbox + Dashboard   ║
║        Cyber Human Social Simulation Engine         ║
╚═══════════════════════════════════════════════════╝
人格系统 · 记忆固化 · 关系演化 · 实时仪表盘
"""


def main():
    print(intro())

    # ── 启动仪表盘 ──────────────────────────────────────
    print("🌐 启动实时仪表盘: http://localhost:5000")
    start_dashboard()

    # ── 创建沙盒 ────────────────────────────────────────
    sandbox = ChatSandbox("SereneX-01")

    # ── 创建 CH（带人格模型）────────────────────────────
    personas = {
        "xiaoming": ("小明", "user_xm", "ENFP"),
        "xiaoyu":   ("小雨", "user_xy", "INTJ"),
        "ahua":     ("阿华", "user_ah", "ISFJ"),
    }

    for key, (name, uid, mbti) in personas.items():
        ch = CyberHuman(name=name, user_id=uid)
        personality = create_personality(persona_key=key)
        ch.personality = personality
        sandbox.add_ch(ch, personality)
        print(f"  🦞 {name} ({mbti}) — {personality.big_five.dict()['extraversion']:.1f}外向 "
              f"| {personality.empathy_score():.2f}共情 | "
              f"{personality.big_five.dict()['neuroticism']:.1f}神经质")

    # 预填充初始关系
    for ch in sandbox.chs.values():
        for other in sandbox.chs.values():
            if ch.id != other.id:
                prob = random.uniform(0.20, 0.50)
                ch.relations[other.id] = prob
                sandbox.relation_matrix[(ch.id, other.id)] = prob

    print("\n" + "="*60)
    print("预填充关系")
    for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
        if ida < idb:
            na = sandbox.chs[ida].name
            nb = sandbox.chs[idb].name
            bar = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))
            print(f"  {na} → {nb}: [{bar}] {prob:.2f}")

    print("\n  🌐 仪表盘: http://localhost:5000")
    print("\n▶ 开始运行...\n")

    # ── 运行模拟 ────────────────────────────────────────
    MAX_ROUNDS = 20
    ROUND_DELAY = 0.5

    for i in range(1, MAX_ROUNDS + 1):
        print(f"{'─'*55}")
        print(f"【Round {i}/{MAX_ROUNDS}】")
        events = sandbox.tick()

        if events:
            for e in events:
                print(e)
        else:
            states = [(ch.name, ch.state.value) for ch in sandbox.chs.values()]
            print(f"  (本轮平静，状态: {', '.join(f'{n}={s}' for n,s in states)})")

        # 打印关系演化
        changed = []
        for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
            if ida < idb:
                changed.append(f"{sandbox.chs[ida].name}-{sandbox.chs[idb].name}:{prob:.2f}")
        print(f"  关系: {', '.join(changed)}")

        time.sleep(ROUND_DELAY)

    # ── 最终报告 ────────────────────────────────────────
    print("\n" + "="*60)
    print("最终沙盒状态")
    print(sandbox.status())

    # 人格报告
    print("\n" + "="*60)
    print("人格系统报告")
    print("="*60)
    for ch in sandbox.chs.values():
        p = getattr(ch, "personality", None)
        if p:
            print(f"\n🦞 {ch.name} ({p.mbti_type})")
            print(f"   {p.big_five.dict()}")

    # 记忆报告
    print("\n" + "="*60)
    print("记忆库")
    print("="*60)
    for ch_id, mem_instance in sandbox.memory_systems.items():
        ch = sandbox.chs.get(ch_id)
        if not ch: continue
        mem_sys = mem_instance
        print(f"\n🦞 {ch.name} 的记忆 ({len(mem_sys.episodic)} 段)：")
        for mem in mem_sys.recall_recent(5):
            age = mem_sys._format_age(mem.age())
            e = max(mem.emotion_tags, key=lambda x: x[1])[0] if mem.emotion_tags else "neutral"
            print(f"  [{age}] {mem.summary[:50]} | 情绪:{e}")

    # 睡眠报告
    print("\n" + "="*60)
    print("睡眠整合记录")
    print("="*60)
    if sandbox.sleep_history:
        for s in sandbox.sleep_history:
            print(f"\n🌙 Round {s['round']} | {s['ch_name']}")
            print(f"   梦境: {s['dream_summary'][:60]}")
            print(f"   重播 {s['memories_replayed']} 段 | "
                  f"神经 +{s['neural_change']:.3f} | 情绪→{s['emotional_after']}")
    else:
        print("  (未触发睡眠整合)")

    print("\n" + "="*60)
    print("神经大脑状态")
    print("="*60)
    for ch in sandbox.chs.values():
        s = ch.brain.summary()
        print(f"\n🦞 {ch.name}:")
        print(f"  神经元:{s['neurons']} 突触:{s['synapses']} "
              f"平均强度:{s['avg_weight']:.4f} 激活度:{s['total_activation']:.4f}")

    print("\n演化日志")
    for line in sandbox.log[-15:]:
        print(f"  {line}")

    print(f"\n✅ Phase 1 运行完成！")
    print(f"   🌐 仪表盘仍在运行: http://localhost:5000")


if __name__ == "__main__":
    main()
