#!/usr/bin/env python3
"""
SereneX Phase 3 — 启动脚本
用法: python3 run_phase3.py [--days N] [--no-spawn]
"""
import sys
import time
import argparse

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from simulation import run_simulation, SimulationEngine


def main():
    parser = argparse.ArgumentParser(description="SereneX Phase 3 文明演化模拟")
    parser.add_argument("--days", type=int, default=30, help="运行天数（默认30）")
    parser.add_argument("--no-spawn", action="store_true", help="禁止自动生成新CH")
    parser.add_argument("--speed", type=float, default=1.0, help="模拟速度（一天=N秒）")
    args = parser.parse_args()

    print("🌍 SereneX Phase 3 — 文明演化沙盒")
    print("="*50)
    print(f"配置：{args.days}天，自动生成={'是' if not args.no_spawn else '否'}")
    print("="*50)

    engine, reports = run_simulation(
        num_days=args.days,
        auto_spawn=not args.no_spawn
    )

    print("\n✅ 模拟完成！")
    print(engine.get_world_summary())
    print("\n最近日记：")
    for name, ch in engine.chs.items():
        diaries = ch.memory.get_all_diaries(limit=3)
        if diaries:
            print(f"\n[{name}]")
            print(f"  最新：{diaries[-1]['date']} {diaries[-1]['text'][:100]}...")


if __name__ == "__main__":
    main()
