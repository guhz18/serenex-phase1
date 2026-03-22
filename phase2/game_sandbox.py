"""
SereneX Phase 2 — GameSandbox
继承 ChatSandbox，叠加游戏世界循环
"""

import sys, os, time, random, asyncio
from typing import Dict, List, Tuple, Optional

# 复用 Phase1 的核心组件
phase1_path = os.path.join(os.path.dirname(__file__), "..", "phase1")
sys.path.insert(0, os.path.abspath(phase1_path))

from chat_sandbox import ChatSandbox
from cyber_human import CyberHuman, ChatBehavior
from llm_interface import get_llm
from emotion_tag import infer_emotions
from personality import create_personality

from game_world import GameWorld, Location, PLACES
from needs_system import NeedsSystem, NeedLabel, ActivityRecord
from quest_system import QuestSystem


class GameSandbox:
    """
    游戏沙盒 — 在 ChatSandbox 基础上叠加：
    - 游戏世界（时间 + 地点）
    - 需求系统（能量/心情/社交）
    - 任务系统（每日任务/成就）
    - 活动系统（自主决定去哪儿、做什么）
    - 玩家介入（发消息/指定地点/制造事件）
    """

    def __init__(self, name: str = "SereneX-Game",
                 app_storage_dir: str = "./memory_store",
                 llm_provider: str = "deepseek"):
        # 复用聊天沙盒
        self.chat = ChatSandbox(name, app_storage_dir)
        self.name = name
        self.round = 0
        self.max_rounds = 50

        # 游戏世界
        self.world = GameWorld()

        # 需求系统 per CH
        self.needs: Dict[str, NeedsSystem] = {}

        # 任务系统
        self.quests = QuestSystem()
        self.quests.new_day()  # 初始化每日任务

        # 活动记录
        self.activity_log: List[ActivityRecord] = []

        # LLM
        self.llm = get_llm()

        # 已探索新地点记录
        self.explored_places: Dict[str, set] = {}  # ch_id -> {loc_ids}

        # 每轮行为缓存（避免重复调用LLM）
        self.pending_chats: Dict[Tuple[str, str], int] = {}  # (a,b)->rounds

        self.log: List[str] = []

    # ── 初始化 ───────────────────────────────────────

    def add_ch(self, ch: CyberHuman, personality=None):
        """添加CH，初始化需求系统"""
        self.chat.add_ch(ch, personality)
        self.needs[ch.id] = NeedsSystem()
        self.world.ch_locations[ch.id] = Location.HOME
        self.world.place_occupants[Location.HOME].append(ch.id)
        self.explored_places[ch.id] = {Location.HOME}

        # 初始化关系
        for other_id in self.chat.chs:
            if other_id != ch.id:
                p = random.uniform(0.20, 0.45)
                self.chat.relation_matrix[(ch.id, other_id)] = p
                self.chat.relation_matrix[(other_id, ch.id)] = p

        self.log.append(f"  + 新成员：{ch.name}（ID:{ch.id[:6]}）")

    # ── 主循环 tick ──────────────────────────────────

    def tick(self) -> List[str]:
        """
        执行一个游戏tick
        每个tick = 游戏内1小时
        """
        self.round += 1
        self.quests.set_round(self.round)
        events = []

        # 1. 推进世界时间
        self.world.advance_tick()

        # 2. 每个CH决定行为（基于人格 + 需求）
        events += self._decide_activities()

        # 3. 处理同地点CH之间的聊天
        events += self._run_place_chats()

        # 4. 处理跨地点关系更新
        self._decay_relations()

        # 5. 需求系统tick
        for nid, ns in self.needs.items():
            ns.tick()

        # 6. 检测任务进度
        events += self._check_quests()

        # 7. 写入仪表盘
        self._write_game_state()

        return events

    # ── 行为决策 ─────────────────────────────────────

    def _decide_activities(self) -> List[str]:
        events = []
        for ch in list(self.chat.chs.values()):
            ns = self.needs.get(ch.id, NeedsSystem())

            # 关键需求优先
            urgent = ns.most_urgent()
            personality = getattr(ch, "personality", None)
            p_factor = personality.chat_probability() if personality else 0.3

            # 根据时间 + 需求决定行为
            hour = self.world.time_hour
            loc = self.world.get_ch_location(ch.id)

            # 深夜强制回家
            if hour >= 23 or hour < 6:
                if loc != Location.HOME:
                    self._move_ch(ch.id, Location.HOME)
                    events.append(f"🌙 {ch.name} 回家休息")
                continue

            # 能量危急 → 回家
            if ns.needs[NeedLabel.ENERGY].is_critical():
                if loc != Location.HOME:
                    self._move_ch(ch.id, Location.HOME)
                self._do_activity(ch.id, "rest")
                events.append(f"😴 {ch.name} 能量不足，回家休息")
                continue

            # 心情危急 → 去咖啡馆/公园
            if ns.needs[NeedLabel.MOOD].is_critical():
                target = random.choice([Location.CAFE, Location.PARK])
                if self._move_ch(ch.id, target):
                    self._do_activity(ch.id, "chat")
                    events.append(f"😟 {ch.name} 心情低落，去{PLACES[target].name}散心")
                continue

            # 工作时间（8~18点）偶尔工作
            if 8 <= hour <= 18 and random.random() < 0.3 * p_factor:
                if loc != Location.OFFICE:
                    if self._move_ch(ch.id, Location.OFFICE):
                        events.append(f"💼 {ch.name} 去办公室工作")
                self._do_activity(ch.id, "work")
                continue

            # 下午茶时间（14~16点）去咖啡馆
            if 14 <= hour <= 16 and random.random() < 0.5:
                if self._move_ch(ch.id, Location.CAFE):
                    self._do_activity(ch.id, "chat")
                    events.append(f"☕ {ch.name} 去咖啡馆喝下午茶")
                continue

            # 傍晚（18~20点）去公园
            if 18 <= hour <= 20 and random.random() < 0.5:
                if self._move_ch(ch.id, Location.PARK):
                    self._do_activity(ch.id, "walk")
                    events.append(f"🌆 {ch.name} 去公园散步")
                continue

            # 随机探索新地点（每2天一次）
            if random.random() < 0.15 * p_factor:
                unvisited = [l for l in Location if l not in self.explored_places.get(ch.id, set())]
                if unvisited:
                    new_loc = random.choice(unvisited)
                    if self._move_ch(ch.id, new_loc):
                        self.explored_places[ch.id].add(new_loc)
                        self._do_activity(ch.id, "explore")
                        events.append(f"🧭 {ch.name} 探索了{PLACES[new_loc].name}")
                        self.quests.trigger_event("EXPLORE_NEW", ch_id=ch.id)
                        continue

            # 默认：随机移动
            if random.random() < 0.2 * p_factor:
                targets = [l for l in Location if l != loc]
                target = random.choice(targets)
                if self._move_ch(ch.id, target):
                    activity = random.choice(["chat", "explore", "alone"])
                    self._do_activity(ch.id, activity)
                    events.append(f"🚶 {ch.name} 前往{PLACES[target].name}")

        return events

    # ── 同地点聊天 ────────────────────────────────────

    def _run_place_chats(self) -> List[str]:
        events = []
        for loc in Location:
            occupants = [cid for cid in self.world.place_occupants[loc] if cid in self.chat.chs]
            if len(occupants) < 2:
                continue

            # 随机选一对聊天
            a, b = random.sample(occupants, 2)
            rel = self.chat.relation_matrix.get((a, b), 0.3)

            if rel < 0.15:
                continue  # 关系太差不聊天

            ch_a = self.chat.chs[a]
            ch_b = self.chat.chs[b]

            # 检查是否已经有活跃会话
            key = tuple(sorted([a, b]))
            rounds = self.pending_chats.get(key, 0)

            # 最多连续聊3轮
            if rounds >= 3:
                continue

            # 激活聊天
            self.pending_chats[key] = rounds + 1
            conversation = self._llm_chat(ch_a, ch_b)

            # 更新需求
            self._do_activity(a, "chat")
            self._do_activity(b, "chat")

            # 更新关系
            emotions_a = infer_emotions(conversation[0]["text"])
            emotions_b = infer_emotions(conversation[1]["text"])
            mood_a = sum(e[1] for e in emotions_a) / max(len(emotions_a), 1)
            mood_b = sum(e[1] for e in emotions_b) / max(len(emotions_b), 1)

            delta = 0.05 * rel
            if mood_a > 0.6: delta += 0.05
            if mood_b > 0.6: delta -= 0.03

            self.chat.relation_matrix[(a, b)] = min(1.0, rel + delta)
            self.chat.relation_matrix[(b, a)] = min(1.0, self.chat.relation_matrix.get((b,a), 0.3) + delta*0.8)

            # 记录
            self.activity_log.append(ActivityRecord(
                activity="chat", location=PLACES[loc].name,
                participants=[ch_a.name, ch_b.name],
                tick=self.round,
            ))

            short_a = conversation[0]["text"][:40]
            short_b = conversation[1]["text"][:40]
            events.append(
                f"💬 {ch_a.name} ↔ {ch_b.name}（{PLACES[loc].name}）\n"
                f"   A: {short_a}...\n"
                f"   B: {short_b}..."
            )

            # 任务触发
            completed = self.quests.trigger_event("CHAT_WITH", ch_id=a, ch_id2=b)
            for q in completed:
                events.append(f"  🎯 任务完成：{q.title}")

            # 深度对话任务
            if self.pending_chats.get(key, 0) >= 3:
                self.quests.trigger_event("DEEP_CHAT", ch_id=a)
                self.quests.trigger_event("DEEP_CHAT", ch_id=b)

        # 检测同地点3人
        for loc in Location:
            occ = [cid for cid in self.world.place_occupants[loc] if cid in self.chat.chs]
            if len(occ) >= 3:
                self.quests.trigger_event("SAME_PLACE", ch_id=occ[0])
                names = [self.chat.chs[c].name for c in occ[:3]]
                events.append(f"  🏠 三人聚会@{PLACES[loc].name}：{'、'.join(names)}")

        return events

    # ── LLM 真实对话 ─────────────────────────────────

    def _llm_chat(self, ch_a: CyberHuman, ch_b: CyberHuman) -> List[Dict]:
        """调用 DeepSeek 生成两人对话"""
        context = self.world.scene_summary(list(self.chat.chs.keys()))
        emotion_a = ch_a.emotion.dominant_tag().value
        emotion_b = ch_b.emotion.dominant_tag().value

        # A说
        mood_a_val = self.needs[ch_a.id].mood_score()
        mood_b_val = self.needs[ch_b.id].mood_score()
        prompt_a = (
            f"场景：{context}\n"
            f"你是{ch_a.name}（MBTI: {getattr(ch_a,'personality',None) and ch_a.personality.mbti_type or 'ENFP'}）。"
            f"你现在在{PLACES[self.world.get_ch_location(ch_a.id)].name}，"
            f"遇到{ch_b.name}，心情指数{mood_a_val:.1f}。\n"
            f"心情{emotion_a}。请用一句话自然地打招呼或开启对话（<30字，口语化）。"
        )
        reply_a = self.llm.generate_response(
            ch_id=ch_a.id, ch_name=ch_a.name,
            ch_persona=f"MBTI人格，人名{ch_a.name}",
            partner_name=ch_b.name,
            context=prompt_a,
            emotion_hint=emotion_a,
        ) or f"{ch_a.name}点了点头，向{ch_b.name}打了个招呼"

        # B回复
        prompt_b = (
            f"场景：{context}\n"
            f"你是{ch_b.name}（MBTI: {getattr(ch_b,'personality',None) and ch_b.personality.mbti_type or 'INTJ'}）。"
            f"你现在在{PLACES[self.world.get_ch_location(ch_b.id)].name}，"
            f"{ch_a.name}对你说：「{reply_a}」\n"
            f"你的心情指数{mood_b_val:.1f}，心情{emotion_b}。"
            f"请用一句话自然回复（<30字，口语化）。"
        )
        reply_b = self.llm.generate_response(
            ch_id=ch_b.id, ch_name=ch_b.name,
            ch_persona=f"MBTI人格，人名{ch_b.name}",
            partner_name=ch_a.name,
            context=prompt_b + f"对方说：「{reply_a}」",
            emotion_hint=emotion_b,
        ) or f"{ch_b.name}笑着回应了{ch_a.name}"

        return [
            {"speaker": ch_a.name, "text": reply_a, "emotion": emotion_a},
            {"speaker": ch_b.name, "text": reply_b, "emotion": emotion_b},
        ]

    # ── 关系衰减 ─────────────────────────────────────

    def _decay_relations(self):
        """长时间没互动，关系缓慢衰减"""
        for (a, b), prob in list(self.chat.relation_matrix.items()):
            if a > b:  # 只处理一次
                continue
            if self.pending_chats.get(tuple(sorted([a, b])), 0) == 0:
                # 没有聊天，关系衰减
                new_val = max(0.1, prob - 0.008)
                self.chat.relation_matrix[(a, b)] = new_val
                self.chat.relation_matrix[(b, a)] = max(0.1, self.chat.relation_matrix.get((b,a), 0.3) - 0.005)

    # ── 工具方法 ─────────────────────────────────────

    def _move_ch(self, ch_id: str, loc: Location) -> bool:
        old = self.world.ch_locations.get(ch_id, Location.HOME)
        if old == loc:
            return True
        if len(self.world.place_occupants[loc]) >= PLACES[loc].capacity:
            return False
        if ch_id in self.world.place_occupants[old]:
            self.world.place_occupants[old].remove(ch_id)
        self.world.place_occupants[loc].append(ch_id)
        self.world.ch_locations[ch_id] = loc
        return True

    def _do_activity(self, ch_id: str, activity: str):
        ns = self.needs.get(ch_id)
        if ns:
            ns.apply_activity(activity)

    # ── 任务检测 ─────────────────────────────────────

    def _check_quests(self) -> List[str]:
        events = []
        newly_done = [q for q in self.quests.quests if q.completed and q not in self.quests.completed_quests]
        for q in newly_done:
            self.quests.completed_quests.append(q)
            events.append(f"  🎉 任务完成：{q.title} → {q.reward}")
            # 发放奖励
            for ch_id in self.chat.chs:
                ns = self.needs.get(ch_id)
                if not ns:
                    continue
                if "心情" in q.reward:
                    ns.needs[NeedLabel.MOOD].value = min(1.0, ns.needs[NeedLabel.MOOD].value + 0.15)
                if "能量" in q.reward:
                    ns.needs[NeedLabel.ENERGY].value = min(1.0, ns.needs[NeedLabel.ENERGY].value + 0.1)
                if "社交" in q.reward:
                    ns.needs[NeedLabel.SOCIAL].value = min(1.0, ns.needs[NeedLabel.SOCIAL].value + 0.2)
                if "关系" in q.reward:
                    for other_id in self.chat.chs:
                        if other_id != ch_id:
                            cur = self.chat.relation_matrix.get((ch_id, other_id), 0.3)
                            self.chat.relation_matrix[(ch_id, other_id)] = min(1.0, cur + 0.15)

        # 新的一天重置
        if self.world.time_hour == 8 and self.round >= 1:
            self.quests.new_day()
            events.append(f"\n  📅 新的一天（Day {self.world.day}）— 每日任务已刷新")
            for q in self.quests.quests:
                if q.qtype.value == "daily":
                    events.append(f"    → {q.title}: {q.desc}")

        return events

    # ── 玩家介入 ─────────────────────────────────────

    def player_send(self, player_name: str, message: str,
                    target_ch: str = "") -> List[Dict]:
        """
        玩家发消息给CH（可指定或广播）
        返回：各CH的回复列表
        """
        responses = self.chat.player_send(player_name, message)
        # 触发任务
        for r in responses:
            ch_id = None
            for cid, ch in self.chat.chs.items():
                if ch.name == r["speaker"]:
                    ch_id = cid
                    break
            if ch_id:
                self.quests.trigger_event("PLAYER_MSG", ch_id=ch_id)
                self._do_activity(ch_id, "chat")
        return responses

    def player_move(self, ch_name: str, location: str) -> str:
        """玩家指定某人去某地"""
        target_loc = None
        for loc in Location:
            if loc.value == location or PLACES[loc].name in location:
                target_loc = loc
                break
        if not target_loc:
            return f"未知地点: {location}，可用：{', '.join(l.value for l in Location)}"

        ch_id = None
        for cid, ch in self.chat.chs.items():
            if ch.name == ch_name:
                ch_id = cid
                break
        if not ch_id:
            return f"未找到角色：{ch_name}"

        if self._move_ch(ch_id, target_loc):
            self._do_activity(ch_id, random.choice(["explore", "chat"]))
            return f"✅ {ch_name} 已前往 {PLACES[target_loc].name}"
        else:
            return f"⚠️ {PLACES[target_loc].name} 已满，无法前往"

    def player_trigger_event(self, event_type: str, desc: str) -> str:
        """玩家触发特殊事件"""
        msg = f"📢 {desc}"
        self.world.today_events.append(msg)
        self.chat.log.append(f"  [玩家事件] {desc}")
        # 所有CH感知
        for ch in self.chat.chs.values():
            ch.perceive_event(f"player_event:{event_type}", intensity=0.8)
            ns = self.needs.get(ch.id)
            if ns and ns.needs[NeedLabel.MOOD].is_critical():
                ns.needs[NeedLabel.MOOD].value += 0.1
        return msg

    def player_assign_activity(self, ch_name: str, activity: str) -> str:
        """玩家指定某人做某活动"""
        ch_id = None
        for cid, ch in self.chat.chs.items():
            if ch.name == ch_name:
                ch_id = cid
                break
        if not ch_id:
            return f"未找到角色：{ch_name}"

        valid = ["rest", "work", "chat", "eat", "exercise", "explore", "alone"]
        if activity not in valid:
            return f"未知活动：{activity}，可用：{', '.join(valid)}"

        self._do_activity(ch_id, activity)
        return f"✅ {ch_name} 开始了「{activity}」"

    # ── 状态输出 ─────────────────────────────────────

    def status(self) -> str:
        lines = [
            f"━━━ {self.name} ━━━",
            f"Round {self.round}/{self.max_rounds} | {self.world.get_time_slot()} | Day {self.world.day}",
            f"事件：{' '.join(self.world.today_events) if self.world.today_events else '（无）'}",
            "",
            "【角色状态】",
        ]
        for ch in self.chat.chs.values():
            ns = self.needs.get(ch.id)
            loc = self.world.get_ch_location(ch.id)
            mood_str = ns.summary() if ns else "?"
            lines.append(
                f"  {ch.name} ({ch.personality.mbti_type if ch.personality else '?'}) "
                f"@ {PLACES[loc].name} | {mood_str} | {ch.emotion.dominant_tag().value}"
            )

        lines += ["", "【关系矩阵】"]
        for (ida, idb), prob in sorted(self.chat.relation_matrix.items()):
            if ida < idb:
                na = self.chat.chs[ida].name if ida in self.chat.chs else ida[:6]
                nb = self.chat.chs[idb].name if idb in self.chat.chs else idb[:6]
                lines.append(f"  {na} ↔ {nb}: {prob:.2f}")

        lines += ["", "【任务】", self.quests.status()]
        return "\n".join(lines)

    def _write_game_state(self):
        """写游戏状态 JSON（供 Web 仪表盘）"""
        import json, os
        os.makedirs("/tmp", exist_ok=True)
        chs_data = []
        for ch in self.chat.chs.values():
            ns = self.needs.get(ch.id)
            loc = self.world.get_ch_location(ch.id)
            chs_data.append({
                "id": ch.id,
                "name": ch.name,
                "mbti": ch.personality.mbti_type if ch.personality else "?",
                "location": PLACES[loc].name,
                "location_id": loc.value,
                "emotion": ch.emotion.dominant_tag().value,
                "needs": {n.value: ns.needs[n].value for n in NeedLabel} if ns else {},
                "relations": {tid: prob for (ida, tid), prob in self.chat.relation_matrix.items() if ida == ch.id},
            })

        quests_data = [{
            "id": q.id, "title": q.title, "desc": q.desc,
            "type": q.qtype.value, "progress": q.progress,
            "required": q.required, "completed": q.completed,
            "reward": q.reward,
        } for q in self.quests.quests]

        state = {
            "live": True,
            "round": self.round,
            "day": self.world.day,
            "time": f"{self.world.get_time_slot()}",
            "events": self.world.today_events,
            "chs": chs_data,
            "quests": quests_data,
            "timestamp": time.time(),
        }
        with open("/tmp/serenex_game.json", "w") as f:
            json.dump(state, f, ensure_ascii=False)
