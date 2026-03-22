#!/usr/bin/env python3
"""
SereneX Phase 2 — 交互式 CLI
支持命令：
  tick [N]        — 运行N轮（默认1轮）
  status / st     — 显示当前状态
  go <CH> <地点>  — 移动角色到某地
  msg <CH> <消息> — 向某角色发消息
  broadcast <msg> — 广播消息给所有人
  event <描述>    — 触发一个特殊事件
  do <CH> <活动>  — 让角色做活动（rest/work/chat/eat/exercise/explore/alone）
  quest / q      — 显示任务
  log / l        — 显示最近日志
  help / h       — 帮助
  quit / exit    — 退出
"""

import sys, os, time
from needs_system import NeedLabel

# 加载 .env
for line in open(".env", encoding="utf-8-sig"):
    try:
        k, v = line.strip().split("=", 1)
        os.environ[k] = v
    except:
        pass

from game_sandbox import GameSandbox
from game_world import Location, PLACES, TIME_SLOTS
from cyber_human import CyberHuman
from personality import create_personality

# ── 彩色输出 ──────────────────────────────────────
C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "dim": "\033[2m",
}
P = "{C['bold']}{C['cyan']}"
OK = f"{C['green']}✅{C['reset']}"
WARN = f"{C['yellow']}⚠️ {C['reset']}"
INFO = f"{C['blue']}ℹ️ {C['reset']}"
BELL = f"{C['magenta']}🔔{C['reset']}"


def c(text: str, color: str) -> str:
    return f"{C.get(color,'')}{text}{C['reset']}"


def banner():
    print(f"""
{C['bold']}{C['cyan']}
╔══════════════════════════════════════════════╗
║   🦞 SereneX Phase 2 — AI 社群模拟 CLI        ║
║   Game Sandbox + DeepSeek LLM                ║
╚══════════════════════════════════════════════╝
{C['reset']}
  命令帮助 → help 或 h
""".strip())


def color_location(loc_id: str) -> str:
    colors = {
        "home": "yellow",
        "park": "green",
        "cafe": "magenta",
        "office": "blue",
        "mall": "red",
        "library": "cyan",
    }
    return c(PLACES[Location(loc_id)].name, colors.get(loc_id, "white"))


# ── 迷你仪表盘 ───────────────────────────────────
def mini_dashboard(sb: GameSandbox):
    print()
    ts = sb.world.get_time_slot()
    day = sb.world.day
    events = sb.world.today_events

    print(f"  {C['bold']}{C['cyan']}╭─ {ts} Day{day} ──────────────────────{C['reset']}")

    for ch in sb.chat.chs.values():
        ns = sb.needs.get(ch.id)
        loc = sb.world.get_ch_location(ch.id)
        loc_name = color_location(loc.value)

        def m(label, val):
            color = "green" if val > 0.6 else ("yellow" if val > 0.3 else "red")
            bar = "█" * int(val * 5) + "░" * (5 - int(val * 5))
            return f"{c(label, 'dim')}{c(bar, color)}"

        energy = ns.needs[NeedLabel.ENERGY].value if ns else 0
        mood   = ns.needs[NeedLabel.MOOD].value   if ns else 0
        social = ns.needs[NeedLabel.SOCIAL].value  if ns else 0
        emo = ch.emotion.dominant_tag().value

        print(f"  │ {C['bold']}{ch.name:<8}{C['reset']} {loc_name:<4} "
              f"{m('⚡', energy)} {m('😊', mood)} {m('💬', social)} {emo}")

    print(f"  {C['cyan']}╰{'─'*40}{C['reset']}")

    if events:
        print(f"  {BELL} 今日事件：{' '.join(events)}")
    print()


# ── 初始化沙盒 ───────────────────────────────────
def init_sandbox() -> GameSandbox:
    sb = GameSandbox("SereneX", app_storage_dir=os.path.join(os.path.dirname(__file__), "..", "phase1", "memory_store"))

    configs = [
        ("xiaoming", "小明", "user_xm"),
        ("xiaoyu",   "小雨", "user_xy"),
        ("ahua",     "阿华", "user_ah"),
        ("hertz",    "Hertz", "ch_hertz"),
    ]
    for key, name, uid in configs:
        ch = CyberHuman(name=name, user_id=uid)
        p = create_personality(persona_key=key)
        ch.personality = p
        sb.add_ch(ch, p)

    print(f"{OK} 沙盒已初始化，4个角色就绪（DeepSeek LLM）")
    print(f"{INFO} 输入 {C['bold']}help{C['reset']} 查看命令\n")
    return sb


# ── 命令处理 ─────────────────────────────────────
def cmd_tick(sb: GameSandbox, args: list):
    n = int(args[0]) if args else 1
    n = min(n, 20)
    print(f"\n{C['dim']}⏳ 运行 {n} 轮...{C['reset']}")
    for i in range(n):
        events = sb.tick()
        mini_dashboard(sb)
        if events:
            for e in events:
                if e.strip():
                    print(f"  {e}")
        if i < n - 1:
            time.sleep(0.3)
    print(f"{C['dim']}  ↗ 共运行 {n} 轮{C['reset']}")


