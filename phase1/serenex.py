#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SereneX Phase 1 -- Unified CLI
Subcommands: chat | play | import | scrape | train | stats | web | gui
"""
from __future__ import print_function
import sys, os, argparse, time

# load .env
_ENV = "/workspace/SereneX/phase1/.env"
if os.path.exists(_ENV):
    for line in open(_ENV, encoding="utf-8-sig"):
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

sys.path.insert(0, "/workspace/SereneX/phase1")


# ── helpers ──────────────────────────────────────────────
_emoji = {"joy":"j7","sadness":"j8","anger":"j9","fear":"j10",
           "surprise":"j11","love":"j12","anxiety":"j13",
           "anticipation":"j14","neutral":"j0"}

_sb = None   # sandbox singleton

def get_sandbox():
    global _sb
    if _sb:
        return _sb
    from chat_sandbox import ChatSandbox
    from cyber_human import CyberHuman
    from personality import create_personality, PersonalityModel, BigFive
    from ch_cyber_g_hertz import CH_HERTZ_PROFILE
    import random
    hertz_bf = BigFive(**CH_HERTZ_PROFILE["big_five"])
    hertz_p = PersonalityModel(mbti_type=CH_HERTZ_PROFILE["mbti"], big_five=hertz_bf)
    _sb = ChatSandbox("SereneX-CLI")
    for key, name, uid, mbti in [
        ("xiaoming","小明","user_xm","ENFP"),
        ("xiaoyu","小雨","user_xy","INTJ"),
        ("ahua","阿华","user_ah","ISFJ"),
        ("hertz","Cyber G. Hertz","ch_hertz","INTP"),
    ]:
        ch = CyberHuman(name=name, user_id=uid)
        ch.personality = hertz_p if key == "hertz" else create_personality(persona_key=key)
        _sb.add_ch(ch, ch.personality)
    for ch in _sb.chs.values():
        for other in _sb.chs.values():
            if ch.id != other.id:
                p = random.uniform(0.25, 0.55)
                ch.relations[other.id] = p
                _sb.relation_matrix[(ch.id, other.id)] = p
    return _sb


def save_interaction(msg, responses):
    import json
    fpath = "/workspace/SereneX/phase1/chat_history.json"
    try:
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"conversation":[],"player_interventions":[]}
    except:
        data = {"conversation":[],"player_interventions":[]}
    if "player_interventions" not in data:
        data["player_interventions"] = []
    entry = {"player":"玩家","message":msg,"responses":responses,"time":time.time()}
    data["player_interventions"].append(entry)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── subcommands ──────────────────────────────────────────

def cmd_chat(rounds):
    from chat_sandbox import ChatSandbox
    import random
    rounds = int(rounds)
    sb = get_sandbox()
    print("")
    print("  [SereneX Chat  %d rounds]" % rounds)
    print("-" * 50)
    for i in range(1, rounds + 1):
        print("Round %d/%d" % (i, rounds))
        events = sb.tick()
        if events:
            for e in events:
                print("  %s" % e)
        else:
            print("  (平静)")
        time.sleep(0.3)
    print("")
    print("-" * 50)
    print("  FINAL STATUS")
    print("-" * 50)
    for ch in sb.chs.values():
        p = ch.personality
        print("  %s(%s) mem=%d emotion=%s" % (
            ch.name, p.mbti_type, ch.episodic_memory_count, ch.emotion.dominant_tag().value))
    print("")


def cmd_play(message):
    print("")
    print("YOU: %s" % message)
    sb = get_sandbox()
    responses = sb.player_send("玩家", message)
    for r in responses:
        e = _emoji.get(r["emotion"], "j0")
        print("%s %s(%s): %s" % (e, r["speaker"], r["ch_mbti"], r["text"]))
    save_interaction(message, responses)
    print("")


def cmd_stats():
    print("")
    print("  [CH STATUS]")
    print("-" * 50)
    sb = get_sandbox()
    for ch in sb.chs.values():
        p = ch.personality
        ba = sum(ch.brain.activation.values())
        print("  %s(%s) mem=%d emotion=%s brain=%.3f" % (
            ch.name, p.mbti_type, ch.episodic_memory_count,
            ch.emotion.dominant_tag().value, ba))
    print("")


def cmd_web(port):
    import threading
    from dashboard_server import start_server
    port = int(port)
    t = threading.Thread(target=start_server, args=(port,), daemon=True)
    t.start()
    print("Web dashboard: http://localhost:%d" % port)
    print("Press Ctrl+C to stop")
    try:
        while True: time.sleep(3600)
    except KeyboardInterrupt:
        print("bye")


def cmd_gui():
    print("")
    print("  [SereneX TUI]  type /quit to exit, /stats for status")
    print("-" * 50)
    sb = get_sandbox()
    while True:
        try:
            user_input = raw_input("\nYOU > ").strip() if sys.version_info[0] < 3 else input("\nYOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("bye!")
            break
        if not user_input:
            continue
        if user_input in ("/quit","/exit","/q"):
            print("bye!")
            break
        if user_input in ("/stats","/s"):
            for ch in sb.chs.values():
                print("  %s: %s" % (ch.name, ch.emotion.dominant_tag().value))
            continue
        responses = sb.player_send("玩家", user_input)
        for r in responses:
            e = _emoji.get(r["emotion"], "j0")
            print("  %s %s: %s" % (e, r["speaker"], r["text"][:80]))
        save_interaction(user_input, responses)


# ── main ───────────────────────────────────────────────
HELP_TEXT = """
SereneX CLI  --  Cyber Human Neural Sandbox

