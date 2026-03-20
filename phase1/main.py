#!/usr/bin/env python3
"""
SereneX Phase 1 — 主运行脚本
Chat Sandbox + 人格模型 + 睡眠整合 + 真实LLM + 私人记忆导入
"""

import sys, os, time, random, threading, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cyber_human import CyberHuman
from chat_sandbox import ChatSandbox
from memory_system import MemorySystem
from personality import create_personality, PRESET_PERSONAS
from llm_interface import get_llm
from chatlog_importer import create_importer


# ── 仪表盘（后台线程）───────────────────────────────
def run_dashboard(port=5000):
    from dashboard_server import start_server
    start_server(port)

def start_dashboard():
    t = threading.Thread(target=run_dashboard, daemon=True)
    t.start()
    return t


def intro():
    llm = get_llm()
    provider = llm.provider
    status = "🔌 " + provider.upper() if provider != "mock" else "📝 mock模式"
    return f"""
╔═══════════════════════════════════════════════════╗
║      SereneX Phase 1 — Chat Sandbox + LLM + Memory  ║
║        Cyber Human Social Simulation Engine           ║
╚═══════════════════════════════════════════════════╝
人格系统 · 记忆固化 · 关系演化 · 真实LLM · 私人记忆导入
LLM: {status}
"""


def create_sandbox_with_chs() -> ChatSandbox:
    sandbox = ChatSandbox("SereneX-01")

    personas = {
        "xiaoming": ("小明", "user_xm"),
        "xiaoyu":   ("小雨", "user_xy"),
        "ahua":     ("阿华", "user_ah"),
    }

    for key, (name, uid) in personas.items():
        ch = CyberHuman(name=name, user_id=uid)
        personality = create_personality(persona_key=key)
        ch.personality = personality
        sandbox.add_ch(ch, personality)

    # 预填充初始关系
    for ch in sandbox.chs.values():
        for other in sandbox.chs.values():
            if ch.id != other.id:
                prob = random.uniform(0.20, 0.50)
                ch.relations[other.id] = prob
                sandbox.relation_matrix[(ch.id, other.id)] = prob

    return sandbox


def demo_chatlog_import(sandbox: ChatSandbox):
    """
    演示：导入聊天记录文件，初始化 CH 私人记忆
    支持格式：微信TXT / JSON / CSV
    """
    # 尝试导入 examples/ 目录下的示例文件
    import glob
    base = os.path.dirname(os.path.abspath(__file__))
    for pattern in [
        f"{base}/examples/*.txt",
        f"{base}/examples/*.json",
        f"{base}/examples/*.csv",
    ]:
        for filepath in glob.glob(pattern):
            fname = os.path.basename(filepath)
            print(f"\n📥 检测到聊天记录: {fname}")
            counts = sandbox.import_chatlogs(filepath, {})
            for ch_name, n in counts.items():
                print(f"  → {ch_name}: {n} 条消息")
            break


def run_simulation(sandbox: ChatSandbox, rounds: int = 20, delay: float = 0.5):
    print(f"\n▶ 开始运行 ({rounds} 轮)...\n")
    for i in range(1, rounds + 1):
        print(f"{'─'*55}")
        print(f"【Round {i}/{rounds}】")
        events = sandbox.tick()

        if events:
            for e in events:
                print(e)
        else:
            states = [(ch.name, ch.state.value) for ch in sandbox.chs.values()]
            print(f"  (本轮平静，状态: {', '.join(f'{n}={s}' for n,s in states)})")

        changed = []
        for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
            if ida < idb:
                changed.append(f"{sandbox.chs[ida].name}-{sandbox.chs[idb].name}:{prob:.2f}")
        print(f"  关系: {', '.join(changed)}")
        time.sleep(delay)

    return sandbox


