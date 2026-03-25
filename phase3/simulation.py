"""
SereneX Phase 3 — 文明演化模拟引擎
管理多个 CH 的运行、交互、文明日志、事件编年
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from agent import CyberHuman


CIV_DIR = Path(__file__).parent / "memory" / "civilization"
CIV_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CivilizationEvent:
    """文明事件"""
    id: str
    day: int
    timestamp: str
    type: str       # birth | death | meeting | discovery | conflict | cooperation | construction | milestone
    participants: list[str]
    description: str
    emotion_avg: dict
    impact: float   # 0.0~1.0 对文明发展的影响
    milestone: str = ""  # 里程碑类型（如果是里程碑事件）


@dataclass
class PopulationRecord:
    """人口记录"""
    day: int
    population: int
    ch_names: list[str]
    new_deaths: int = 0
    new_births: int = 0


class CivilizationLogger:
    """
    文明日志：记录所有重大事件，生成文明编年史
    """

    def __init__(self):
        self.events_file = CIV_DIR / "events.json"
        self.population_file = CIV_DIR / "population.json"
        self.relationships_file = CIV_DIR / "relationships.json"
        self._load()

    def _load(self):
        try:
            if self.events_file.exists():
                with open(self.events_file, encoding="utf-8") as f:
                    self.events = json.load(f)
            else:
                self.events = []

            if self.population_file.exists():
                with open(self.population_file, encoding="utf-8") as f:
                    self.population_history = json.load(f)
            else:
                self.population_history = []

            if self.relationships_file.exists():
                raw = open(self.relationships_file, encoding="utf-8").read()
                if raw.strip() == "{" or not raw.strip():
                    self.relationships = {}
                else:
                    parsed = json.loads(raw)
                    self.relationships = {tuple(k.split("___")): v for k, v in parsed.items()}
            else:
                self.relationships = {}
        except (json.JSONDecodeError, OSError):
            # 文件损坏时重置
            self.events = []
            self.population_history = []
            self.relationships = {}

    def _save(self):
        """原子写入：先写临时文件再 rename，防止文件损坏"""
        def atomic_write(path, data):
            tmp = str(path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)

        atomic_write(self.events_file, self.events)
        atomic_write(self.population_file, self.population_history)
        serializable_rel = {f"{k[0]}___{k[1]}": v for k, v in self.relationships.items()}
        atomic_write(self.relationships_file, serializable_rel)

    def log_event(self, ch_name: str, description: str, emotion: dict, weight: float,
                  event_type: str = "activity", participants: list[str] = None):
        """记录一个事件"""
        event = CivilizationEvent(
            id=f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            day=SimulationEngine.get_current_day(),
            timestamp=datetime.now().isoformat(),
            type=event_type,
            participants=participants or [ch_name],
            description=description,
            emotion_avg=emotion,
            impact=weight
        )
        self.events.append({
            "id": event.id,
            "day": event.day,
            "type": event.type,
            "participants": event.participants,
            "description": event.description,
            "emotion_avg": event.emotion_avg,
            "impact": event.impact
        })
        self._save()

    def log_milestone(self, milestone_type: str, description: str, participants: list[str], emotion: dict):
        """记录里程碑"""
        event = {
            "id": f"milestone_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "day": SimulationEngine.get_current_day(),
            "timestamp": datetime.now().isoformat(),
            "type": "milestone",
            "milestone_type": milestone_type,
            "participants": participants,
            "description": description,
            "emotion_avg": emotion,
            "impact": 1.0
        }
        self.events.append(event)
        self._save()
        return description

    def update_population(self, ch_names: list[str]):
        """更新人口记录"""
        record = PopulationRecord(
            day=SimulationEngine.get_current_day(),
            population=len(ch_names),
            ch_names=ch_names
        )
        self.population_history.append({
            "day": record.day,
            "population": record.population,
            "ch_names": record.ch_names
        })
        self._save()

    def update_relationship(self, ch1: str, ch2: str, delta: float):
        """更新两个 CH 之间的关系"""
        key = tuple(sorted([ch1, ch2]))
        current = self.relationships.get(key, 0.0)
        new_val = max(-1.0, min(1.0, current + delta))
        self.relationships[key] = new_val
        self._save()

    def get_phase(self) -> str:
        """根据人口判断当前文明阶段"""
        pop = len(self.population_history[-1]["ch_names"]) if self.population_history else 2
        if pop <= 2:
            return "🏕️ 原始个体（亚当与伊娃）"
        elif pop <= 5:
            return "🏠 小聚落"
        elif pop <= 15:
            return "🏘️ 部落"
        elif pop <= 50:
            return "🏛️ 城邦"
        elif pop <= 200:
            return "🌍 国家"
        else:
            return "🏺 文明"

    def generate_chronicle(self) -> str:
        """生成文明编年史"""
        if not self.events:
            return "文明的史书还是一片空白..."

        milestones = [e for e in self.events if e.get("type") == "milestone"]
        major = [e for e in self.events if e.get("impact", 0) >= 0.7]

        chronicle = f"""【文明编年史 — {self.get_phase()}】

