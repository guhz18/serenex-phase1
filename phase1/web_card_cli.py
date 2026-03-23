#!/usr/bin/env python3
"""
SereneX — 网页 → CH 卡片 CLI
用法：
  python3 web_card_cli.py <ucl_url> [--name 名字] [--desc 描述]
  python3 web_card_cli.py list
  python3 web_card_cli.py load <文件名>
  python3 web_card_cli.py import <文件名>   # 导入卡片到当前沙盒
"""

import sys, os, json, time, re, argparse
from pathlib import Path

# ── 加载 .env ──────────────────────────────────────────────
for line in open(".env", encoding="utf-8-sig"):
    try:
        k, v = line.strip().split("=", 1)
        os.environ[k] = v
    except:
        pass

# ── 内部模块 ────────────────────────────────────────────────
from ch_card import CHCard, CARDS_DIR
from content_scraper import WebPageScraper, ContentScraper
from personality_infer import PersonalityInferrer


# ── UCL 内容清洗 ────────────────────────────────────────────
def clean_ucl_content(raw_text: str) -> str:
    """去除 UCL 网页噪声（导航、页脚、Cookie 提示等）"""
    if not raw_text:
        return ""
    lines = raw_text.split("\n")
    cleaned = []
    skip_patterns = [
        r"cookie", r"privacy policy", r"terms of use",
        r"accessibility", r"ucl home", r"main navigation",
        r"skip to", r"copyright", r"student central",
        r"research domains", r"by topic", r"follow us",
    ]
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) < 20:  # 太短的行跳过
            continue
        if any(re.search(p, line, re.I) for p in skip_patterns):
            continue
        cleaned.append(line)
    return "\n".join(cleaned[:300])  # 最多 300 行


# ── 核心生成函数 ────────────────────────────────────────────
def _fetch_with_curl(url: str) -> str:
    """curl 替代方案（处理反爬严格的网站）"""
    import subprocess, shlex
    cmd = (
        f"curl -s -L --max-time 15 "
        f"-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' "
        f"-H 'Accept: text/html,application/xhtml+xml' "
        f"-H 'Accept-Language: en-GB,en;q=0.9' "
        f"-H 'Accept-Encoding: gzip, deflate, br' "
        f"--compressed "
        f"{shlex.quote(url)}"
    )
    try:
        return subprocess.check_output(cmd, shell=True, timeout=15).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠️ curl 也失败了: {e}")
        return ""


def generate_card_from_url(url: str, name: str = "", description: str = "") -> CHCard:
    """抓取网页 → 提取内容 → 推断人格 → 生成 CH 卡片"""
    print(f"🌐 正在抓取: {url}")

    scraper = WebPageScraper()
    posts = scraper.scrape(url)

    raw_content = ""
    if posts:
        post = posts[0]
        raw_content = post.content
        if not name and post.author:
            name = post.author.split("|")[0].strip()[:20]
        print(f"✅ 抓取完成（WebScraper），内容长度: {len(raw_content)} 字符")
    else:
        # fallback 1: curl
        raw_content = _fetch_with_curl(url)
        if raw_content:
            print(f"✅ curl 备用方案成功，内容长度: {len(raw_content)} 字符")
        else:
            print("⚠️ 未能抓取到内容，将使用示例内容生成演示卡片")

    content = clean_ucl_content(raw_content) if raw_content else ""

    if len(content) < 200:
        content = (raw_content or "")[:2000] or "示例内容：这是一个来自 UCL 的学术型人格卡片。"
        print(f"⚠️ 内容过短，使用 {'原始内容前2000字' if raw_content else '示例内容'}")

    print(f"📝 最终分析内容长度: {len(content)} 字符")

    # 人格推断
    print(f"🧠 正在分析人格特征...")
    inferrer = PersonalityInferrer()
    profile = inferrer.infer(content)

    # CH 名字：优先用用户指定 > 从标题提取
    if not name:
        title = scraper.title or url.split("/")[-1].replace("-", " ").replace("_", " ")
        # 取第一个有意义的词
        words = [w for w in title.split() if len(w) > 2 and w.lower() not in ("page", "home", "index", "ucl")]
        name = words[0] if words else "UCL_User"

    card = CHCard(
        name=name,
        source_url=url,
        source_title=posts[0].author if posts else "",
        description=description or f"从 {url} 生成的 Cyber Human",
        mbti=profile.suggested_mbti,
        big_five=profile.suggested_big_five,
        persona_description=profile.persona_description,
        role_type=_infer_role_type(content),
        writing_style=asdict(profile.writing_style) if profile.writing_style else {},
        memory_snippets=_extract_memory_snippets(content, profile),
        emotion_tags=list(set(
            [profile.emotional_tone]
            + (profile.engagement_pattern.split("/") if profile.engagement_pattern else [])
        )),
        relations={},
    )
    return card


