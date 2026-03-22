"""
SereneX Phase 2 — 任务系统
每日任务 + 社交成就
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import random


class QuestType(Enum):
    DAILY = "daily"           # 每日任务
    SOCIAL = "social"         # 社交成就
    EXPLORE = "explore"       # 探索成就
    SPECIAL = "special"       # 特殊事件


@dataclass
class Quest:
    id: str
    title: str
    desc: str
    qtype: QuestType
    target_ch: str = ""
    target_ch2: str = ""       # 第二个目标CH
    condition: str = ""         # 条件描述
    reward: str = ""
    progress: int = 0
    required: int = 1
    completed: bool = False
    failed: bool = False

    def update(self, event: str, ch_id: str) -> bool:
        """
        更新进度，返回是否完成
        """
        if self.completed or self.failed:
            return False

        if ch_id and ch_id not in (self.target_ch, self.target_ch2) and self.target_ch:
            return False

        if self.condition in event or self.condition == "":
            self.progress += 1
            if self.progress >= self.required:
                self.completed = True
                return True
        return False


class QuestSystem:
    """
    任务系统：生成、管理、结算任务
    """

    def __init__(self):
        self.quests: List[Quest] = []
        self.completed_quests: List[Quest] = []
        self.total_reward_points: int = 0
        self.round_count: int = 0

    def new_day(self):
        """每天重置每日任务"""
        self.quests = [q for q in self.quests if q.qtype != QuestType.DAILY]
        self._generate_daily_quests()

    def set_round(self, r: int):
        self.round_count = r

    def _generate_daily_quests(self):
        templates: List[Quest] = [
            Quest(
                id="q_daily_chat_2",
                title="社交达人",
                desc="让任意两位CH进行1次聊天",
                qtype=QuestType.DAILY,
                condition="CHAT_WITH",
                required=1,
                reward="社交值+0.2",
            ),
            Quest(
                id="q_daily_group",
                title="三人聚会",
                desc="让3个CH在同一个地点碰面",
                qtype=QuestType.DAILY,
                condition="SAME_PLACE_3",
                required=1,
                reward="全员心情+0.15",
            ),
            Quest(
                id="q_daily_explore",
                title="探索者",
                desc="让任意CH去一个新地点",
                qtype=QuestType.DAILY,
                condition="EXPLORE_NEW",
                required=1,
                reward="能量+0.1",
            ),
            Quest(
                id="q_daily_deep",
                title="深度对话",
                desc="指定两位CH聊天3轮以上",
                qtype=QuestType.DAILY,
                condition="DEEP_CHAT",
                required=1,
                reward="关系+0.15",
            ),
        ]
        # 每天随机选2个
        chosen = random.sample(templates, min(2, len(templates)))
        for q in chosen:
            q.progress = 0
            q.completed = False
        self.quests.extend(chosen)

    def add_special_quest(self, title: str, desc: str, target_ch: str,
                          condition: str, reward: str):
        """玩家主动触发的特殊任务"""
        q = Quest(
            id=f"q_special_{random.randint(1000,9999)}",
            title=title, desc=desc, qtype=QuestType.SPECIAL,
            target_ch=target_ch, condition=condition,
            reward=reward, required=1,
        )
        self.quests.append(q)
        return q

    def trigger_event(self, event_type: str, ch_id: str = "", ch_id2: str = ""):
        """事件触发器，检测任务进度"""
        results = []
        for q in list(self.quests):
            if q.completed or q.failed:
                continue

            # 构造事件串
            event_str = f"{event_type}_{ch_id}"
            if event_type == "CHAT_WITH" and ch_id2:
                # 交换顺序以匹配
                if q.update(event_str, ch_id) or q.update(f"{event_type}_{ch_id2}", ch_id2):
                    if q.completed and q not in results:
                        results.append(q)
            else:
                if q.update(event_str, ch_id):
                    results.append(q)

            # 每日3轮对话
            if q.id == "q_daily_deep" and event_type == "CHAT_TURN":
                q.progress += 1
                if q.progress >= 3:
                    q.completed = True
                    results.append(q)

            # 三人同地点
            if q.id == "q_daily_group" and event_type == "SAME_PLACE":
                q.progress = 1
                q.completed = True
                results.append(q)

        return results

    def status(self) -> str:
        if not self.quests:
            return "  暂无任务"
        lines = []
        for q in self.quests:
            status = "✅" if q.completed else ("❌" if q.failed else "⬜")
            prog = f"[{q.progress}/{q.required}]" if not q.completed else ""
            lines.append(f"  {status} {q.title} {prog} — {q.desc} ({q.reward})")
        return "\n".join(lines)

    def completed_summary(self) -> str:
        if not self.completed_quests:
            return "尚无完成的任务"
        return "已完成：" + "、".join(q.title for q in self.completed_quests)
