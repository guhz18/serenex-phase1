"""
SereneX Phase 1 — 博主人格推断
根据爬取的内容，推断博主的性格、写作风格、兴趣领域
输出：MBTI类型 + Big Five向量 + persona描述 + 关系风格
"""

import re
from typing import List, Dict, Optional
from collections import Counter
from dataclasses import dataclass

from content_scraper import Post
from personality import PersonalityModel, MBTI_PROFILES, BigFive, create_personality


# ── 内容风格分析 ──────────────────────────────────────────

@dataclass
class WritingStyle:
    """写作风格特征"""
    avg_sentence_length: float   # 平均句子长度
    question_ratio: float        # 问句比例（好奇度）
    exclamation_ratio: float     # 感叹句比例（热情度）
    emoji_count_per_post: float   # 平均每条动态的表情数
    first_person_freq: float      # 第一人称使用频率（I/我）
    emotional_vocab_ratio: float   # 情绪词占比
    topic_diversity: float        # 话题多样性（词汇分散度）
    url_sharing_ratio: float      # 分享链接比例
    humor_score: float           # 幽默指标（0~1）
    formality: float             # 正式程度（0=随意口语，1=正式书面）


@dataclass
class ContentProfile:
    """内容画像"""
    writing_style: WritingStyle
    top_topics: List[tuple]      # 高频话题 [(word, count), ...]
    emotional_tone: str           # 主情绪基调
    engagement_pattern: str       # 互动风格（回复型/发布型/混合型）
    inferred_personality: PersonalityModel
    persona_description: str       # 适合放进 LLM prompt 的人物描述
    suggested_mbti: str
    suggested_big_five: Dict[str, float]


