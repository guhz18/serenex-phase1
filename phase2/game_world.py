"""
SereneX Phase 2 — Game Sandbox
游戏世界：地点、时间、事件
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
import random


class Location(Enum):
    HOME = "home"           # 在家
    PARK = "park"           # 公园
    CAFE = "cafe"           # 咖啡馆
    OFFICE = "office"       # 办公室
    MALL = "mall"           # 商场
    LIBRARY = "library"     # 图书馆


@dataclass
class Place:
    name: str
    id: Location
    description: str
    capacity: int = 5       # 同时容纳人数
    activity_tags: List[str]  # 适合的活动类型
    mood_modifier: float = 0.0  # 在此地心情修正


PLACES: Dict[Location, Place] = {
    Location.HOME:     Place("家",     Location.HOME,     "舒适的小窝，休息恢复能量",   capacity=2, activity_tags=["rest", "chat_home"]),
    Location.PARK:      Place("公园",   Location.PARK,     "阳光下的草地，适合散步聊天", capacity=8, activity_tags=["walk", "chat_outdoor", "exercise"]),
    Location.CAFE:      Place("咖啡馆", Location.CAFE,     "氛围温馨，适合深度对话",     capacity=6, activity_tags=["chat_indoor", "work"]),
    Location.OFFICE:   Place("办公室", Location.OFFICE,   "工作场所，忙碌但充实",       capacity=10, activity_tags=["work", "meet"]),
    Location.MALL:     Place("商场",   Location.MALL,     "热闹繁华，吃喝玩乐齐全",     capacity=20, activity_tags=["shop", "eat", "chat_indoor"]),
    Location.LIBRARY:  Place("图书馆", Location.LIBRARY,  "安静的知识殿堂，适合独处",   capacity=15, activity_tags=["read", "work", "rest"]),
}


TIME_SLOTS = {
    0:  ("深夜", "凌晨了，万籁俱寂"),
    6:  ("清晨", "阳光初现，新的一天"),
    8:  ("上午", "精力充沛的上午时光"),
    12: ("中午", "午餐时间"),
    14: ("下午", "慵懒的下午"),
    18: ("傍晚", "夕阳西下"),
    20: ("晚间", "华灯初上的夜晚"),
    22: ("深夜", "夜深人静"),
}


class GameWorld:
    """
    游戏世界状态机
    - 管理时间（tick 为单位，每 tick = 1 小时游戏时间）
    - 管理地点与人物位置
    - 触发每日事件
    - 提供时间/地点查询接口
    """

    def __init__(self):
        self.time_hour: int = 8          # 初始时间：上午8点
        self.day: int = 1
        self.tick_count: int = 0
        # ch_id -> location
        self.ch_locations: Dict[str, Location] = {}
        # location -> [ch_id]
        self.place_occupants: Dict[Location, List[str]] = {loc: [] for loc in Location}
        # 今日事件
        self.today_events: List[str] = []
        self._generate_daily_events()

    # ── 时间 ───────────────────────────────────────

    def advance_tick(self):
        """推进1个tick（=1游戏小时）"""
        self.tick_count += 1
        self.time_hour += 1
        if self.time_hour >= 24:
            self.time_hour = 0
            self.day += 1
            self._new_day()
        # 每3个tick生成一次随机事件
        if self.tick_count % 3 == 0:
            self._maybe_spawn_event()

    def _new_day(self):
        """新的一天"""
        self._generate_daily_events()
        # 重置所有人到家的位置
        for ch_id in self.ch_locations:
            self.ch_locations[ch_id] = Location.HOME
        for loc in self.place_occupants:
            self.place_occupants[loc] = []

    def get_time_slot(self) -> str:
        ts = TIME_SLOTS.get(self.time_hour, TIME_SLOTS[22])
        return f"[Day{self.day} {ts[0]}]"

    def get_time_hint(self) -> str:
        ts = TIME_SLOTS.get(self.time_hour, TIME_SLOTS[22])
        return ts[1]

    # ── 位置 ───────────────────────────────────────

    def set_ch_location(self, ch_id: str, loc: Location) -> bool:
        """移动人物到指定地点"""
        old = self.ch_locations.get(ch_id)
        if old:
            if ch_id in self.place_occupants[old]:
                self.place_occupants[old].remove(ch_id)

        if len(self.place_occupants[loc]) >= PLACES[loc].capacity:
            return False  # 满了

        self.ch_locations[ch_id] = loc
        self.place_occupants[loc].append(ch_id)
        return True

    def get_ch_location(self, ch_id: str) -> Location:
        return self.ch_locations.get(ch_id, Location.HOME)

    def get_location_name(self, ch_id: str) -> str:
        loc = self.get_ch_location(ch_id)
        return PLACES[loc].name

    def get_same_place_chs(self, ch_id: str) -> List[str]:
        """返回同地点的其他CH"""
        loc = self.get_ch_location(ch_id)
        return [cid for cid in self.place_occupants[loc] if cid != ch_id]

    # ── 每日事件 ───────────────────────────────────

    def _generate_daily_events(self):
        pool = [
            "今天天气很好，适合出门！",
            "小雨淅淅沥沥，咖啡馆里人很多",
            "突然停电了！大家只能待在家里",
            "公园有露天音乐会！很多人去了",
            "商场打折季，人山人海",
            "图书馆有新书上架",
            "今天是社区志愿者日",
            "天气预报说晚上有流星雨",
        ]
        self.today_events = random.sample(pool, min(2, len(pool)))

    def _maybe_spawn_event(self):
        roll = random.random()
        if roll < 0.25:  # 25%概率
            triggers = [
                ("rain", "突然下起了雨，大家都往咖啡馆跑！"),
                ("sunny", "阳光突然特别明媚，公园里热闹起来！"),
                ("traffic", "交通管制通知，小明滞留在路上"),
                ("news", "新闻里播放了一条有趣的消息，引发了讨论"),
            ]
            kind, msg = random.choice(triggers)
            self.today_events.append(msg)
            return msg
        return None

    def get_events(self) -> List[str]:
        return self.today_events

    # ── 场景摘要 ───────────────────────────────────

    def scene_summary(self, ch_ids: List[str]) -> str:
        """生成当前世界场景摘要（用于LLM Prompt）"""
        lines = [f"【{self.get_time_slot()}】{self.get_time_hint()}"]
        if self.today_events:
            lines.append(f"今日事件：{' | '.join(self.today_events)}")
        lines.append("当前位置：")
        for cid in ch_ids:
            loc = self.get_ch_location(cid)
            lines.append(f"  - {cid}: 在{PLACES[loc].name}")
        return "\n".join(lines)
