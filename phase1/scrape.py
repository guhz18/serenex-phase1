#!/usr/bin/env python3
"""
SereneX — 一键爬取博主内容 + 训练 CH

用法:
  python3 scrape.py bilibili <uid或主页URL>       # 爬取B站
  python3 scrape.py weibo <uid或主页URL>         # 爬取微博
  python3 scrape.py web <URL>                     # 爬取任意网页

示例:
  python3 scrape.py bilibili 672328094
  python3 scrape.py weibo 1195230310
  python3 scrape.py bilibili https://space.bilibili.com/672328094
  python3 scrape.py weibo https://weibo.com/u/6723462181
  python3 scrape.py web https://blog.example.com
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env
for line in open(".env", encoding="utf-8-sig"):
    k, v = line.strip().split("=", 1)
    os.environ[k] = v

from personality_infer import train_ch_from_url
from content_scraper import BilibiliScraper, WeiboScraper, WebPageScraper


def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print(__doc__)
        print("\n内置已支持平台:")
        print("  bilibili — B站用户视频/动态")
        print("  weibo    — 微博用户发布")
        print("  web      — 任意网页")
        print()
        print("直接示例:")
        print("  python3 scrape.py bilibili 672328094")
        print("  python3 scrape.py weibo 1195230310")
        print("  python3 scrape.py web https://example.com/blog")
        return

    platform = args[0].lower()
    target = " ".join(args[1:])  # 支持多空格ID

    print(f"\n{'='*55}")
    print(f"  SereneX 内容爬虫 — {platform.upper()}")
    print(f"{'='*55}\n")

    # 预处理URL
    uid_display = target
    if platform == "bilibili" and "://" in target:
        scraped = BilibiliScraper()
        uid = scraped.uid_from_url(target)
        if uid:
            uid_display = f"{target} → UID:{uid}"
        else:
            print("⚠️ 无法从URL提取B站UID，请直接提供数字UID")
            print("   例: python3 scrape.py bilibili 672328094")
            return
    elif platform == "weibo" and "://" in target:
        scraped = WeiboScraper()
        uid = scraped.uid_from_url(target)
        if uid:
            uid_display = f"{target} → UID:{uid}"
        else:
            print("⚠️ 无法从URL提取微博UID，请直接提供数字UID")
            print("   例: python3 scrape.py weibo 1195230310")
            return
    else:
        uid = target

    print(f"目标: {uid_display}")
    print(f"平台: {platform}\n")

    # 爬取 + 分析
    result = train_ch_from_url(platform, uid, limit=50)

    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        return

    # 输出报告
    print(f"\n{'='*55}")
    print("  📊 内容分析报告")
    print(f"{'='*55}")
    print(f"\n📌 基本信息")
    print(f"   平台: {result['platform']}")
    print(f"   用户ID: {result['user_id']}")
    print(f"   分析内容: {result['posts_analyzed']} 条")

    print(f"\n📌 推断人格")
    print(f"   MBTI: {result['mbti']}")
    bf = result["big_five"]
    print(f"   Big Five: 开放{bf['openness']:.2f} "
          f"| 尽责{bf['conscientiousness']:.2f} "
          f"| 外向{bf['extraversion']:.2f} "
          f"| 宜人{bf['agreeableness']:.2f} "
          f"| 神经{bf['neuroticism']:.2f}")

    print(f"\n📌 写作风格")
    ws = result["writing_style"]
    print(f"   平均句长: {ws['avg_sentence_length']:.0f}字")
    print(f"   Emoji频率: 每条{ws['emoji_per_post']:.1f}个")
    print(f"   问句比例: {ws['question_ratio']*100:.0f}%")
    print(f"   幽默度: {ws['humor_score']*100:.0f}%")
    print(f"   正式程度: {ws['formality']*100:.0f}%")

    print(f"\n📌 话题分布 (Top 8)")
    for word, count in result["top_topics"]:
        bar = "█" * min(count, 20)
        print(f"   {word:12s} {bar} ({count})")

    print(f"\n📌 情绪基调: {result['emotional_tone']}")
    print(f"📌 互动模式: {result['engagement_pattern']}")

    print(f"\n📌 人物描述 (LLM Persona)")
    print(f"   {result['persona_description']}")

    print(f"\n📌 内容样本 (前5条)")
    for i, p in enumerate(result["sample_posts"], 1):
        print(f"   [{i}] ({p['date']}) {p['content'][:60]}...")

    # 保存结果
    output_file = f"ch_profile_{platform}_{result['user_id']}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 报告已保存: {output_file}")
    print(f"   可用此文件初始化 CH:")
    print(f"   from personality_infer import train_ch_from_url")
    print(f"   result = train_ch_from_url('{platform}', '{result['user_id']}')")


if __name__ == "__main__":
    main()