def _infer_role_type(content: str) -> str:
    """从内容领域推断角色类型"""
    content_lower = content.lower()
    keywords = {
        "blogger": ["blog", "post", "article", "writing", "分享", "文章"],
        "academic": ["research", "study", "paper", "professor", "phd", "ucl", "university", "学术", "研究"],
        "developer": ["code", "github", "programming", "software", "开发", "编程", "工程师"],
        "designer": ["design", "ui", "ux", "creative", "设计"],
        "data_scientist": ["data", "ml", "machine learning", "ai", "analytics", "数据", "机器学习"],
    }
    for role, kws in keywords.items():
        if any(kw in content_lower for kw in kws):
            return role
    return "general"


def _extract_memory_snippets(content: str, profile) -> list:
    """从内容中提取关键记忆片段"""
    snippets = []
    # 取高频话题词作为记忆
    if profile.top_topics:
        for word, count in profile.top_topics[:5]:
            if len(word) > 1 and count > 1:
                snippets.append(f"关注领域: {word}（提及 {count} 次）")
    # 推断身份
    if profile.engagement_pattern and isinstance(profile.engagement_pattern, str):
        snippets.append(f"互动风格: {profile.engagement_pattern}")
    return snippets[:8]  # 最多 8 条


def asdict(obj):
    """兼容 dataclass 和普通 dict"""
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import fields
        return {f.name: asdict(getattr(obj, f.name)) for f in fields(obj)}
    elif isinstance(obj, list):
        return [asdict(x) if hasattr(x, "__dataclass_fields__") else x for x in obj]
    elif isinstance(obj, dict):
        return {k: asdict(v) for k, v in obj.items()}
    return obj


# ── CLI 命令 ────────────────────────────────────────────────
def cmd_scrape(args):
    url = args.url
    if not url.startswith("http"):
        url = "https://" + url
    card = generate_card_from_url(url, name=args.name, description=args.desc)
    path = card.save()
    print(f"\n✅ CH 卡片已生成: {path}")
    print(f"\n{card.to_json()}")
    return card


def cmd_list(args):
    cards = list(CARDS_DIR.glob("*.json"))
    if not cards:
        print("📭 暂无卡片，运行 `python3 web_card_cli.py scrape <url>` 创建第一张！")
        return
    print(f"📦 CH 卡片库 ({len(cards)} 张)\n")
    for p in sorted(cards):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        print(f"  [{p.stem}]")
        print(f"    名字: {data.get('name', '?')}")
        print(f"    MBTI: {data.get('mbti', '?')}  |  角色: {data.get('role_type', '?')}")
        print(f"    来源: {data.get('source_url', '?')[:60]}...")
        print(f"    卡片文件: {p.name}")
        print()


def cmd_load(args):
    path = Path(args.file)
    if not path.is_absolute():
        path = CARDS_DIR / path
    if not path.exists():
        path = CARDS_DIR / f"{args.file}.json"
    card = CHCard.load(str(path))
    print(f"📄 加载卡片: {card.name}\n")
    print(card.to_json())


def cmd_import(args):
    """将卡片导入为 CyberHuman 实例（预览用）"""
    path = Path(args.file)
    if not path.exists():
        path = CARDS_DIR / path
    card = CHCard.load(str(path))
    from cyber_human import CyberHuman
    from personality import create_personality
    ch = CyberHuman(**card.to_cyber_human_kwargs())
    p = create_personality(persona_key=card.mbti.lower() if card.mbti else "xiaoming")
    ch.personality = p
    print(f"✅ 卡片已导入为 CyberHuman:")
    print(f"   名字: {ch.name}")
    print(f"   MBTI: {card.mbti}")
    print(f"   描述: {card.persona_description[:80]}...")
    return ch


# ── 主入口 ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SereneX CH Card CLI — 网页 → 可移植人格卡片")
    sub = parser.add_subparsers()

    p_scrape = sub.add_parser("scrape", help="抓取 UCL 网页并生成 CH 卡片")
    p_scrape.add_argument("url", help="UCL 网页 URL")
    p_scrape.add_argument("--name", "-n", default="", help="指定 CH 名字")
    p_scrape.add_argument("--desc", "-d", default="", help="卡片描述")

    sub.add_parser("list", help="列出所有已生成的 CH 卡片")

    p_load = sub.add_parser("load", help="查看卡片 JSON 内容")
    p_load.add_argument("file", help="卡片文件名或路径")

    p_import = sub.add_parser("import", help="将卡片导入为 CyberHuman 实例（测试用）")
    p_import.add_argument("file", help="卡片文件名或路径")

    args = parser.parse_args()

    if hasattr(args, "url"):
        cmd_scrape(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "load":
        cmd_load(args)
    elif args.command == "import":
        cmd_import(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
