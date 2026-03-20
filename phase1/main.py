#!/usr/bin/env python3
"""
SereneX Phase 1 — 主运行脚本
运行 Chat Sandbox，观察 CyberHuman 之间的自发聊天
"""

import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cyber_human import CyberHuman, ChatBehavior
from chat_sandbox import ChatSandbox
from emotion_tag import infer_emotions

def intro():
    return """
╔═══════════════════════════════════════════╗
║       SereneX Phase 1 — Chat Sandbox       ║
║        Cyber Human Social Simulation        ║
╚═══════════════════════════════════════════╝
3 个 Cyber Human 将在沙盒中自发聊天，
根据关系网络发起对话，记忆内容，并调整亲密度。
"""

def main():
    print(intro())
    sandbox = ChatSandbox("SereneX-01")

    ch_xm = CyberHuman(name="小明", user_id="user_xm")
    ch_xy = CyberHuman(name="小雨", user_id="user_xy")
    ch_ah = CyberHuman(name="阿华", user_id="user_ah")

    for ch in [ch_xm, ch_xy, ch_ah]:
        sandbox.add_ch(ch)

    print("\n初始状态：")
    print(sandbox.status())

    # 预填充初始关系
    for ch in [ch_xm, ch_xy, ch_ah]:
        for other in [ch_xm, ch_xy, ch_ah]:
            if ch.id != other.id:
                prob = random.uniform(0.2, 0.5)
                ch.relations[other.id] = prob
                sandbox.relation_matrix[(ch.id, other.id)] = prob

    print("\n预填充关系：")
    for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
        if ida < idb:
            na = sandbox.chs[ida].name
            nb = sandbox.chs[idb].name
            bar = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))
            print(f"  {na} -> {nb}: [{bar}] {prob:.2f}")

    print("\n▶ 开始运行...\n")

    for i in range(1, 13):
        print(f"{'─'*50}")
        print(f"【Round {i}/12】")
        events = sandbox.tick()
        if events:
            for e in events:
                print(e)
        else:
            waiting = [ch.name for ch in sandbox.chs.values()
                      if ch.state.value in ("idle", "waiting")]
            print(f"  (无新会话，{', '.join(waiting) if waiting else '所有人'})")
        print(f"  关系:", end=" ")
        rels = []
        for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
            if ida < idb:
                na = sandbox.chs[ida].name
                nb = sandbox.chs[idb].name
                rels.append(f"{na}-{nb}:{prob:.2f}")
        print(", ".join(rels))
        time.sleep(0.2)

    print("\n" + "="*60)
    print("最终状态报告")
    print(sandbox.status())

    print("\n" + "="*60)
    print("记忆库内容")
    print("="*60)
    for ch_id, mem_instance in sandbox.memory_systems.items():
        ch = sandbox.chs[ch_id]
        mem_sys = mem_instance  # already an instance
        print(f"\n🦞 {ch.name} 的记忆 ({len(mem_sys.episodic)} 段)：")
        for mem in mem_sys.recall_recent(5):
            age = mem_sys._format_age(mem.age())
            e = max(mem.emotion_tags, key=lambda x: x[1])[0] if mem.emotion_tags else "neutral"
            print(f"  [{age}] {mem.summary[:50]} | 情绪:{e}")

    print("\n" + "="*60)
    print("神经大脑状态")
    print("="*60)
    for ch in sandbox.chs.values():
        s = ch.brain.summary()
        print(f"\n🦞 {ch.name}:")
        print(f"  神经元:{s['neurons']} 突触:{s['synapses']} "
              f"平均强度:{s['avg_weight']:.4f} 激活度:{s['total_activation']:.4f}")

    print("\n" + "="*60)
    print("演化日志")
    print("="*60)
    for line in sandbox.log[-20:]:
        print(line)

    print("\n✅ Phase 1 运行完成！")

if __name__ == "__main__":
    main()
