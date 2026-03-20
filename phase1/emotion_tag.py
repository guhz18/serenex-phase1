"""
Emotion Label — 情绪标签枚举
"""

from enum import Enum


class EmotionLabel(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    LOVE = "love"
    ANXIETY = "anxiety"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


# 从对话文本推断情绪
EMOTION_KEYWORDS = {
    EmotionLabel.JOY: ["哈哈", "太棒了", "开心", "真好", "喜欢", "赞", "厉害", "哈哈", "happy", "joy", ":)"],
    EmotionLabel.SADNESS: ["难过", "伤心", "沮丧", "遗憾", "可惜", "sad", "忧郁", "失落", "唉"],
    EmotionLabel.ANGER: ["生气", "愤怒", "讨厌", "真烦", "无语", "怒", "annoyed", "angry"],
    EmotionLabel.FEAR: ["害怕", "担心", "紧张", "怕", "不敢", "慌", "fear", "scared"],
    EmotionLabel.SURPRISE: ["惊讶", "震惊", "没想到", "真的假的", "哇", "wow", "OMG", "居然"],
    EmotionLabel.DISGUST: ["恶心", "讨厌", "无语", "反感", "disgusting", "厌烦"],
    EmotionLabel.LOVE: ["爱你", "喜欢", "想念", "在乎", "温暖", "love", "care", " cherish"],
    EmotionLabel.ANXIETY: ["焦虑", "不安", "压力大", "怎么办", "焦虑", "worried", "anxious"],
    EmotionLabel.ANTICIPATION: ["期待", "希望", "想", "要", "快要", "期待", "hope", "excited"],
}


def infer_emotions(text: str) -> list:
    """从文本推断情绪标签和强度"""
    text_lower = text.lower()
    results = []
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            # 归一化：关键词命中数转强度 (0.3 ~ 0.9)
            intensity = min(0.9, 0.3 + 0.15 * score)
            results.append((emotion, intensity))
    if not results:
        results.append((EmotionLabel.NEUTRAL, 0.5))
    return results
