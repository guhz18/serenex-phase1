"""
SereneX Phase 1 — 人格模型 (MBTI + Big Five)
"""

from dataclasses import dataclass, field
from typing import Dict, List
import random


# ── MBTI 16型人格定义 ──────────────────────────────────────────
MBTI_PROFILES: Dict[str, Dict] = {
    # 四维倾向 → 对应行为权重
    "INTJ": {"e_i": 0.2, "s_n": 0.3, "t_f": 0.8, "j_p": 0.8,
             "description": "战略家，理性独立"},
    "INTP": {"e_i": 0.2, "s_n": 0.7, "t_f": 0.7, "j_p": 0.3,
             "description": "逻辑学家，深度思考者"},
    "ENTJ": {"e_i": 0.8, "s_n": 0.3, "t_f": 0.8, "j_p": 0.8,
             "description": "指挥官，领导型"},
    "ENTP": {"e_i": 0.8, "s_n": 0.8, "t_f": 0.4, "j_p": 0.6,
             "description": "辩论家，创意十足"},
    "INFJ": {"e_i": 0.2, "s_n": 0.7, "t_f": 0.2, "j_p": 0.6,
             "description": "提倡者，理想主义"},
    "INFP": {"e_i": 0.2, "s_n": 0.7, "t_f": 0.1, "j_p": 0.4,
             "description": "调停者，内心温暖"},
    "ENFJ": {"e_i": 0.8, "s_n": 0.6, "t_f": 0.2, "j_p": 0.7,
             "description": "主人公，激励型"},
    "ENFP": {"e_i": 0.8, "s_n": 0.8, "t_f": 0.2, "j_p": 0.5,
             "description": "竞选者，热情洋溢"},
    "ISTJ": {"e_i": 0.2, "s_n": 0.7, "t_f": 0.7, "j_p": 0.2,
             "description": "物流师，务实可靠"},
    "ISFJ": {"e_i": 0.2, "s_n": 0.7, "t_f": 0.2, "j_p": 0.3,
             "description": "守护者，细心温暖"},
    "ESTJ": {"e_i": 0.8, "s_n": 0.7, "t_f": 0.7, "j_p": 0.2,
             "description": "总经理，执行力强"},
    "ESFJ": {"e_i": 0.8, "s_n": 0.7, "t_f": 0.2, "j_p": 0.5,
             "description": "执政官，热情利他"},
    "ISTP": {"e_i": 0.2, "s_n": 0.4, "t_f": 0.7, "j_p": 0.4,
             "description": "鉴赏家，实用主义"},
    "ISFP": {"e_i": 0.2, "s_n": 0.4, "t_f": 0.2, "j_p": 0.5,
             "description": "探险家，艺术气息"},
    "ESTP": {"e_i": 0.8, "s_n": 0.4, "t_f": 0.6, "j_p": 0.6,
             "description": "企业家，行动派"},
    "ESFP": {"e_i": 0.8, "s_n": 0.5, "t_f": 0.3, "j_p": 0.6,
             "description": "表演者，活跃自在"},
}

# ── Big Five（五大人格）默认区间 ───────────────────────────────
@dataclass
class BigFive:
    openness: float = 0.5         # 开放性：好奇心/创造力
    conscientiousness: float = 0.5 # 尽责性：自律/责任感
    extraversion: float = 0.5      # 外向性：社交能量
    agreeableness: float = 0.5     # 宜人性：合作/信任
    neuroticism: float = 0.5      # 神经质：情绪波动

    def dict(self) -> Dict:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    def as_mbti_scores(self) -> Dict[str, float]:
        return {
            "e_i": self.extraversion,        # >0.5 外向
            "s_n": self.openness,            # >0.5 直觉
            "t_f": 1 - self.agreeableness,   # >0.5 思考
            "j_p": self.conscientiousness,   # >0.5 判断
        }