Subcommands:
  chat   [-r N]       Run sandbox simulation (default 20 rounds)
  play   <message>    Player broadcast message to all CHs
  import <filepath>   Import chat log file
  scrape <platform> <target>  Scrape blogger content
  train  <platform> <target> [-n name]  Train new CH profile
  stats             Show all CHs status
  web    [-p port]   Start web dashboard (default port 5000)
  gui              Start TUI terminal interface

Examples:
  python3 serenex.py chat -r 10
  python3 serenex.py play Hello everyone
  python3 serenex.py stats
  python3 serenex.py web -p 5000
  python3 serenex.py gui
"""

def main():
    if len(sys.argv) < 2:
        print(HELP_TEXT)
        return
    cmd = sys.argv[1]

    if cmd == "chat":
        rounds = 20
        for a in sys.argv[2:]:
            if a.isdigit():
                rounds = int(a)
        cmd_chat(rounds)

    elif cmd == "play":
        if len(sys.argv) < 3:
            print("Usage: serenex.py play <message>")
            return
        message = " ".join(sys.argv[2:])
        cmd_play(message)

    elif cmd == "stats":
        cmd_stats()

    elif cmd == "web":
        port = 5000
        for a in sys.argv[2:]:
            if a.isdigit():
                port = int(a)
        cmd_web(port)

    elif cmd == "gui":
        cmd_gui()

    elif cmd == "import":
        if len(sys.argv) < 3:
            print("Usage: serenex.py import <filepath>")
            return
        filepath = sys.argv[2]
        sb = get_sandbox()
        from chatlog_importer import create_importer
        counts = sb.import_chatlogs(filepath, {})
        print("Imported: %s" % counts)

    elif cmd == "scrape":
        if len(sys.argv) < 4:
            print("Usage: serenex.py scrape <platform> <target>")
            print("  platform: bilibili | weibo | web")
            return
        platform = sys.argv[2]
        target = sys.argv[3]
        from personality_infer import train_ch_from_url
        print("Scraping %s %s..." % (platform, target))
        r = train_ch_from_url(platform, target)
        if "error" in r:
            print("Error: %s" % r["error"])
        else:
            print("Done! MBTI=%s topics=%s" % (r.get("mbti"), r.get("topics",[])[:3]))

    elif cmd == "train":
        if len(sys.argv) < 4:
            print("Usage: serenex.py train <platform> <target> [-n name]")
            return
        platform = sys.argv[2]
        target = sys.argv[3]
        name = None
        if "-n" in sys.argv:
            idx = sys.argv.index("-n")
            name = sys.argv[idx+1] if idx+1 < len(sys.argv) else None
        from personality_infer import train_ch_from_url
        print("Training CH from %s %s..." % (platform, target))
        r = train_ch_from_url(platform, target)
        if "error" in r:
            print("Error: %s" % r["error"])
        else:
            print("Done! MBTI=%s" % r.get("mbti"))

    else:
        print("Unknown command: %s" % cmd)
        print(HELP_TEXT)


if __name__ == "__main__":
    main()
