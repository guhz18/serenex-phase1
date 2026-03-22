"""
SereneX Phase 2 — 需求系统（简化版，无RPG）
每个CH有3个核心需求：能量、心情、社交
"""

from enum import Enum
from typing import Dict, List
from dataclasses import dataclass, field
import random


class NeedLabel(Enum):
    ENERGY = "energy"       # 精力
    MOOD = "mood"           # 心情
    SOCIAL = "social"        # 社交值


@dataclass
class NeedState:
    """单个需求状态"""
    value: float = 0.6     # 0.0 ~ 1.0，1.0=完全满足
    decay_rate: float = 0.05  # 每tick自然消耗

    def is_critical(self) -> bool:
        return self.value < 0.25

    def is_full(self) -> bool:
        return self.value > 0.9

    def label(self) -> str:
        if self.value >= 0.8: return "😊满足"
        if self.value >= 0.5: return "😐一般"
        if self.value >= 0.25: return "😟较低"
        return "😫危急"


class NeedsSystem:
    """
    管理单个 CH 的需求状态
    需求会随时间自然消耗，通过活动补充/消耗
    """

    def __init__(self):
        self.needs: Dict[NeedLabel, NeedState] = {
            NeedLabel.ENERGY:  NeedState(value=0.8, decay_rate=0.06),
            NeedLabel.MOOD:    NeedState(value=0.7, decay_rate=0.04),
            NeedLabel.SOCIAL:  NeedState(value=0.5, decay_rate=0.05),
        }

    def tick(self):
        """每个tick消耗"""
        for need in self.needs.values():
            need.value = max(0.0, need.value - need.decay_rate)

    def apply_activity(self, activity: str):
        """
        根据活动类型调整需求
        activity: rest | work | chat | eat | exercise | explore | alone
        """
        mapping: Dict[str, Dict[NeedLabel, float]] = {
            "rest":     {NeedLabel.ENERGY: +0.35, NeedLabel.MOOD: +0.05, NeedLabel.SOCIAL: -0.02},
            "work":     {NeedLabel.ENERGY: -0.15, NeedLabel.MOOD: -0.05, NeedLabel.SOCIAL: +0.02},
            "chat":     {NeedLabel.ENERGY: -0.05, NeedLabel.MOOD: +0.10, NeedLabel.SOCIAL: +0.15},
            "eat":      {NeedLabel.ENERGY: +0.10, NeedLabel.MOOD: +0.05, NeedLabel.SOCIAL: +0.0},
            "exercise": {NeedLabel.ENERGY: -0.20, NeedLabel.MOOD: +0.08, NeedLabel.SOCIAL: +0.0},
            "explore":  {NeedLabel.ENERGY: -0.08, NeedLabel.MOOD: +0.05, NeedLabel.SOCIAL: +0.03},
            "alone":    {NeedLabel.ENERGY: -0.02, NeedLabel.MOOD: -0.05, NeedLabel.SOCIAL: -0.08},
        }
        deltas = mapping.get(activity, {})
        for need_label, delta in deltas.items():
            self.needs[need_label].value = max(0.0, min(1.0, self.needs[need_label].value + delta))

    def most_urgent(self) -> NeedLabel:
        """返回最紧急的需求"""
        return min(self.needs, key=lambda n: self.needs[n].value)

    def summary(self) -> str:
        parts = []
        for need in [NeedLabel.ENERGY, NeedLabel.MOOD, NeedLabel.SOCIAL]:
            st = self.needs[need]
            parts.append(f"{need.value}:{st.label()}")
        return " | ".join(parts)

    def is_critical_any(self) -> bool:
        return any(n.is_critical() for n in self.needs.values())

    def mood_score(self) -> float:
        return self.needs[NeedLabel.MOOD].value


@dataclass
class ActivityRecord:
    """活动记录"""
    activity: str
    location: str
    participants: List[str]
    tick: int
    outcome: str = "normal"  # normal | good | bad
