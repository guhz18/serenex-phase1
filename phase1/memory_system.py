"""
SereneX Phase 1 — 记忆系统
"""

import json
import uuid
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from emotion_tag import EmotionLabel


@dataclass
class EpisodicMemory:
    """情景记忆单元"""
    id: str
    timestamp: float
    content: str               # 原始文本
    summary: str               # 摘要
    participants: List[str]    # 参与的CH ID列表
    emotion_tags: List[Tuple[str, float]] = field(default_factory=list)  # (label, intensity)
    importance: float = 0.5     # 重要性 0~1
    linked_image_ids: List[str] = field(default_factory=list)
    
    def age(self) -> float:
        return time.time() - self.timestamp
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['emotion_tags'] = [{'label': t, 'intensity': i} for t, i in self.emotion_tags]
        return d


@dataclass
class ImageMemory:
    """图像记忆"""
    id: str
    filepath_or_url: str
    description: str
    emotion_tags: List[Tuple[str, float]] = field(default_factory=list)
    linked_memory_ids: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class MemorySystem:
    """
    CH 的记忆存储系统
    - 情景记忆：文本事件
    - 图像记忆：图片+描述
    - 情绪权重：与记忆关联的情绪
    """
    
    def __init__(self, ch_id: str, storage_dir: str = "./memory_store"):
        self.ch_id = ch_id
        self.storage_dir = storage_dir
        self.episodic: List[EpisodicMemory] = []
        self.images: List[ImageMemory] = []
        self._memory_counter = 0
        
        import os
        os.makedirs(f"{storage_dir}/{ch_id}", exist_ok=True)
    
    def store_dialogue(self, text: str, participants: List[str],
                       emotion_tags: List[Tuple[EmotionLabel, float]],
                       summary: str = "") -> str:
        """存储一段对话到情景记忆"""
        self._memory_counter += 1
        mem_id = f"mem_{self.ch_id}_{self._memory_counter:04d}"
        
        # 生成摘要
        if not summary:
            summary = text[:80] + "..." if len(text) > 80 else text
        
        mem = EpisodicMemory(
            id=mem_id,
            timestamp=time.time(),
            content=text,
            summary=summary,
            participants=participants,
            emotion_tags=[(t.value, i) for t, i in emotion_tags],
            importance=self._calc_importance(text, emotion_tags),
        )
        
        self.episodic.append(mem)
        self._persist_memory(mem)
        return mem_id
    
    def _calc_importance(self, text: str,
                         emotion_tags: List[Tuple[EmotionLabel, float]]) -> float:
        """计算记忆重要性"""
        base = 0.3
        # 字数越多越重要
        base += min(0.2, len(text) / 1000)
        # 强烈情绪提升重要性
        max_intensity = max((i for _, i in emotion_tags), default=0.0)
        base += max_intensity * 0.3
        return min(1.0, base)
    
    def _persist_memory(self, mem: EpisodicMemory):
        """持久化到磁盘"""
        import os
        path = f"{self.storage_dir}/{self.ch_id}/{mem.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mem.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_memories(self):
        """从磁盘加载记忆"""
        import os, glob
        pattern = f"{self.storage_dir}/{self.ch_id}/mem_*.json"
        for path in glob.glob(pattern):
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
                d['emotion_tags'] = [(t['label'], t['intensity']) for t in d['emotion_tags']]
                mem = EpisodicMemory(**d)
                self.episodic.append(mem)
        self._memory_counter = len(self.episodic)
    
    def recall_recent(self, limit: int = 10) -> List[EpisodicMemory]:
        """回忆最近N段记忆"""
        sorted_mem = sorted(self.episodic, key=lambda m: m.timestamp, reverse=True)
        return sorted_mem[:limit]
    
    def recall_by_emotion(self, emotion: EmotionLabel, limit: int = 5) -> List[EpisodicMemory]:
        """按情绪标签检索记忆"""
        return [
            m for m in self.episodic
            if any(label == emotion.value and i > 0.5 for label, i in m.emotion_tags)
        ][:limit]
    
    def recall_context(self, keyword: str, limit: int = 3) -> List[EpisodicMemory]:
        """按关键词检索记忆"""
        return [
            m for m in self.episodic
            if keyword.lower() in m.content.lower()
        ][-limit:]
    
    def memory_summary(self) -> str:
        recent = self.recall_recent(5)
        if not recent:
            return f"{self.ch_id} 的记忆库是空的。"
        lines = [f"共 {len(self.episodic)} 段记忆，最近的 {len(recent)} 段："]
        for m in recent:
            age = self._format_age(m.age())
            dom_emotion = max(m.emotion_tags, key=lambda x: x[1])[0] if m.emotion_tags else "neutral"
            lines.append(f"  [{age}] {m.summary[:40]} | 情绪:{dom_emotion} 重要度:{m.importance:.2f}")
        return "\n".join(lines)
    
    def _format_age(self, seconds: float) -> str:
        if seconds < 60: return f"{int(seconds)}s前"
        if seconds < 3600: return f"{int(seconds/60)}m前"
        if seconds < 86400: return f"{int(seconds/3600)}h前"
        return f"{int(seconds/86400)}d前"
