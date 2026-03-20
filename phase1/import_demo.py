#!/usr/bin/env python3
"""SereneX — 演示：导入微信聊天记录"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env
for line in open(".env", encoding="utf-8-sig"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

from chat_sandbox import ChatSandbox
from cyber_human import CyberHuman
from personality import create_personality
from chatlog_importer import create_importer

# 创建沙盒，加入群聊成员
sb = ChatSandbox("DashGroup")
members = [
    ("小明",    "u1", "xiaoming"),
    ("小李",    "u2", "analytical"),
    ("阿华",    "u3", "ahua"),
    ("小张",    "u4", "leader"),
    ("新时代孔乙己", "u5", "analytical"),
]
for name, uid, pkey in members:
    ch = CyberHuman(name=name, user_id=uid)
    ch.personality = create_personality(persona_key=pkey)
    sb.add_ch(ch, ch.personality)

# 导入聊天记录
filepath = "examples/聊天记录_dash群202403xx.txt"
print(f"📥 导入文件: {filepath}\n")
counts = sb.import_chatlogs(filepath, {})

print("=" * 50)
print("导入结果")
print("=" * 50)
for name, n in counts.items():
    print(f"  {name}: {n} 条消息")

print()
print("各CH记忆库状态：")
for ch in sb.chs.values():
    p = ch.personality
    print(f"  {ch.name}({p.mbti_type}) — {ch.episodic_memory_count}段记忆 | "
          f"情绪:{ch.emotion.dominant_tag().value}")

print()
print("最近3段记忆预览：")
for ch_id, mem in sb.memory_systems.items():
    ch = sb.chs.get(ch_id)
    if not ch or not mem.episodic:
        continue
    print(f"\n  🦞 {ch.name}:")
    for m in mem.recall_recent(3):
        e = max(m.emotion_tags, key=lambda x: x[1])[0] if m.emotion_tags else "neutral"
        print(f"    [{m.summary[:40]}] 情绪:{e}")

print(f"\n✅ 完成！共导入 {sum(counts.values())} 条消息")