@dataclass
class PersonalityModel:
    """人格模型：MBTI + Big Five，影响 CH 的一切行为"""
    mbti_type: str = "ENFP"
    big_five: BigFive = field(default_factory=BigFive)

    # 内部状态
    _mbti_scores: Dict[str, float] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        # 从 MBTI 或 Big Five 推导一、二级分数
        if self.mbti_type in MBTI_PROFILES:
            raw = MBTI_PROFILES[self.mbti_type]
            self._mbti_scores = dict(raw)
        else:
            # fallback：从 Big Five 反推
            self._mbti_scores = self.big_five.as_mbti_scores()

    # ── 对外接口 ──────────────────────────────────────────────

    def chat_probability(self) -> float:
        """基于外向性计算主动发起聊天的基准概率"""
        extraversion = self._mbti_scores.get("e_i", 0.5)
        base = 0.20
        return base + extraversion * 0.30  # 0.20 ~ 0.50

    def accept_probability(self, applicant_id: str, relation_level: float) -> float:
        """
        基于宜人性计算接受聊天的概率
        relation_level: 对方和自己的亲密度 [0,1]
        """
        agree = self._mbti_scores.get("t_f", 0.5)  # t_f 高=理性=不太容易接受
        warmth = 1 - agree * 0.6
        return (0.3 + relation_level * 0.4) * warmth

    def relationship_delta(self, outcome: str) -> float:
        """基于宜人性和神经质调整关系变化幅度"""
        agree = self.big_five.agreeableness        # 高宜人=更容易喜欢
        neuro = self.big_five.neuroticism          # 高神经质=情绪波动大
        delta_map = {"positive": 0.08, "neutral": 0.02, "negative": -0.05}
        delta = delta_map.get(outcome, 0.0)
        sensitivity = 1.0 + neuro * 0.5           # 神经质高→情绪反应更强烈
        warmth = agree * 0.5 + 0.75               # 宜人高→正面放大，负面缩小
        if delta > 0:
            return delta * warmth * sensitivity
        else:
            return delta * (2.0 - warmth) * sensitivity

    def curiosity_level(self) -> float:
        """好奇心强度，影响是否主动探索新关系"""
        return self._mbti_scores.get("s_n", 0.5) * self.big_five.openness

    def empathy_score(self) -> float:
        """共情能力，影响对话深度"""
        return (self._mbti_scores.get("t_f", 0.5) * 0.3 +
                self.big_five.agreeableness * 0.7)

    def conversation_style(self) -> Dict:
        """返回影响对话风格的参数"""
        e_i = self._mbti_scores.get("e_i", 0.5)
        return {
            "initiates_topics": e_i > 0.5,
            "asks_follow_questions": self.big_five.openness > 0.4,
            "short_or_long": "long" if self.big_five.conscientiousness > 0.5 else "short",
            "emotional_or_rational": "rational" if self._mbti_scores.get("t_f", 0.5) > 0.5 else "emotional",
        }

    def summary(self) -> Dict:
        mbti_info = MBTI_PROFILES.get(self.mbti_type, {})
        return {
            "mbti": self.mbti_type,
            "mbti_desc": mbti_info.get("description", ""),
            "big_five": self.big_five.dict(),
            "chat_prob": round(self.chat_probability(), 3),
            "empathy": round(self.empathy_score(), 3),
            "style": self.conversation_style(),
        }


# ── 预设人物模板 ────────────────────────────────────────────────
PRESET_PERSONAS = {
    "xiaoming": ("ENFP", {
        "openness": 0.8, "conscientiousness": 0.4, "extraversion": 0.9,
        "agreeableness": 0.8, "neuroticism": 0.3,
    }),
    "xiaoyu": ("INTJ", {
        "openness": 0.7, "conscientiousness": 0.9, "extraversion": 0.2,
        "agreeableness": 0.5, "neuroticism": 0.2,
    }),
    "ahua": ("ISFJ", {
        "openness": 0.4, "conscientiousness": 0.7, "extraversion": 0.4,
        "agreeableness": 0.9, "neuroticism": 0.3,
    }),
    "analytical": ("INTP", {
        "openness": 0.9, "conscientiousness": 0.6, "extraversion": 0.1,
        "agreeableness": 0.4, "neuroticism": 0.4,
    }),
    "leader": ("ENTJ", {
        "openness": 0.6, "conscientiousness": 0.9, "extraversion": 0.9,
        "agreeableness": 0.4, "neuroticism": 0.3,
    }),
}


def create_personality(persona_key: str = None, mbti_type: str = None,
                       big_five: Dict = None) -> PersonalityModel:
    """工厂函数：从预设或自定义创建人格模型"""
    if persona_key and persona_key in PRESET_PERSONAS:
        mbti, bf_dict = PRESET_PERSONAS[persona_key]
        bf = BigFive(**bf_dict)
        return PersonalityModel(mbti_type=mbti, big_five=bf)

    if mbti_type and mbti_type in MBTI_PROFILES:
        bf = BigFive(**(big_five or {}))
        return PersonalityModel(mbti_type=mbti_type, big_five=bf)

    # 随机生成
    mbti = random.choice(list(MBTI_PROFILES.keys()))
    bf = BigFive(
        openness=random.uniform(0.3, 0.9),
        conscientiousness=random.uniform(0.3, 0.9),
        extraversion=random.uniform(0.2, 0.9),
        agreeableness=random.uniform(0.3, 0.9),
        neuroticism=random.uniform(0.1, 0.7),
    )
    return PersonalityModel(mbti_type=mbti, big_five=bf)
