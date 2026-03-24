"""
SereneX Phase 3 — 长期记忆系统
每条记忆都有情绪权重，权重决定记忆的重要程度和衰减速度
"""
import json
import os
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

MEMORY_DIR = Path(__file__).parent.parent / "memory"


class EmotionType(Enum):
    JOY = "joy"
    SORROW = "sorrow"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    CURIOSITY = "curiosity"
    CALM = "calm"


@dataclass
class EmotionVector:
    joy: float = 0.0       # 0.0~1.0
    sorrow: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    curiosity: float = 0.0
    calm: float = 0.5

    def dominant(self) -> tuple[str, float]:
        """返回最强情绪及强度"""
        max_key = max(self.__dict__, key=lambda k: getattr(self, k))
        max_val = getattr(self, max_key)
        return max_key, max_val

    def to_dict(self):
        return asdict(self)


@dataclass
class MemoryEntry:
    """单条记忆"""
    id: str                           # mem_YYYYMMDD_HHMMSS
    timestamp: str                     # ISO格式时间戳
    sensory_type: str                  # visual | auditory | tactile | internal
    content: str                       # 记忆内容描述
    emotion: dict                      # 情绪向量
    weight: float                      # 权重 0.0~1.0
    tags: list[str] = field(default_factory=list)
    summary: str = ""                  # 简短摘要
    location: str = ""                 # 世界坐标 "x,y,z"
    related_ch: list[str] = field(default_factory=list)  # 涉及的CH名字
    reflection: str = ""                # CH对这条记忆的反思
    reinforced: int = 1                # 被唤醒次数
    source: str = ""                    # 日记/事件/对话

    def calc_weight(self, days_since: float = 0.0) -> float:
        """动态权重：情绪强度 × 时间衰减 × 强化次数"""
        intensity = max(self.emotion.values())
        # 基础分：情绪强的拉高，中性有基础分0.2
        base = intensity * 0.7 + (1 - intensity) * 0.2
        # 时间衰减（30天半衰期）
        recency = pow(0.5, days_since / 30)
        # 强化系数（被唤醒越多越难遗忘）
        reinforced = 1 + (self.reinforced - 1) * 0.05
        return min(base * recency * reinforced, 1.0)


