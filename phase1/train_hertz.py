#!/usr/bin/env python3
"""SereneX - 创建 Cyber G. Hertz CH"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ch_cyber_g_hertz import CH_HERTZ_PROFILE
from cyber_human import CyberHuman
from personality import PersonalityModel, BigFive
from emotion_tag import infer_emotions
from memory_system import MemorySystem


def create_hertz_ch():
    profile = CH_HERTZ_PROFILE
    bf_vals = profile["big_five"]
    bf = BigFive(**bf_vals)
    personality = PersonalityModel(mbti_type=profile["mbti"], big_five=bf)

    ch = CyberHuman(name=profile["name"], user_id=profile["uid"])
    ch.personality = personality

    mem_sys = MemorySystem(ch.id)
    for post in profile["sample_posts"]:
        emotions = infer_emotions(post["content"])
        mem_sys.store_dialogue(
            text=post["content"],
            participants=[ch.id],
            emotion_tags=emotions,
            summary=post["title"] + ": " + post["content"][:40],
        )
        kws = [kw for kw in profile["memory_keywords"] if kw in post["content"]]
        if kws:
            ch.brain.stimulate({kw: 0.7 for kw in kws}, strength=0.8)
        ch.episodic_memory_count += 1

    return ch


def demo():
    p = CH_HERTZ_PROFILE
    ch = create_hertz_ch()

    print("=== Cyber G. Hertz — CH 卡片 ===")
    print("真实原型:", p["real_name"], "| Bilibili UID:", p["source_id"])
    print("简介:", p["bio"])
    print()
    print("推断人格:")
    print("  MBTI:", p["mbti"])
    bf = p["big_five"]
    print("  Big Five:", bf)
    print()
    print("专业领域:", " | ".join(p["topics"]))
    print()
    print("说话风格:")
    ss = p["speaking_style"]
    print("  口头禅:", " / ".join(ss["catchphrases"]))
    print("  语言:", ss["language"])
    print()
    print("LLM Persona:")
    for line in p["persona"].split("。"):
        if line.strip():
            print(" ", line.strip()[:60], "。" if len(line) > 60 else "")
    print()
    print("CH 实体状态:")
    print("  ID:", ch.id)
    print("  姓名:", ch.name)
    print("  MBTI:", ch.personality.mbti_type)
    print("  记忆:", ch.episodic_memory_count, "段")
    print("  大脑激活:", round(sum(ch.brain.activation.values()), 3))
    print("  主导情绪:", ch.emotion.dominant_tag().value)
    print()
    print("=== 创建完成 ===")


if __name__ == "__main__":
    demo()