class PersonalityInferrer:
    """
    从内容推断人格特征
    分析维度：
    1. 写作风格（句子长度、问句、感叹词、emoji）
    2. 词汇偏好（情绪词、第一/第二人称、专业术语）
    3. 话题分布（技术/情感/生活/观点）
    4. 互动模式（转发/原创/回复）
    5. 时间规律（发布时间、频率）
    """

    # 情绪词库
    EMOTION_POSITIVE = {
        "开心", "快乐", "幸福", "美好", "棒", "赞", "厉害", "感动", "温暖",
        "哈哈", "哈哈哈", "超", "最", "爱", "喜欢", "期待", "兴奋", "完美",
        "happy", "joy", "love", "great", "best", "amazing", "wonderful",
        "太好了", "开心", "幸福", "nice", "good", "lol", "haha",
    }
    EMOTION_NEGATIVE = {
        "难过", "伤心", "痛苦", "累", "困", "烦", "怕", "焦虑", "迷茫",
        "sad", "bad", "tired", "upset", "worried", "anxious", "cry",
        "唉", "怎么", "为什么", "烦", "不会", "不行", "讨厌",
    }
    EMOTION_EXCITED = {
        "哇", "天哪", "太棒", "竟然", "没想到", "真的假的",
        "omg", "wow", "omg", "holy", "wtf", "omfg",
    }
    HUMOR_MARKERS = {
        "哈哈", "哈哈哈", "笑死", "救命", "笑喷", "哈哈哈哈哈",
        "lol", "lmao", "kek", "😂😂", "🤣", "😂",
    }
    CURIOUS_MARKERS = {
        "为什么", "怎么", "是不是", "有没有", "谁知道", "什么意思",
        "why", "how", "what", "is it", "does anyone",
        "?" * 3, "求助", "请教", "问一下", "有人知道吗",
    }
    FIRST_PERSON = {
        "我", "我们", "俺", "本人的", "我个人", "我认为", "我感觉",
        "i ", "i'm", "i've", "my ", "me ", "myself",
    }
    FORMAL_WORDS = {
        "因此", "所以", "然而", "但是", "综上所述", "根据", "研究表明",
        "therefore", "thus", "however", "according to", "research shows",
        "指出", "认为", "分析", "总结", "结论",
    }

    def __init__(self, posts: List[Post]):
        self.posts = [p for p in posts if len(p.content) > 10]
        self.total = len(self.posts)
        if self.total == 0:
            raise ValueError("没有有效内容可供分析")

    # ── 分析入口 ────────────────────────────────────────

    def analyze(self) -> ContentProfile:
        """完整分析，返回内容画像"""
        style = self._analyze_writing_style()
        top_topics = self._analyze_topics()
        emotional_tone = self._analyze_emotional_tone()
        engagement = self._analyze_engagement_pattern()
        mbti, bf = self._infer_mbti_and_big_five(style, emotional_tone, engagement)
        persona_desc = self._build_persona_description(style, top_topics, emotional_tone, engagement)

        profile = ContentProfile(
            writing_style=style,
            top_topics=top_topics,
            emotional_tone=emotional_tone,
            engagement_pattern=engagement,
            inferred_personality=create_personality(mbti_type=mbti, big_five=bf),
            persona_description=persona_desc,
            suggested_mbti=mbti,
            suggested_big_five=bf,
        )
        return profile

    # ── 写作风格分析 ───────────────────────────────────

    def _analyze_writing_style(self) -> WritingStyle:
        texts = [p.content for p in self.posts]

        # 平均句子长度
        all_sentences = []
        for t in texts:
            sents = re.split(r"[。.!?！？\n]", t)
            all_sentences.extend([s for s in sents if len(s.strip()) > 2])
        avg_len = sum(len(s) for s in all_sentences) / max(1, len(all_sentences))

        # 问句比例
        question_count = sum(1 for t in texts if "?" in t or "？" in t or "吗" in t or "怎么" in t or "为什么" in t)
        question_ratio = question_count / self.total

        # 感叹句比例
        exclaim_count = sum(1 for t in texts if "!" in t or "！" in t or "哇" in t or "啊" in t)
        exclamation_ratio = exclaim_count / self.total

        # Emoji 数量
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols
            "\U0001F680-\U0001F6FF"  # transport
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        total_emoji = sum(len(emoji_pattern.findall(t)) for t in texts)
        emoji_per_post = total_emoji / self.total

        # 第一人称频率
        first_person_count = sum(
            sum(1 for fp in self.FIRST_PERSON if fp.lower() in t.lower())
            for t in texts
        )
        first_person_freq = first_person_count / self.total

        # 情绪词占比
        emotion_words = self.EMOTION_POSITIVE | self.EMOTION_NEGATIVE | self.EMOTION_EXCITED
        emotion_count = sum(
            sum(1 for w in emotion_words if w.lower() in t.lower())
            for t in texts
        )
        total_words = sum(len(t) for t in texts)
        emotional_vocab_ratio = emotion_count / max(1, total_words)

        # 话题多样性（词汇分散度）
        all_words = " ".join(texts).lower()
        words = [w for w in re.split(r"[\s,.\n，。！？]", all_words) if len(w) >= 2]
        word_counts = Counter(words)
        unique_ratio = len(word_counts) / max(1, len(words))
        topic_diversity = unique_ratio

        # 链接分享比例
        url_count = sum(1 for t in texts if "http" in t.lower() or "b23.tv" in t.lower())
        url_sharing_ratio = url_count / self.total

        # 幽默指标
        humor_count = sum(sum(1 for h in self.HUMOR_MARKERS if h in t) for t in texts)
        humor_score = min(1.0, humor_count / self.total)

        # 正式程度
        formal_count = sum(sum(1 for fw in self.FORMAL_WORDS if fw.lower() in t.lower()) for t in texts)
        formality = min(1.0, formal_count / self.total * 5)

        return WritingStyle(
            avg_sentence_length=avg_len,
            question_ratio=question_ratio,
            exclamation_ratio=exclamation_ratio,
            emoji_count_per_post=emoji_per_post,
            first_person_freq=first_person_freq,
            emotional_vocab_ratio=emotional_vocab_ratio,
            topic_diversity=topic_diversity,
            url_sharing_ratio=url_sharing_ratio,
            humor_score=humor_score,
            formality=formality,
        )

    def _analyze_topics(self, top_n: int = 8) -> List[tuple]:
        """高频词汇（话题）提取"""
        # 停用词
        stop_words = {
            "的", "是", "了", "在", "和", "也", "有", "我", "你", "他",
            "她", "它", "这", "那", "就", "都", "而", "到", "为",
            "with", "the", "a", "an", "is", "are", "was", "were",
            "to", "of", "in", "for", "on", "and", "or", "but", "the",
            "not", "be", "have", "has", "had", "it", "this", "that",
            "https", "http", "com", "www", "b23", "t.cn", "weibo",
            "一个", "这个", "那个", "什么", "怎么", "为什么", "如果",
            "可以", "可能", "没有", "知道", "大家", "感觉", "觉得",
        }
        all_text = " ".join(p.content for p in self.posts).lower()
        words = [w for w in re.split(r"[\s,.\n，。！？、：；「」【】]", all_text) if 2 <= len(w) <= 6]
        filtered = [w for w in words if w not in stop_words]
        return Counter(filtered).most_common(top_n)

    def _analyze_emotional_tone(self) -> str:
        """情绪基调"""
        pos = sum(sum(1 for w in self.EMOTION_POSITIVE if w.lower() in p.content.lower()) for p in self.posts)
        neg = sum(sum(1 for w in self.EMOTION_NEGATIVE if w.lower() in p.content.lower()) for p in self.posts)
        exc = sum(sum(1 for w in self.EMOTION_EXCITED if w.lower() in p.content.lower()) for p in self.posts)
        total = max(1, pos + neg + exc)
        tones = {"positive": pos/total, "negative": neg/total, "excited": exc/total}
        return max(tones, key=tones.get)

    def _analyze_engagement_pattern(self) -> str:
        """互动模式"""
        has_url = sum(1 for p in self.posts if "http" in p.content.lower())
        url_ratio = has_url / self.total
        has_repost = sum(1 for p in self.posts if "转发" in p.content or "repost" in p.content.lower())
        repost_ratio = has_repost / self.total
        if url_ratio > 0.4:
            return "内容分享型"      # 高频转发分享，原创少
        elif repost_ratio > 0.3:
            return "互动讨论型"      # 热衷互动讨论
        else:
            return "原创表达型"      # 以原创为主

    # ── MBTI + Big Five 推断 ─────────────────────────────

    def _infer_mbti_and_big_five(self, style: WritingStyle,
                                  tone: str, engagement: str) -> tuple:
        """
        根据写作风格推断 MBTI 和 Big Five
        """
        # 外向性（聊天频率、emoji、感叹）
        ex_raw = (style.exclamation_ratio * 3 + style.emoji_count_per_post * 0.5 +
                   style.first_person_freq * 0.3 + style.url_sharing_ratio * 0.2)
        extraversion = max(0.1, min(0.95, ex_raw))

        # 开放性（话题多样性、问句、正式程度）
        open_raw = (style.topic_diversity * 0.5 + style.question_ratio * 2 +
                     style.formality * 0.3 + (1 - style.formality) * 0.2)
        openness = max(0.1, min(0.95, open_raw))

        # 宜人性（情绪词汇、正向比例）
        agree_raw = (style.emotional_vocab_ratio * 3 +
                      (0.5 if tone == "positive" else 0) +
                      style.humor_score * 0.3)
        agreeableness = max(0.1, min(0.95, agree_raw))

        # 尽责性（正式程度、句子长度）
        cons_raw = (style.formality * 0.5 + style.avg_sentence_length / 50 +
                     (1 - style.humor_score) * 0.2)
        conscientiousness = max(0.1, min(0.95, cons_raw))

        # 神经质（负向情绪占比）
        neg_count = sum(1 for p in self.posts if
                       any(w in p.content for w in self.EMOTION_NEGATIVE))
        neuroticism = max(0.05, min(0.85, neg_count / self.total * 3))

        bf = {
            "openness": round(openness, 3),
            "conscientiousness": round(conscientiousness, 3),
            "extraversion": round(extraversion, 3),
            "agreeableness": round(agreeableness, 3),
            "neuroticism": round(neuroticism, 3),
        }

        # 推断 MBTI
        e_i = "E" if extraversion > 0.5 else "I"
        s_n = "N" if openness > 0.5 else "S"
        t_f = "T" if (1 - agreeableness) > 0.5 else "F"
        j_p = "J" if conscientiousness > 0.5 else "P"
        mbti = e_i + s_n + t_f + j_p

        # 覆盖特殊信号
        if style.question_ratio > 0.3:
            s_n = "N"  # 高好奇 → 直觉
        if style.humor_score > 0.5:
            e_i = "E"  # 高幽默 → 外向
        if engagement == "内容分享型":
            e_i = "E"  # 高分享 → 外向

        mbti = e_i + s_n + t_f + j_p

        # 验证是否为有效MBTI
        if mbti not in MBTI_PROFILES:
            mbti = "ENFP"  # fallback

        return mbti, bf

    # ── 人物描述生成 ─────────────────────────────────────

    def _build_persona_description(self, style: WritingStyle,
                                    topics: List[tuple],
                                    tone: str,
                                    engagement_pattern: str = "") -> str:
        """生成 LLM 可用的人物描述"""
        topic_str = "、".join(w for w, _ in topics[:5]) if topics else "多种话题"

        tone_map = {
            "positive": "积极乐观，擅长发现美好事物",
            "negative": "偏向内省，对负面情绪有较多表达",
            "excited": "热情洋溢，容易激动和兴奋",
        }
        tone_desc = tone_map.get(tone, "")

        engagement_map = {
            "内容分享型": "喜欢分享有趣的内容和链接，与粉丝积极互动",
            "互动讨论型": "热衷参与讨论，关注评论区反馈",
            "原创表达型": "以原创内容为主，注重自我表达",
        }
        engage_desc = engagement_map.get(engagement_pattern, "")

        style_descs = []
        if style.emoji_count_per_post > 0.8:
            style_descs.append("表情丰富")
        if style.question_ratio > 0.2:
            style_descs.append("善于提问，好奇心强")
        if style.humor_score > 0.4:
            style_descs.append("幽默风趣")
        if style.formality > 0.5:
            style_descs.append("表达正式有条理")
        elif style.humor_score < 0.2:
            style_descs.append("语言简洁直接")
        style_str = "，".join(style_descs) if style_descs else "风格自然"

        return (
            f"一个关注{topic_str}的博主，"
            f"{tone_desc}，{engage_desc}，{style_str}。"
            f"常用{('较长' if style.avg_sentence_length > 25 else '简短')}句子写作，"
            f"每条动态约有{style.emoji_count_per_post:.1f}个表情符号。"
        )


