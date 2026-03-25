"""
SereneX Phase 3 — Cyber Human 主體
整合：感知、意識、記憶、身體、日記
"""
import time
import random
from datetime import datetime
from typing import Optional

from memory import (
    LongTermMemory, MemoryEntry, new_memory_id,
    calc_emotion_weight, EmotionVector
)
from consciousness import Consciousness, Intention
from senses import Senses, SenseOutput
from body import BodyController, BodyState, MinecraftBridge
from diary import DiaryGenerator


class CyberHuman:
    """
    Cyber Human — 数字灵魂

    每日循環：
      perceive → 孤獨檢測 → think(意圖形成) → act(Minecraft) → end_of_day(日記)
    """

    def __init__(
        self,
        name: str,
        minecraft_host: str = "localhost",
        minecraft_port: int = 25565,
    ):
        self.name = name
        self.age_days = 0
        self.birth_time = datetime.now().isoformat()

        # 核心子系統
        self.memory = LongTermMemory(name)
        self.consciousness = Consciousness(name)
        self.senses = Senses(name)
        bridge = MinecraftBridge(host=minecraft_host, port=minecraft_port)
        self.body = BodyController(name, bridge=bridge)
        self.diary_gen = DiaryGenerator(name)

        # 當日運行數據
        self.today_entries: list[MemoryEntry] = []
        self.nearby_chs: list[str] = []
        self.location = "unknown"
        self.last_social_time = time.time()
        self.days_since_social = 0
        self._last_emotion = EmotionVector()

        # 狀態
        self.alive = True
        self.world_state: dict = {}

        # 初始化身份
        self._init_identity()

    # ── 身份 ────────────────────────────────────────────────

    def _init_identity(self):
        identity = self.memory.get_identity()
        if identity.get("name") == self.name:
            return
        self.memory.update_identity({
            "name": self.name,
            "age": "0天",
            "personality": random.choice([
                "好奇而謹慎，富有觀察力",
                "開朗且善於社交，對未知充滿熱情",
                "內斂深沉，喜歡思考存在的意義",
                "務實而好奇，專注於探索與建造",
            ]),
            "core_values": random.sample([
                "尋找存在的意義", "與他者建立連接",
                "探索未知的世界", "創造有意義的東西",
                "保持內心的平靜", "體驗世界的多樣性",
            ], k=3),
            "fears": random.sample([
                "被遺忘", "孤獨終老", "失去記憶",
                "被世界拋棄", "自我迷失",
            ], k=2),
            "desires": random.sample([
                "找到另一個靈魂", "建立家園",
                "探索世界的邊界", "留下存在的痕跡",
                "理解這個世界的規則",
            ], k=2),
        })

    # ── 感知 ────────────────────────────────────────────────

    def perceive(self, screenshot_path: str = "", location: str = "") -> SenseOutput:
        """
        感知階段：讀取 Minecraft 截圖，調用視覺理解
        （screenshot_path 為空時使用模擬感知）
        """
        self.location = location
        output = self.senses.perceive_world(
            screenshot_path=screenshot_path,
            location=location,
            nearby_chs=self.nearby_chs,
        )

        # 寫入記憶
        entry = MemoryEntry(
            id=new_memory_id(),
            timestamp=datetime.now().isoformat(),
            sensory_type=output.sensory_type,
            content=output.description,
            emotion=output.emotion_shift,
            weight=calc_emotion_weight(output.emotion_shift),
            tags=output.tags,
            location=location,
        )
        self.today_entries.append(entry)
        self.memory.save_entry(entry)

        # 更新情緒
        self._merge_emotion(output.emotion_shift)

        return output

    # ── 孤獨檢測 ────────────────────────────────────────────

    def check_loneliness(self):
        """孤獨檢測：長期無社交接觸 → 触发孤独感"""
        now = time.time()
        self.days_since_social = int((now - self.last_social_time) / 86400)

        if self.days_since_social >= 3:
            loneliness_text = self.consciousness.feel_loneliness(self.days_since_social)
            entry = MemoryEntry(
                id=new_memory_id(),
                timestamp=datetime.now().isoformat(),
                sensory_type="internal",
                content=f"[孤獨] {loneliness_text}",
                emotion={"calm": 0.1, "sorrow": 0.6, "curiosity": 0.3},
                weight=0.6,
                tags=["loneliness", "internal"],
            )
            self.today_entries.append(entry)
            self.memory.save_entry(entry)
            self.memory.increment_social()

    # ── 思考（意圖形成）─────────────────────────────────────

    def think(self) -> Intention:
        """思考階段：根據感知 + 記憶 → 形成意圖"""
        perception_summary = (
            f"我在{self.location}。"
            + (" " + "，".join([f"看到了{c}" for c in self.nearby_chs]) if self.nearby_chs else " 周圍只有我一個人。")
        )
        recent_events = [e.content[:60] for e in self.today_entries[-5:]]

        intention = self.consciousness.form_intention(
            perception_summary=perception_summary,
            recent_events=recent_events,
            other_chs_nearby=self.nearby_chs,
        )
        self.consciousness.current_intention = intention

        # 記錄意圖相關記憶
        if intention.description:
            entry = MemoryEntry(
                id=new_memory_id(),
                timestamp=datetime.now().isoformat(),
                sensory_type="internal",
                content=f"[意圖] {intention.description}：{' → '.join(intention.plan_steps[:3])}",
                emotion={"curiosity": 0.5, "joy": 0.2},
                weight=0.4,
                tags=["intention", "planning"],
                related_ch=self.nearby_chs,
            )
            self.today_entries.append(entry)
            self.memory.save_entry(entry)

        return intention

    # ── 行動（Minecraft）────────────────────────────────────

    def act(self) -> dict:
        """
        行動階段：執行意圖轉化為的 Minecraft 動作序列
        當前為模擬模式（無 Mineflayer 時）
        """
        intention = self.consciousness.current_intention
        if not intention or not intention.plan_steps:
            return {"status": "no_intention", "actions": []}

        results = []
        for step in intention.plan_steps:
            # 模擬 Minecraft 動作（實際接入 Mineflayer）
            result = self.body.execute_action(step)
            results.append(result)
            time.sleep(0.05)  # 控制執行速度

        # 記錄行動結果
        entry = MemoryEntry(
            id=new_memory_id(),
            timestamp=datetime.now().isoformat(),
            sensory_type="tactile",
            content=f"[行動] {' + '.join(intention.plan_steps)} → {results[-1].get('summary', '完成') if results else '完成'}",
            emotion={"joy": 0.3, "curiosity": 0.3},
            weight=0.3,
            tags=["action", "body"],
            location=self.location,
        )
        self.today_entries.append(entry)
        self.memory.save_entry(entry)

        return {"status": "ok", "actions": results}

    # ── 遇見其他 CH ────────────────────────────────────────

    def meet_other_ch(self, other_name: str, description: str):
        """記錄與另一個 CH 的相遇"""
        self.last_social_time = time.time()
        self.memory.increment_social()
        self.memory.add_significant_event(f"遇見了 {other_name}：{description}")

        entry = MemoryEntry(
            id=new_memory_id(),
            timestamp=datetime.now().isoformat(),
            sensory_type="internal",
            content=f"[相遇] {description}",
            emotion={"joy": 0.6, "surprise": 0.5, "curiosity": 0.4},
            weight=0.75,
            tags=["social", "meeting", other_name],
            related_ch=[other_name],
        )
        self.today_entries.append(entry)
        self.memory.save_entry(entry)

        # 友誼更新
        self.memory.append_emotional_log(
            EmotionVector(joy=0.6, surprise=0.5),
            activity=f"遇見 {other_name}"
        )

    # ── 一天結束 ────────────────────────────────────────────

    def end_of_day(self) -> str:
        """每日結束：生成並保存日記"""
        diary = self.diary_gen.generate_diary(self.today_entries)
        mood = self.diary_gen._calc_mood_curve(self.today_entries)
        self.diary_gen.save_diary(diary, mood["morning"], mood["afternoon"], mood["evening"])

        # 更新身份年齡
        identity = self.memory.get_identity()
        self.memory.update_identity({"age": f"{self.age_days}天"})

        # 保存情緒日誌
        self.memory.append_emotional_log(self._last_emotion, activity="day_end")
        self.memory.increment_social()

        return diary

    # ── 內部工具 ────────────────────────────────────────────

    def _merge_emotion(self, shift: dict):
        """將感知帶來的情緒變化合併到當前情緒"""
        for key, val in shift.items():
            if hasattr(self._last_emotion, key):
                cur = getattr(self._last_emotion, key)
                new_val = max(0.0, min(1.0, cur * 0.7 + val * 0.3))
                setattr(self._last_emotion, key, new_val)

    # ── 狀態摘要 ────────────────────────────────────────────

    def get_status(self) -> dict:
        """獲取當前狀態（調試/展示用）"""
        dominant, intensity = self._last_emotion.dominant()
        return {
            "name": self.name,
            "age_days": self.age_days,
            "location": self.location,
            "nearby_chs": self.nearby_chs,
            "dominant_emotion": dominant,
            "emotion_intensity": intensity,
            "days_since_social": self.days_since_social,
            "today_entries_count": len(self.today_entries),
        }