def cmd_status(sb: GameSandbox, _):
    print()
    print(sb.status())


def cmd_go(sb: GameSandbox, args: list):
    if len(args) < 2:
        print(f"{WARN} 用法: go <角色名> <地点>")
        print(f"  地点: {', '.join(l.value for l in Location)}")
        return
    ch_name, loc_str = args[0], args[1]
    result = sb.player_move(ch_name, loc_str)
    print(result)


def cmd_msg(sb: GameSandbox, args: list):
    if len(args) < 2:
        print(f"{WARN} 用法: msg <角色名> <消息内容>")
        return
    ch_name, message = args[0], " ".join(args[1:])
    responses = sb.player_send("玩家", message, target_ch=ch_name)
    print(f"\n{BELL} {c(ch_name, 'bold')} 收到消息：「{message}」")
    for r in responses:
        if ch_name == "" or r["speaker"] == ch_name:
            print(f"  {c(r['speaker'], 'cyan')} 回复：{r['text']}")


def cmd_broadcast(sb: GameSandbox, args: list):
    if not args:
        print(f"{WARN} 用法: broadcast <消息内容>")
        return
    message = " ".join(args)
    responses = sb.player_send("玩家", message)
    print(f"\n{BELL} 广播：「{message}」")
    for r in responses:
        print(f"  {c(r['speaker'], 'cyan')} 回复：{r['text']}")


def cmd_event(sb: GameSandbox, args: list):
    if not args:
        print(f"{WARN} 用法: event <事件描述>")
        return
    desc = " ".join(args)
    msg = sb.player_trigger_event("custom", desc)
    print(f"{OK} {msg}")


def cmd_do(sb: GameSandbox, args: list):
    if len(args) < 2:
        print(f"{WARN} 用法: do <角色名> <活动>")
        print(f"  活动: rest | work | chat | eat | exercise | explore | alone")
        return
    result = sb.player_assign_activity(args[0], args[1])
    print(result)


def cmd_quest(sb: GameSandbox, _):
    print()
    print("━━━ 任务 ━━━")
    print(sb.quests.status())
    print()
    print(f"{C['dim']}  历史完成：{sb.quests.completed_summary()}{C['reset']}")


def cmd_log(sb: GameSandbox, _):
    print()
    print("━━━ 最近日志 ━━━")
    log = sb.chat.log[-20:]
    if not log:
        print("  （空）")
    for entry in log:
        print(f"  {entry}")


def cmd_help(_):
    print(f"""
{C['bold']}SereneX Phase 2 — 命令帮助{C['reset']}

  {C['green']}tick [N]{C['reset']}      运行 N 轮游戏（默认1轮，最多20轮）
                每轮 = 游戏内1小时，日夜交替自动推进

  {C['green']}status / st{C['reset']}  显示完整沙盒状态（角色、关系、任务）

  {C['green']}go <人> <地>{C['reset']}  移动角色到指定地点
                地点: home | park | cafe | office | mall | library
                示例: go 小明 cafe

  {C['green']}msg <人> <内容>{C['reset']}  向角色发送私信
                示例: msg 小明 今天心情怎么样？

  {C['green']}broadcast <内容>{C['reset']}  广播消息给所有人
                示例: broadcast 今晚咖啡馆聚会！

  {C['green']}event <描述>{C['reset']}  触发一个特殊事件（影响所有角色心情）
                示例: event 突然下起了大雨！

  {C['green']}do <人> <活动>{C['reset']}  让角色执行活动
                活动: rest | work | chat | eat | exercise | explore | alone

  {C['green']}quest / q{C['reset']}   显示当前任务进度

  {C['green']}log / l{C['reset']}      显示最近事件日志

  {C['green']}clear{C['reset']}        清屏

  {C['green']}quit / exit{C['reset']}  退出
""".strip())


COMMANDS = {
    "tick": cmd_tick,
    "status": cmd_status,
    "st": cmd_status,
    "go": cmd_go,
    "msg": cmd_msg,
    "broadcast": cmd_broadcast,
    "event": cmd_event,
    "do": cmd_do,
    "quest": cmd_quest,
    "q": cmd_quest,
    "log": cmd_log,
    "l": cmd_log,
    "help": cmd_help,
    "h": cmd_help,
    "clear": lambda _: os.system("clear") or print("已清屏"),
}


def main():
    os.system("clear")
    banner()
    sb = init_sandbox()
    mini_dashboard(sb)

    while True:
        try:
            raw = input(f"{C['bold']}{C['magenta']}serenex>{C['reset']} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C['dim']}再见！{C['reset']}")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("quit", "exit", "q"):
            print(f"{C['dim']}bye~{C['reset']}")
            break

        if cmd in COMMANDS:
            try:
                COMMANDS[cmd](sb, args)
            except Exception as e:
                print(f"{C['red']}❌ 错误：{e}{C['reset']}")
        else:
            print(f"{WARN} 未知命令: {cmd}，输入 help 查看帮助")


if __name__ == "__main__":
    main()