# ── 一键从URL创建 CH 记忆 ─────────────────────────────────

def train_ch_from_url(platform: str, url_or_id: str, ch_name: str = None,
                       limit: int = 30) -> Dict:
    """
    给定平台和链接/ID，一键爬取内容并推断人格
    返回完整的 CH 训练数据
    """
    from content_scraper import create_scraper

    scraper = create_scraper(platform)

    # 如果是URL，提取ID
    if "://" in str(url_or_id):
        if platform == "bilibili":
            uid = scraper.uid_from_url(url_or_id) if hasattr(scraper, "uid_from_url") else url_or_id
        elif platform == "weibo":
            uid = scraper.uid_from_url(url_or_id) if hasattr(scraper, "uid_from_url") else url_or_id
        else:
            uid = url_or_id
    else:
        uid = str(url_or_id)

    print(f"🔍 开始爬取 {platform} 用户: {uid}")
    posts = scraper.scrape(uid, limit=limit)
    print(f"   爬取到 {len(posts)} 条内容")

    if not posts:
        return {"error": "未能获取内容，可能需要登录或链接无效"}

    # 过滤太短的内容
    valid_posts = [p for p in posts if len(p.content) > 20]
    print(f"   有效内容: {len(valid_posts)} 条")

    # 推断人格
    inferrer = PersonalityInferrer(valid_posts)
    profile = inferrer.analyze()

    # 输出结果
    result = {
        "platform": platform,
        "user_id": uid,
        "posts_analyzed": len(valid_posts),
        "top_topics": profile.top_topics,
        "emotional_tone": profile.emotional_tone,
        "engagement_pattern": profile.engagement_pattern,
        "mbti": profile.suggested_mbti,
        "big_five": profile.suggested_big_five,
        "persona_description": profile.persona_description,
        "writing_style": {
            "avg_sentence_length": round(profile.writing_style.avg_sentence_length, 1),
            "emoji_per_post": round(profile.writing_style.emoji_count_per_post, 2),
            "question_ratio": round(profile.writing_style.question_ratio, 2),
            "humor_score": round(profile.writing_style.humor_score, 2),
            "formality": round(profile.writing_style.formality, 2),
        },
        "sample_posts": [
            {"content": p.content[:100], "date": p.date_str}
            for p in valid_posts[:5]
        ],
    }

    return result


if __name__ == "__main__":
    print("PersonalityInferrer OK")
