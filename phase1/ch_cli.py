#!/usr/bin/env python3
"""
SereneX — CH Card CLI
生成、列出、加载可移植的 Cyber Human 卡片

用法:
  python3 ch_cli.py gen <URL>                 # 从网页生成卡片
  python3 ch_cli.py gen <URL> --name 张三      # 指定 CH 名字
  python3 ch_cli.py gen <URL> --name 张三 --limit 5  # 限制分析条数
  python3 ch_cli.py list                      # 列出所有卡片
  python3 ch_cli.py show <卡片文件名>          # 查看卡片内容
  python3 ch_cli.py load <卡片文件名>          # 加载卡片（打印可导入的 Python dict）

Cards 保存位置: phase1/cards/*.json
"""
import sys, os, json, re, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env
_env_path = os.path.join(os.path.dirname(__file__), "phase1", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path, encoding="utf-8-sig"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
else:
    _env_path2 = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path2):
        for line in open(_env_path2, encoding="utf-8-sig"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from ch_card import CHCard, CARDS_DIR
from content_scraper import WebPageScraper, create_scraper, Post
from personality_infer import PersonalityInferrer


# ── MCP 网页提取 ────────────────────────────────────────────────
# 用于从无法直接 HTTP 访问的环境（MCP 沙盒）提取网页内容

def _fetch_via_mcp(url: str, timeout: int = 15) -> str:
    """通过 OpenClaw MCP extract_content_from_websites 工具提取网页"""
    import subprocess, json, tempfile, os

    script = f"""
import sys, json
try:
    from matrix_mcp import matrix_mcp as mcp
    result = mcp.extract_content_from_websites({{
        "tasks": [{{"url": "{url}", "prompt": "提取页面完整文本内容", "task_name": "fetch"}}]
    }})
    print(result)
except ImportError:
    print(json.dumps({{"error": "MCP not available, use direct HTTP"}}))
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(script)
        tmp = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp], capture_output=True, text=True, timeout=timeout + 5
        )
        output = result.stdout.strip()
        if output:
            data = json.loads(output)
            if isinstance(data, dict) and "error" not in data:
                # 解析 MCP 返回的内容
                content_list = data.get("content", [])
                if content_list and isinstance(content_list[0], dict):
                    return content_list[0].get("text", "")
    finally:
        os.unlink(tmp)
    return ""


# ── 网页 → CH Card ──────────────────────────────────────────────

def generate_card_from_url(url: str, name: str = None, limit: int = 20,
                            use_mcp: bool = True) -> CHCard:
    """
    爬取网页 + 推断人格 + 生成 CH Card

    use_mcp: True 则优先通过 MCP 工具提取（沙盒环境），
             False 则用直接 HTTP（用户本机环境）
    """
    print(f"\n🌐 爬取网页: {url}")

    content_text = ""
    if use_mcp:
        print("   [通过 MCP 工具提取...]")
        content_text = _fetch_via_mcp(url)
        if content_text:
            print(f"   MCP 提取成功: {len(content_text)} 字")

    # 如果 MCP 失败，尝试直接 HTTP
    if not content_text:
        print("   [回退到直接 HTTP...]")
        scraper = WebPageScraper()
        posts = scraper.scrape(url, limit=limit)
        if posts:
            content_text = posts[0].content
            title = posts[0].author

    if not content_text or len(content_text) < 50:
        raise ValueError(
            f"无法从 {url} 提取到有效内容（{len(content_text)} 字）。\n"
            f"请检查: 1) URL 是否正确  2) 网络是否可达  "
            f"3) 网站是否允许爬取\n"
            f"提示: 本机运行前请确保已安装依赖: pip install -r requirements.txt"
        )

    # 提取标题（从 URL 或内容）
    title = _extract_title_from_content(content_text) or url
    content_snippet = content_text[:200]
    print(f"   标题: {title}")
    print(f"   内容长度: {len(content_text)} 字")

    # 如果没有指定名字，从标题提取
    if not name:
        name = _extract_name_from_title(title)
        print(f"   推断名字: {name}")

    # 用 WebPageScraper 的平台标记
    print(f"\n🧠 推断人格（分析 {len(content_text)} 字内容）...")
    # 构建合成 Post 对象（复用 WebPageScraper 逻辑，但不重复请求）
    synthetic_post = Post(
        platform="web",
        author=title,
        content=content_text,
        timestamp=0,
        date_str="",
        url=url,
    )
    inferrer = PersonalityInferrer([synthetic_post])
    profile = inferrer.analyze()

    # BigFive 是 dataclass，转为 O-C-E-A-N 格式 dict
    bf = profile.suggested_big_five
    bf_dict = {
        "O": round(bf.openness, 3),
        "C": round(bf.conscientiousness, 3),
        "E": round(bf.extraversion, 3),
        "A": round(bf.agreeableness, 3),
        "N": round(bf.neuroticism, 3),
    }

    result = {
        "platform": "web",
        "user_id": url,
        "posts_analyzed": 1,
        "top_topics": profile.top_topics,
        "emotional_tone": profile.emotional_tone,
        "engagement_pattern": profile.engagement_pattern,
        "mbti": profile.suggested_mbti,
        "big_five": bf_dict,
        "persona_description": profile.persona_description,
        "writing_style": {
            "avg_sentence_length": round(profile.writing_style.avg_sentence_length, 1),
            "emoji_per_post": round(profile.writing_style.emoji_count_per_post, 2),
            "question_ratio": round(profile.writing_style.question_ratio, 2),
            "humor_score": round(profile.writing_style.humor_score, 2),
            "formality": round(profile.writing_style.formality, 2),
        },
        "sample_posts": [{"content": content_text[:100], "date": ""}],
    }

    # 提取记忆片段（Top话题前5条）
    memory_snippets = [f"关于「{topic}」的话题" for topic, _ in result.get("top_topics", [])[:5]]

    # 情绪标签
    emotion_tags = [result.get("emotional_tone", "中性")]

    # 角色类型推断
    role_type = _infer_role_type(result)

    card = CHCard(
        name=name or title,
        source_url=url,
        source_title=title,
        description=result.get("persona_description", ""),
        mbti=result.get("mbti", "INTP"),
        big_five=result.get("big_five", {"O":0.5,"C":0.5,"E":0.5,"A":0.5,"N":0.5}),
        persona_description=result.get("persona_description", ""),
        role_type=role_type,
        writing_style={
            "avg_sentence_length": result.get("writing_style", {}).get("avg_sentence_length", 20),
            "emoji_per_post": result.get("writing_style", {}).get("emoji_per_post", 0),
            "question_ratio": result.get("writing_style", {}).get("question_ratio", 0.1),
            "humor_score": result.get("writing_style", {}).get("humor_score", 0.1),
            "formality": result.get("writing_style", {}).get("formality", 0.5),
        },
        memory_snippets=memory_snippets,
        emotion_tags=emotion_tags,
        relations={},
    )
    return card


def _extract_name_from_title(title: str) -> str:
    """从网页标题简单推断人物名字"""
    # 去掉常见前缀后缀
    t = re.sub(r"^(博客|文章|日志|记录|我的|首页|个人)\s*[-–—|]\s*", "", title)
    t = re.sub(r"\s*[-–—|]\s*(博客|文章|网站|主页|UCL|University).*$", "", t)
    t = t.strip()
    # 截取前20字符
    return t[:20] or "CH_Web"


def _extract_title_from_content(content: str) -> str:
    """从内容前200字中尝试提取标题（取第一行或第一句）"""
    if not content:
        return ""
    first_line = content.split("\n")[0].strip()
    if 5 < len(first_line) < 100 and not first_line.startswith("http"):
        return first_line
    # 取前50字
    return content[:50].strip()


def _infer_role_type(result: dict) -> str:
    """从话题和内容推断角色类型"""
    topics = " ".join([t for t, _ in result.get("top_topics", [])])
    topics_lower = topics.lower()

    if any(k in topics_lower for k in ["ai", "机器学习", "深度学习", "python", "算法", "代码", "编程", "nlp"]):
        return "developer"
    elif any(k in topics_lower for k in ["研究", "论文", "学术", "实验", "data", "science"]):
        return "academic"
    elif any(k in topics_lower for k in ["设计", "ui", "ux", "创意", "艺术", "visual"]):
        return "designer"
    elif any(k in topics_lower for k in ["产品", "运营", "增长", "商业", "marketing"]):
        return "product"
    elif any(k in topics_lower for k in ["心理", "情感", "哲学", "思考", "life"]):
        return "thinker"
    else:
        return "blogger"


# ── CLI 命令 ──────────────────────────────────────────────────

def cmd_gen(args):
    card = generate_card_from_url(args.url, name=args.name, limit=args.limit)
    path = card.save()
    print(f"\n✅ CH 卡片已生成并保存:")
    print(f"   📁 {path}")
    print(f"\n   名字: {card.name}")
    print(f"   类型: {card.role_type}")
    print(f"   MBTI: {card.mbti}")
    print(f"   Big Five: O={card.big_five['O']:.2f} C={card.big_five['C']:.2f} "
          f"E={card.big_five['E']:.2f} A={card.big_five['A']:.2f} N={card.big_five['N']:.2f}")
    print(f"   记忆片段: {', '.join(card.memory_snippets[:3])}")
    print(f"\n💡 在其他机器运行 CH:")
    print(f"   1. 拷贝 cards/{path.name} 到对方 phase1/cards/ 目录")
    print(f"   2. from ch_card import CHCard; card = CHCard.load('{path.name}')")
    print(f"   3. 用 card.to_cyber_human_kwargs() 初始化 CyberHuman")


def cmd_list(args):
    cards = list(CARDS_DIR.glob("*.json"))
    if not cards:
        print("📭 暂无卡片，运行 `python3 ch_cli.py gen <URL>` 生成第一张")
        return
    print(f"\n📦 CH 卡片列表 ({len(cards)} 张)\n")
    print(f"   {'文件名':<40} {'名字':<15} {'MBTI':<6} {'角色':<12} 来源")
    print(f"   {'-'*95}")
    for p in sorted(cards):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            url_short = data.get("source_url", "")[:40]
            print(f"   {p.name:<40} {data.get('name',''):<15} {data.get('mbti',''):<6} "
                  f"{data.get('role_type',''):<12} {url_short}")
        except Exception as e:
            print(f"   {p.name:<40} [解析失败: {e}]")
    print(f"\n💡 查看详情: python3 ch_cli.py show <文件名>")


def cmd_show(args):
    path = CARDS_DIR / args.filename
    if not path.exists():
        path = Path(args.filename)
    if not path.exists():
        print(f"❌ 找不到卡片: {args.filename}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"\n📇 CH 卡片: {data.get('name', '未知')}")
    print(f"   文件: {path.name}")
    print(f"   来源: {data.get('source_url', 'N/A')}")
    print(f"   角色: {data.get('role_type', 'N/A')}")
    print(f"   MBTI: {data.get('mbti', 'N/A')}  |  Big Five: {data.get('big_five', {})}")
    print(f"\n📝 人物描述:")
    print(f"   {data.get('persona_description', 'N/A')}")
    print(f"\n🧠 记忆片段:")
    for m in data.get("memory_snippets", []):
        print(f"   • {m}")
    print(f"\n🏷️  情绪标签: {', '.join(data.get('emotion_tags', []))}")
    print(f"\n📝 完整 JSON:")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_load(args):
    """打印可导入的 Python dict，用于集成到其他代码"""
    path = CARDS_DIR / args.filename
    if not path.exists():
        path = Path(args.filename)
    if not path.exists():
        print(f"❌ 找不到卡片: {args.filename}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    print("# 在代码中导入 CH Card:")
    print("from ch_card import CHCard")
    print(f"card = CHCard.load('{path.name}')")
    print(f"# 或直接构造:")
    print(f"card_kwargs = {json.dumps(data, ensure_ascii=False, indent=2)}")
    print(f"\n# 初始化 CyberHuman:")
    print("from cyber_human import CyberHuman")
    print("ch = CyberHuman(**card.to_cyber_human_kwargs())")


# ── 入口 ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SereneX CH Card CLI — 生成可移植的 Cyber Human 卡片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # gen 命令
    p_gen = sub.add_parser("gen", help="从网页 URL 生成 CH 卡片")
    p_gen.add_argument("url", help="目标网页 URL（支持任意网页）")
    p_gen.add_argument("--name", "-n", help="指定 CH 名字（不指定则从标题推断）")
    p_gen.add_argument("--limit", "-l", type=int, default=20, help="分析内容条数（默认20）")

    # list 命令
    sub.add_parser("list", help="列出所有 CH 卡片")

    # show 命令
    p_show = sub.add_parser("show", help="查看 CH 卡片内容")
    p_show.add_argument("filename", help="卡片文件名（不含路径）")

    # load 命令
    p_load = sub.add_parser("load", help="打印卡片的 Python 导入代码")
    p_load.add_argument("filename", help="卡片文件名（不含路径）")

    args = parser.parse_args()

    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "show":
        cmd_show(args)
    elif args.cmd == "load":
        cmd_load(args)


if __name__ == "__main__":
    main()