def final_report(sandbox: ChatSandbox):
    print("\n" + "="*60)
    print("最终沙盒状态")
    print(sandbox.status())

    print("\n" + "="*60)
    print("人格系统报告")
    for ch in sandbox.chs.values():
        p = getattr(ch, "personality", None)
        if p:
            bf = p.big_five.dict()
            print(f"\n🦞 {ch.name} ({p.mbti_type}) — {p.big_five.dict()}")
            print(f"   聊天发起概率: {p.chat_probability():.2f}  |  "
                  f"共情: {p.empathy_score():.2f}  |  "
                  f"好奇心: {p.curiosity_level():.2f}")
            style = p.conversation_style()
            print(f"   风格: {'主动发起话题' if style['initiates_topics'] else '被动'} | "
                  f"{style['short_or_long']}回复 | {style['emotional_or_rational']}性")

    print("\n" + "="*60)
    print("记忆库")
    for ch_id, mem in sandbox.memory_systems.items():
        ch = sandbox.chs.get(ch_id)
        if not ch: continue
        print(f"\n🦞 {ch.name} ({len(mem.episodic)} 段记忆)：")
        for m in mem.recall_recent(5):
            age = mem._format_age(m.age())
            e = max(m.emotion_tags, key=lambda x: x[1])[0] if m.emotion_tags else "neutral"
            print(f"  [{age}] {m.summary[:50]} | 情绪:{e}")

    print("\n" + "="*60)
    print("睡眠整合记录")
    if sandbox.sleep_history:
        for s in sandbox.sleep_history[-5:]:
            print(f"\n🌙 Round {s['round']} | {s['ch_name']}")
            print(f"   {s['dream_summary'][:60]}")
            print(f"   重播{s['memories_replayed']}段 | 神经+{s['neural_change']:.3f} | "
                  f"情绪→{s['emotional_after']}")
    else:
        print("  (未触发睡眠整合)")

    print("\n" + "="*60)
    print("神经大脑状态")
    for ch in sandbox.chs.values():
        s = ch.brain.summary()
        print(f"\n🦞 {ch.name}: 神经元:{s['neurons']} 突触:{s['synapses']} "
              f"均强:{s['avg_weight']:.4f} 激活:{s['total_activation']:.4f}")

    print("\n演化日志 (最近15条)")
    for line in sandbox.log[-15:]:
        print(f"  {line}")


def main():
    print(intro())

    # ── LLM 配置提示 ──────────────────────────────────────
    llm = get_llm()
    if llm.provider == "mock":
        print("⚠️  当前为 mock 模式，对话为模板回复")
        print("   切换到真实 LLM：")
        print("   export LLM_PROVIDER=deepseek  # 或 openai / qwen")
        print("   export DEEPSEEK_API_KEY=sk-xxx")
        print("   然后重新运行 python3 main.py\n")
    else:
        print(f"✅ 使用真实 LLM: {llm.provider.upper()}\n")

    # ── 启动仪表盘 ──────────────────────────────────────
    print("🌐 启动实时仪表盘: http://localhost:5000")
    start_dashboard()
    time.sleep(0.5)

    # ── 创建沙盒 ────────────────────────────────────────
    sandbox = create_sandbox_with_chs()

    # 打印 CH 人格
    print("\n人格配置：")
    for ch in sandbox.chs.values():
        p = getattr(ch, "personality", None)
        if p:
            print(f"  🦞 {ch.name} ({p.mbti_type}) 外向={p.big_five.extraversion:.1f} "
                  f"共情={p.empathy_score():.2f} 神经质={p.big_five.neuroticism:.1f}")

    # 打印预填充关系
    print("\n预填充关系：")
    for (ida, idb), prob in sorted(sandbox.relation_matrix.items()):
        if ida < idb:
            na = sandbox.chs[ida].name
            nb = sandbox.chs[idb].name
            bar = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))
            print(f"  {na} → {nb}: [{bar}] {prob:.2f}")

    # ── 尝试导入聊天记录（如果有）───────────────────────
    demo_chatlog_import(sandbox)

    # ── 运行模拟 ────────────────────────────────────────
    sandbox = run_simulation(sandbox, rounds=20, delay=0.5)

    # ── 最终报告 ───────────────────────────────────────
    final_report(sandbox)

    print(f"\n{'='*60}")
    print(f"✅ Phase 1 运行完成！")
    print(f"   🌐 仪表盘仍在运行: http://localhost:5000")
    print(f"   📁 记忆数据: ./memory_store/")
    print(f"   🤖 LLM: {llm.provider.upper()}")
    print(f"\n   私人聊天记录导入：")
    print(f"   python3 -c \"")
    print(f"     from chat_sandbox import ChatSandbox; from chatlog_importer import create_importer;")
    print(f"     sb = ChatSandbox('MySereneX'); sb.import_chatlogs('your_chat.txt', {{}})\"")
    print(f"   \"")


if __name__ == "__main__":
    main()
