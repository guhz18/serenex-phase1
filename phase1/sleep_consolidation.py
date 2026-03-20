"""
SereneX Phase 1 — 记忆固化（Sleep/Dream Consolidation）
模拟人类睡眠时的记忆整合机制
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from memory_system import MemorySystem
from personality import PersonalityModel


@dataclass
class DreamFragment:
    """梦的片段——被激活并被加工的记忆"""
    memory_id: str
    original_summary: str
    dream_narrative: str       # 做梦时生成的"梦境叙事"
    emotional_shift: float    # 情绪偏移（做梦后情绪变化）
    neural_strength_delta: float  # 神经权重变化量


@dataclass
class ConsolidationResult:
    """一次睡眠整合的结果"""
    ch_id: str
    duration_seconds: float
    memories_replayed: int
    memories_strengthened: int
    new_memory_summary: str
    dreams: List[DreamFragment]
    neural_change: float
    emotional_after: str  # 整合后主导情绪


class SleepConsolidation:
    """
    记忆固化系统——模拟人类睡眠时的记忆整合

    机制：
    1. REPLAY：对重要记忆按权重进行"神经回放"
    2. REHEARSAL：在回放中生成新的关联（类比做梦）
    3. INTEGRATION：将回放结果加权写入神经网络
    4. CONSOLIDATION：将短期记忆摘要化为长期记忆
    """

    # 每次睡眠最多处理的记忆数
    MAX_REPLAY = 10
    # 记忆被"强化"的阈值（权重低于此不参与）
    REPLAY_THRESHOLD = 0.1

    def __init__(self, personality: PersonalityModel):
        self.personality = personality
        self.total_sleep_sessions = 0

    def run_sleep(self, ch_id: str, mem_sys: MemorySystem,
                  current_emotion: str) -> ConsolidationResult:
        """
        执行一次完整的睡眠整合
        返回 ConsolidationResult
        """
        start = time.time()
        memories = mem_sys.recall_recent(limit=50)
        
        # 按重要性筛选
        important = [m for m in memories if m.importance >= self.REPLAY_THRESHOLD]
        important = sorted(important, key=lambda m: m.importance, reverse=True)
        to_replay = important[:self.MAX_REPLAY]

        dreams: List[DreamFragment] = []
        total_neural_delta = 0.0
        strengthened = 0

        for mem in to_replay:
            # 1. Replay：回忆这件事
            replay_result = self._replay_memory(mem, current_emotion)
            
            # 2. Rehearsal：做梦——生成梦境叙事
            dream = self._dream_fragment(mem, current_emotion)
            dreams.append(dream)

            # 3. Integration：强化记忆的神经权重
            delta = self._integrate_memory(mem, dream)
            total_neural_delta += delta
            strengthened += 1

        # 4. Consolidation：生成睡眠摘要
        summary = self._generate_sleep_summary(ch_id, to_replay, dreams)

        duration = time.time() - start
        self.total_sleep_sessions += 1

        return ConsolidationResult(
            ch_id=ch_id,
            duration_seconds=duration,
            memories_replayed=len(to_replay),
            memories_strengthened=strengthened,
            new_memory_summary=summary,
            dreams=dreams,
            neural_change=total_neural_delta,
            emotional_after=self._dominant_after(dreams, current_emotion),
        )

    def _replay_memory(self, mem, current_emotion: str) -> Dict:
        """
        神经回放：提取记忆内容，通过大脑激活模式模拟"回忆"
        返回回放元数据
        """
        # 记忆越重要，被激活的神经簇越多
        intensity = mem.importance
        neurons_activated = int(8 + intensity * 16)  # 8~24 个神经元

        return {
            "memory_id": mem.id,
            "content_snippet": mem.summary[:30],
            "neurons_activated": neurons_activated,
            "activation_pattern": f"pattern_{mem.id[:6]}",
        }

    def _dream_fragment(self, mem, current_emotion: str) -> DreamFragment:
        """
        做梦：从记忆片段生成梦境叙事
        梦境 = 原始记忆 + 随机元素 + 情绪偏移
        """
        import random

        # 随机选择梦境类型
        dream_templates = [
            f"梦中又回到了那个场景……{mem.summary[:15]}，但这次好像多了什么。",
            f"半梦半醒间，听到有人在说「{mem.summary[:20]}」……",
            f"梦里浮现出碎片化的画面，关于……{mem.summary[:15]}，很真实。",
            f"在梦里，这件事变得更重要了，{mem.summary[:20]}反复出现。",
            f"朦胧中……{mem.summary[:10]}，然后梦就散了。",
        ]

        # 情绪偏移：梦境通常放大情绪，尤其是负面记忆
        neuro = self.personality.big_five.neuroticism
        is_negative = any(
            label in (mem.emotion_tags or [])
            for label in ["sadness", "anger", "fear", "anxiety"]
        )

        if is_negative:
            shift = neuro * 0.15  # 神经质高→负面记忆被放大
        else:
            shift = -neuro * 0.05  # 神经质高→正面记忆轻微减弱

        return DreamFragment(
            memory_id=mem.id,
            original_summary=mem.summary,
            dream_narrative=random.choice(dream_templates),
            emotional_shift=shift,
            neural_strength_delta=mem.importance * 0.05 + abs(shift),
        )

    def _integrate_memory(self, mem, dream: DreamFragment) -> float:
        """
        整合：将做梦后的强化量更新到记忆重要性
        模拟：睡眠期间权重重新分配
        """
        # 重要性上升（被反复激活的记忆被强化）
        new_importance = min(1.0, mem.importance + dream.neural_strength_delta * 0.1)
        mem.importance = new_importance
        return dream.neural_strength_delta * 0.1

    def _generate_sleep_summary(self, ch_id: str,
                                 replayed: List,
                                 dreams: List[DreamFragment]) -> str:
        """生成睡眠记忆的摘要（类似人类醒来后对梦的模糊记忆）"""
        if not dreams:
            return f"{ch_id} 安静地睡了一觉，什么也没梦到。"

        positive_dreams = [d for d in dreams if d.emotional_shift > 0]
        negative_dreams = [d for d in dreams if d.emotional_shift < 0]

        if positive_dreams:
            best = max(positive_dreams, key=lambda d: d.neural_strength_delta)
            return f"做了{len(dreams)}个梦，印象最深的一个：{best.dream_narrative}（感到温暖）"
        elif negative_dreams:
            worst = max(negative_dreams, key=lambda d: abs(d.emotional_shift))
            return f"夜里有{len(dreams)}个片段闪过……醒来时记得{worst.dream_narrative}（有点沉重）"
        else:
            d = dreams[0]
            return f"朦胧中好像梦到了{d.dream_narrative}，细节已经模糊了。"

    def _dominant_after(self, dreams: List[DreamFragment],
                        current_emotion: str) -> str:
        if not dreams:
            return current_emotion
        avg_shift = sum(d.emotional_shift for d in dreams) / len(dreams)
        if avg_shift > 0.03:
            return "joy"
        elif avg_shift < -0.03:
            return "sadness"
        return current_emotion

    def should_sleep(self, rounds_since_last_sleep: int,
                     current_brain_activation: float) -> Tuple[bool, str]:
        """
        判断是否应该进入睡眠
        返回 (should_sleep, reason)
        """
        # 每 20 轮强制睡眠一次
        if rounds_since_last_sleep >= 20:
            return True, f"运行{rounds_since_last_sleep}轮，强制进入睡眠整合"

        # 大脑激活过高时（过度刺激），建议睡眠
        if current_brain_activation > 2.5:
            return True, f"大脑激活度过高({current_brain_activation:.2f})，需要休息整合"

        # 低激活时也睡眠（恢复性）
        if current_brain_activation < 0.05 and rounds_since_last_sleep > 8:
            return True, f"大脑进入休眠状态，进行记忆整理"

        return False, ""