"""
        # 按阶段分组
        phases = {
            "原始个体": [e for e in milestones if e.get("milestone_type") == "birth"],
            "聚落形成": [e for e in milestones if e.get("milestone_type") == "settlement"],
            "部落时代": [e for e in milestones if e.get("milestone_type") == "tribe"],
            "城邦崛起": [e for e in milestones if e.get("milestone_type") == "city"],
            "文明曙光": [e for e in milestones if e.get("milestone_type") == "civilization"],
        }

        for phase, events in phases.items():
            if events:
                chronicle += f"\n■ {phase}\n"
                for e in events:
                    chronicle += f"  Day {e['day']}: {e['description']}\n"

        if major:
            chronicle += "\n■ 重大事件\n"
            for e in major[-10:]:
                chronicle += f"  Day {e['day']}: {e['description'][:60]}\n"

        return chronicle


class SimulationEngine:
    """
    模拟引擎：驱动 CH 在 Minecraft 世界中逐日演化
    """

    _current_day = 0

    def __init__(self):
        self.chs: dict[str, CyberHuman] = {}
        self.day = 0
        self.civ_logger = CivilizationLogger()
        self.running = False
        self.speed = 1.0  # 模拟速度（一天=几秒）
        self._reached_milestones: set[int] = {0}  # 已达成的里程碑人口阈值

    @staticmethod
    def get_current_day() -> int:
        return SimulationEngine._current_day

    def add_ch(self, ch: CyberHuman):
        """添加一个 CH 到世界"""
        self.chs[ch.name] = ch
        self.civ_logger.update_population(list(self.chs.keys()))
        self.civ_logger.log_milestone(
            "birth", f"{ch.name} 诞生于这个世界",
            [ch.name], {"joy": 0.9, "curiosity": 0.8, "surprise": 0.5}
        )
        print(f"🌱 {ch.name} 诞生！")

    def detect_encounters(self) -> list[tuple[str, str]]:
        """检测 CH 之间的相遇（这里用距离模拟）"""
        encounters = []
        names = list(self.chs.keys())
        for i, name1 in enumerate(names):
            for name2 in names[i+1:]:
                # 实际距离待 Minecraft 位置系统接入
                # 目前模拟：随机决定是否相遇
                import random
                if random.random() < 0.3:
                    encounters.append((name1, name2))
        return encounters

    def simulate_day(self) -> dict:
        """
        模拟一天：每个 CH 执行感知→思考→行动循环
        """
        SimulationEngine._current_day += 1
        self.day = SimulationEngine._current_day

        day_report = {
            "day": self.day,
            "ch_reports": {},
            "encounters": [],
            "milestones": []
        }

        print(f"\n{'='*50}")
        print(f"☀️  Day {self.day} 开始")
        print(f"{'='*50}")

        # 检测相遇
        encounters = self.detect_encounters()
        for name1, name2 in encounters:
            desc = f"{name1} 和 {name2} 在世界中相遇"
            self.chs[name1].meet_other_ch(name2, desc)
            self.chs[name2].meet_other_ch(name1, desc)
            self.civ_logger.log_event(name1, desc, {"joy": 0.4, "curiosity": 0.5}, 0.6, "meeting", [name1, name2])
            day_report["encounters"].append(desc)

        # CH 逐个行动
        for name, ch in self.chs.items():
            print(f"\n--- {name} ---")

            # 感知阶段
            ch.nearby_chs = [n for n in self.chs.keys() if n != name]
            perception = ch.perceive(screenshot_path="", location=f"世界中心")
            print(f"  感知：{perception.description[:60]}")

            # 孤独检测
            ch.check_loneliness()

            # 思考阶段（意图形成）
            intention = ch.think()
            print(f"  意图：{intention.description}")
            if intention.plan_steps:
                print(f"  计划：{' → '.join(intention.plan_steps[:3])}")

            # 行动阶段（暂时跳过 Minecraft 执行，待接入 Mineflayer）
            # act_result = ch.act()

            # 每天结束：生成日记
            diary = ch.end_of_day()
            print(f"  日记：{diary[:80]}...")

            ch.age_days += 1
            day_report["ch_reports"][name] = {
                "intention": intention.description,
                "entries_count": len(ch.today_entries),
                "diary_preview": diary[:100]
            }

            # 清空当天记录（已保存到文件）
            ch.today_entries = []

        # 文明里程碑检测
        milestones = self._check_milestones()
        day_report["milestones"] = milestones
        for m in milestones:
            print(f"\n🎉 {m}")

        # 更新人口记录
        self.civ_logger.update_population(list(self.chs.keys()))

        print(f"\n🌙 Day {self.day} 结束 | 当前人口：{len(self.chs)}")
        phase = self.civ_logger.get_phase()
        print(f"   文明阶段：{phase}")

        return day_report

    def _check_milestones(self) -> list[str]:
        """检测文明里程碑"""
        new_milestones = []
        pop = len(self.chs)

        milestones = {
            2: ("birth", "第二个灵魂诞生！", "settlement"),
            3: ("settlement", "第一个小聚落形成", "settlement"),
            5: ("tribe", "部落在合作中形成", "tribe"),
            10: ("village", "繁荣的村庄出现", "village"),
            25: ("city", "城市雏形诞生", "city"),
            50: ("nation", "国家的概念出现", "nation"),
            100: ("civilization", "文明璀璨绽放", "civilization"),
        }

        for threshold, (mtype, desc, phase) in milestones.items():
            if pop >= threshold and threshold not in self._reached_milestones:
                self._reached_milestones.add(threshold)
                new_milestones.append(
                    self.civ_logger.log_milestone(phase, desc, list(self.chs.keys()), {"joy": 0.9})
                )

        return new_milestones

    def spawn_new_ch(self, name: str) -> CyberHuman:
        """生成新的 CH"""
        new_ch = CyberHuman(name)
        self.add_ch(new_ch)
        return new_ch

    def get_world_summary(self) -> str:
        """获取世界状态摘要"""
        return (
            f"【世界状态 — Day {self.day}】\n"
            f"人口：{len(self.chs)}\n"
            f"阶段：{self.civ_logger.get_phase()}\n"
            f"CH列表：{', '.join(self.chs.keys())}\n"
        )


def run_simulation(num_days: int = 30, auto_spawn: bool = True):
    """
    运行模拟

    Args:
        num_days: 运行多少天
        auto_spawn: 是否在合适时机自动生成新CH
    """
    engine = SimulationEngine()

    # 初始 CH：亚当 & 伊娃
    adam = CyberHuman("亚当")
    eve = CyberHuman("伊娃")

    # 初始关系
    engine.add_ch(adam)
    engine.add_ch(eve)
    engine.civ_logger.update_relationship("亚当", "伊娃", 0.5)

    # 特殊事件：第一天相遇
    adam.meet_other_ch("伊娃", "第一次见到伊娃，她/他的存在让我感到一种难以名状的连接")
    eve.meet_other_ch("亚当", "第一次见到亚当，心中涌起一股好奇与温暖")

    reports = []
    for day in range(1, num_days + 1):
        report = engine.simulate_day()
        reports.append(report)

        # 自动生成新 CH
        if auto_spawn and day % 30 == 0 and len(engine.chs) < 100:
            new_name = f"CH_{len(engine.chs)+1:03d}"
            engine.spawn_new_ch(new_name)

        time.sleep(0.1)  # 控制速度

    # 生成文明编年史
    chronicle = engine.civ_logger.generate_chronicle()

    print("\n" + "="*60)
    print("🏛️  文明编年史")
    print("="*60)
    print(chronicle)

    return engine, reports


if __name__ == "__main__":
    print("🌍 SereneX Phase 3 — 文明演化模拟器")
    print("从亚当和伊娃开始... \n")
    engine, reports = run_simulation(num_days=30)
