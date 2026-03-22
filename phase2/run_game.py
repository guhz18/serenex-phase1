#!/usr/bin/env python3
"""快速启动：同时运行 CLI + 后台自动 tick"""
import subprocess, sys, time, os

# 加载.env
for line in open(".env", encoding="utf-8-sig"):
    try:
        k,v = line.strip().split("=",1); os.environ[k]=v
    except: pass

from game_sandbox import GameSandbox
from cyber_human import CyberHuman
from personality import create_personality
from game_world import Location

def boot():
    sb = GameSandbox("SereneX", app_storage_dir=os.path.join(os.path.dirname(__file__),"..","phase1","memory_store"))
    for key, name, uid in [("xiaoming","小明","xm"),("xiaoyu","小雨","xy"),("ahua","阿华","ah"),("hertz","Hertz","hz")]:
        ch = CyberHuman(name=name, user_id=uid)
        p = create_personality(persona_key=key); ch.personality = p
        sb.add_ch(ch, p)
    return sb

if __name__ == "__main__":
    sb = boot()
    print("自动运行10轮...")
    for i in range(1, 11):
        events = sb.tick()
        ts = sb.world.get_time_slot()
        print(f"\n【Round {i}/10】{ts}")
        for ch in sb.chat.chs.values():
            ns = sb.needs.get(ch.id)
            loc = sb.world.get_ch_location(ch.id)
            from needs_system import NeedLabel
            energy = ns.needs[NeedLabel.ENERGY].value if ns else 0
            mood   = ns.needs[NeedLabel.MOOD].value   if ns else 0
            print(f"  {ch.name} @ {loc.value} energy={energy:.2f} mood={mood:.2f}")
        for e in events: print(f"  {e}")
        time.sleep(0.5)
    print("\n✅ 完成！启动CLI: python game_cli.py")
    print("   启动仪表盘: python game_dashboard.py")