@dataclass
class DailyMemory:
    """每日记忆文件"""
    ch_name: str
    date: str          # YYYY-MM-DD
    entries: list[dict]
    mood_morning: float = 0.5
    mood_afternoon: float = 0.5
    mood_evening: float = 0.5
    social_encounters: int = 0
    significant_events: list[str] = field(default_factory=list)
    diary_text: str = ""   # LLM生成的日记

    def save(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = MEMORY_DIR / self.ch_name.lower()
        base_dir.mkdir(parents=True, exist_ok=True)
        filepath = base_dir / f"{self.date}.json"
        data = asdict(self)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath

    @classmethod
    def load(cls, ch_name: str, date_str: str, base_dir: Optional[Path] = None) -> "DailyMemory":
        if base_dir is None:
            base_dir = MEMORY_DIR / ch_name.lower()
        filepath = base_dir / f"{date_str}.json"
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                return cls(**json.load(f))
        return cls(ch_name=ch_name, date=date_str, entries=[])


class LongTermMemory:
    """长期记忆管理器"""

    def __init__(self, ch_name: str):
        self.ch_name = ch_name
        self.base_dir = MEMORY_DIR / ch_name.lower()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.today_file = self._today_file()

    def _today_file(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.base_dir / f"{today}.json"

    def save_entry(self, entry: MemoryEntry) -> str:
        """保存单条记忆到今日文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        dm = DailyMemory.load(self.ch_name, today, self.base_dir)
        entry_dict = asdict(entry)
        dm.entries.append(entry_dict)
        filepath = dm.save(self.base_dir)
        return str(filepath)

    def add_diary(self, diary_text: str, mood_morning=0.5, mood_afternoon=0.5, mood_evening=0.5):
        """写入每日日记"""
        today = datetime.now().strftime("%Y-%m-%d")
        dm = DailyMemory.load(self.ch_name, today, self.base_dir)
        dm.diary_text = diary_text
        dm.mood_morning = mood_morning
        dm.mood_afternoon = mood_afternoon
        dm.mood_evening = mood_evening
        dm.save(self.base_dir)

    def add_significant_event(self, event: str):
        """记录重大事件"""
        today = datetime.now().strftime("%Y-%m-%d")
        dm = DailyMemory.load(self.ch_name, today, self.base_dir)
        if event not in dm.significant_events:
            dm.significant_events.append(event)
        dm.save(self.base_dir)

    def increment_social(self):
        today = datetime.now().strftime("%Y-%m-%d")
        dm = DailyMemory.load(self.ch_name, today, self.base_dir)
        dm.social_encounters += 1
        dm.save(self.base_dir)

    def retrieve_recent(self, days: int = 7, min_weight: float = 0.0) -> list[MemoryEntry]:
        """检索最近N天的记忆"""
        results = []
        now = datetime.now()
        for i in range(days):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            dm = DailyMemory.load(self.ch_name, d, self.base_dir)
            for entry_dict in dm.entries:
                entry = MemoryEntry(**entry_dict)
                if entry.weight >= min_weight:
                    results.append(entry)
        return results

    def retrieve_by_tags(self, tags: list[str], days: int = 30) -> list[MemoryEntry]:
        """按标签检索记忆"""
        results = []
        now = datetime.now()
        for i in range(days):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            dm = DailyMemory.load(self.ch_name, d, self.base_dir)
            for entry_dict in dm.entries:
                entry = MemoryEntry(**entry_dict)
                if any(tag in entry.tags for tag in tags):
                    results.append(entry)
        return sorted(results, key=lambda e: e.weight, reverse=True)

    def get_identity(self) -> dict:
        """获取CH的自我认知"""
        identity_file = self.base_dir / "identity.json"
        if identity_file.exists():
            with open(identity_file, encoding="utf-8") as f:
                return json.load(f)
        return {
            "name": self.ch_name,
            "age": "unknown",
            "personality": "curious, observant",
            "core_values": [],
            "fears": [],
            "desires": []
        }

    def update_identity(self, updates: dict):
        identity_file = self.base_dir / "identity.json"
        identity = self.get_identity()
        identity.update(updates)
        with open(identity_file, "w", encoding="utf-8") as f:
            json.dump(identity, f, ensure_ascii=False, indent=2)

    def get_emotional_log(self) -> list[dict]:
        """读取情绪曲线历史"""
        log_file = self.base_dir / "emotional_log.json"
        if log_file.exists():
            with open(log_file, encoding="utf-8") as f:
                return json.load(f)
        return []

    def append_emotional_log(self, emotion_vector: EmotionVector, activity: str):
        log_file = self.base_dir / "emotional_log.json"
        log = self.get_emotional_log()
        log.append({
            "timestamp": datetime.now().isoformat(),
            "activity": activity,
            **emotion_vector.to_dict()
        })
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

    def get_all_diaries(self, limit: int = 30) -> list[dict]:
        """获取所有日记（用于上下文）"""
        diaries = []
        for f in sorted(self.base_dir.glob("*.json"), reverse=True)[:limit]:
            with open(f, encoding="utf-8") as fp:
                dm = DailyMemory(**json.load(fp))
                if dm.diary_text:
                    diaries.append({"date": dm.date, "text": dm.diary_text})
        return diaries


def new_memory_id() -> str:
    return f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def calc_emotion_weight(emotion: dict) -> float:
    """独立工具函数：计算情绪权重"""
    intensity = max(emotion.values())
    base = intensity * 0.7 + (1 - intensity) * 0.2
    return min(base, 1.0)


from datetime import timedelta
