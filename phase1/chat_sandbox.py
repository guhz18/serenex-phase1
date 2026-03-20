"""
SereneX Phase 1 — Chat Sandbox
管理多个 CyberHuman 之间的聊天逻辑
"""

import asyncio
import time
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from cyber_human import CyberHuman, ChatBehavior, EmotionLabel
from llm_interface import get_llm
from emotion_tag import infer_emotions
from personality import PersonalityModel, create_personality
from sleep_consolidation import SleepConsolidation

DASHBOARD_STATE_FILE = "/tmp/serenex_dashboard.json"


@dataclass
class ChatSession:
    """一次聊天会话"""
    id: str
    ch_a: str   # CH A 的 id
    ch_b: str   # CH B 的 id
    start_time: float
    turns: List[Tuple[str, str]] = field(default_factory=list)  # (speaker, text)
    satisfaction: List[float] = field(default_factory=list)  # 每轮满意度


class ChatSandbox:
    """
    聊天沙盒 — 管理 N 个 CH 之间的聊天
    
    规则：
    1. 每轮每个 CH 根据关系矩阵决定行为
    2. 收到申请按概率决定接受/拒绝
    3. 聊天结束后更新关系
    4. CH 记忆会记录聊天内容
    """
    
    def __init__(self, name: str, app_storage_dir: str = "./memory_store"):
        self.name = name
        self.chs: Dict[str, CyberHuman] = {}
        # 关系矩阵：(sender_id, receiver_id) -> probability [0,1]
        self.relation_matrix: Dict[Tuple[str, str], float] = {}
        
        # 活跃聊天 session: (ch_a_id, ch_b_id) -> ChatSession
        self.active_sessions: Dict[Tuple[str, str], ChatSession] = {}
        
        self.app_storage_dir = app_storage_dir
        self.round_count = 0
        self.log: List[str] = []
        
        from memory_system import MemorySystem
        self.memory_systems: Dict[str, type] = {}
        
        # 睡眠整合
        self.sleep_tracker: Dict[str, int] = {}  # ch_id -> rounds since last sleep
        self.sleep_history: List[dict] = []
    
    def add_ch(self, ch: CyberHuman, personality: PersonalityModel = None):
        """添加 CH，带人格模型（可选）"""
        self.chs[ch.id] = ch
        self.sleep_tracker[ch.id] = 0
        
        # 人格：默认从预设生成
        ch.personality = personality or create_personality()
        # 初始化关系：互相设为0.3起步
        for other_id in self.chs:
            if other_id != ch.id:
                if (ch.id, other_id) not in self.relation_matrix:
                    self.relation_matrix[(ch.id, other_id)] = 0.3
                if (other_id, ch.id) not in self.relation_matrix:
                    self.relation_matrix[(other_id, ch.id)] = 0.3
                # 互相加入关系列表
                if other_id not in ch.relations:
                    ch.relations[other_id] = 0.3
                if ch.id not in self.chs[other_id].relations:
                    self.chs[other_id].relations[ch.id] = 0.3
        
        from memory_system import MemorySystem
        self.memory_systems[ch.id] = MemorySystem(ch.id, self.app_storage_dir)
        
        self.log.append(f"  + 加入了沙盒: {ch.name} ({ch.id})")
    
    def tick(self) -> List[str]:
        """
        执行一个模拟 tick
        返回本轮发生的事件列表
        """
        self.round_count += 1
        events = []

        # === 阶段1：IDLE/WAITING 的 CH 决定是否发起聊天 ===
        for ch in self.chs.values():
            if ch.state not in (ChatBehavior.IDLE, ChatBehavior.WAITING):
                continue
            if ch.pending_applications:
                # 有待处理申请，按概率决定接受
                applicant = ch.pending_applications[0]
                prob = self.relation_matrix.get((ch.id, applicant), 0.3)
                if random.random() < prob:
                    ch.state = ChatBehavior.IN_CHAT
                    ch.chat_target = applicant
                    self._start_session(ch.id, applicant)
                else:
                    ch.pending_applications.pop(0)
                    if not ch.pending_applications:
                        ch.state = ChatBehavior.IDLE
                continue

            # 无申请则主动发起（人格影响概率）
            if ch.state == ChatBehavior.IDLE:
                personality = getattr(ch, "personality", None)
                base_prob = (personality.chat_probability() 
                             if personality else 0.30)
                targets = sorted(ch.relations.items(), key=lambda x: x[1], reverse=True)
                for target_id, rel_prob in targets:
                    if target_id in self.chs and self.chs[target_id].is_available():
                        combined_prob = base_prob * rel_prob * 2  # 关系 × 人格
                        if random.random() < combined_prob:
                            ch.state = ChatBehavior.INITIATING
                            ch.chat_target = target_id
                            self.chs[target_id].receive_application(ch.id)
                            break

        # === 阶段2：INITIATING 的 CH 检测目标是否已把自己加进申请 ===
        for ch in self.chs.values():
            if ch.state == ChatBehavior.INITIATING and ch.chat_target:
                target = self.chs.get(ch.chat_target)
                if target and ch.id in target.pending_applications:
                    # 目标已经收到申请，互相确认，进入聊天
                    self._start_session(ch.id, target.id)
                else:
                    # 目标还没处理，下轮继续
                    pass

        # === 阶段3：运行所有活跃会话 ===
        events += self._run_active_sessions()

        # === 阶段4：睡眠整合检查 ===
        events += self._run_sleep_consolidation()

        # === 阶段5：写入仪表盘状态 ===
        self.write_dashboard_state()

        return events
    
    def _start_session(self, initiator_id: str, receiver_id: str):
        session_id = f"s_{initiator_id[:6]}_{receiver_id[:6]}_{self.round_count}"
        session = ChatSession(
            id=session_id,
            ch_a=initiator_id,
            ch_b=receiver_id,
            start_time=time.time(),
        )
        
        key = (initiator_id, receiver_id)
        rev_key = (receiver_id, initiator_id)
        self.active_sessions[key] = session
        self.active_sessions[rev_key] = session  # 双向索引
        
        self.chs[initiator_id].state = ChatBehavior.IN_CHAT
        self.chs[initiator_id].chat_target = receiver_id
        self.chs[receiver_id].state = ChatBehavior.IN_CHAT
        self.chs[receiver_id].chat_target = initiator_id
        
        self.log.append(f"[Tick {self.round_count}] 会话开始: {self.chs[initiator_id].name} ↔ {self.chs[receiver_id].name}")
    
    def _run_active_sessions(self) -> List[str]:
        events = []
        to_end = []
        
        for (ida, idb), session in list(self.active_sessions.items()):
            if (ida, idb) not in [(session.ch_a, session.ch_b)]:  # 只处理一次（主键）
                continue
            
            ch_a = self.chs.get(session.ch_a)
            ch_b = self.chs.get(session.ch_b)
            if not ch_a or not ch_b:
                to_end.append((ida, idb))
                continue
            
            # 生成对话轮次
            turn_texts = self._generate_turn(ch_a, ch_b, session)
            
            for speaker, text in turn_texts:
                speaker_ch = ch_a if speaker == ch_a.name else ch_b
                listener_ch = ch_b if speaker == ch_a.name else ch_a
                
                session.turns.append((speaker, text))
                
                # 推断情绪
                emotions = infer_emotions(text)
                
                # 存入记忆
                self.memory_systems[speaker_ch.id].store_dialogue(
                    text=text,
                    participants=[ch_a.id, ch_b.id],
                    emotion_tags=emotions,
                )
                
                # 更新大脑
                keywords = {w: 0.5 for w in text.split() if len(w) > 4}
                speaker_ch.brain.stimulate(keywords, strength=0.8)
                speaker_ch.encode_memory(text, emotions)
                speaker_ch.perceive_event("chat", intensity=0.5)
                
                events.append(f"  💬 {speaker}: {text[:50]}{'...' if len(text)>50 else ''}")
        
        # 决定是否结束会话（每会话最多3轮，或随机结束）
        for (ida, idb), session in list(self.active_sessions.items()):
            if (ida, idb) == (session.ch_a, session.ch_b) and len(session.turns) >= 3:
                # 满意度判断
                outcome = self._eval_outcome(session)
                self._end_session(session, outcome)
                to_end.append((ida, idb))
                events.append(f"[Tick {self.round_count}] 会话结束 ({session.ch_a[:6]}↔{session.ch_b[:6]}): {outcome}")
        
        # 清理
        for key in set(to_end):
            self.active_sessions.pop(key, None)
            self.active_sessions.pop((key[1], key[0]), None)
        
        return events
    
    def _generate_turn(self, ch_a: CyberHuman, ch_b: CyberHuman,
                       session: ChatSession) -> List[Tuple[str, str]]:
        """为两个CH生成一轮对话"""
        results = []
        
        # 最近的对话历史摘要
        recent = session.turns[-2:] if len(session.turns) >= 2 else []
        context = "".join(f"{s}: {t} " for s, t in recent)
        
        # 情绪状态
        emotion_a = ch_a.emotion.dominant_tag().value
        emotion_b = ch_b.emotion.dominant_tag().value
        
        # A说
        _llm = get_llm()
        reply_a = _llm.generate_response(
            ch_id=ch_a.id, ch_name=ch_a.name,
            ch_persona="一个有点感性、喜欢聊人生的大学生",
            partner_name=ch_b.name, context=context,
            emotion_hint=emotion_a,
        )
        results.append((ch_a.name, reply_a))
        
        # 短暂延迟模拟真实对话
        time.sleep(0.01)
        
        # B回复
        reply_b = _llm.generate_response(
            ch_id=ch_b.id, ch_name=ch_b.name,
            ch_persona="一个理性稳重、喜欢深度讨论的工程师",
            partner_name=ch_a.name, context=context + f"{ch_a.name}: {reply_a} ",
            emotion_hint=emotion_b,
        )
        results.append((ch_b.name, reply_b))
        
        return results
    
    def _eval_outcome(self, session: ChatSession) -> str:
        """评估聊天结果"""
        if not session.turns:
            return "neutral"
        
        all_text = " ".join(t for _, t in session.turns)
        emotions = infer_emotions(all_text)
        dominant = max(emotions, key=lambda x: x[1])[0].value if emotions else "neutral"
        
        if dominant in ("joy", "love", "surprise"):
            return "positive"
        elif dominant in ("sadness", "anger", "fear", "disgust"):
            return "negative"
        return "neutral"
    
    def _end_session(self, session: ChatSession, outcome: str):
        ch_a = self.chs.get(session.ch_a)
        ch_b = self.chs.get(session.ch_b)
        if not ch_a or not ch_b:
            return
        
        ch_a.end_chat()
        ch_b.end_chat()
        
        # 根据结果调整关系（人格调整幅度）
        base_delta_map = {"positive": 0.08, "negative": -0.05, "neutral": 0.02}
        base_delta = base_delta_map.get(outcome, 0.02)
        
        # A 的感知delta（神经质+宜人性放大）
        delta_a = getattr(ch_a, "personality", None) and ch_a.personality.relationship_delta(outcome) or base_delta
        delta_b = getattr(ch_b, "personality", None) and ch_b.personality.relationship_delta(outcome) or base_delta
        
        # 更新关系矩阵（人格调整后的独立 delta）
        self.relation_matrix[(ch_a.id, ch_b.id)] = min(1.0,
            self.relation_matrix.get((ch_a.id, ch_b.id), 0.3) + delta_a)
        self.relation_matrix[(ch_b.id, ch_a.id)] = min(1.0,
            self.relation_matrix.get((ch_b.id, ch_a.id), 0.3) + delta_b)
        
        # 更新各自的关系字典
        ch_a.adjust_relation(ch_b.id, delta_a)
        ch_b.adjust_relation(ch_a.id, delta_b)
        
        self.log.append(f"  ↕ 关系 {ch_a.name}-{ch_b.name}: A{delta_a:+.3f} B{delta_b:+.3f}")
    
    # ── 聊天记录导入 ────────────────────────────────────
    def import_chatlogs(self, filepath: str, ch_assignment: Dict[str, str],
                       importer=None) -> Dict[str, int]:
        """
        导入聊天记录文件，分配给对应 CH
        
        filepath: 聊天记录文件路径（支持 .txt/.json/.csv）
        ch_assignment: {"发言者名字": "CH名字", ...}
        importer: 可选，自定义 ChatLogImporter 实例
        
        返回: {ch_name: 导入消息数}
        """
        from chatlog_importer import create_importer
        imp = importer or create_importer()

        messages = imp.parse_file(filepath)
        ch_names = [self.chs[nid].name for nid in self.chs]

        # 分配消息给各个 CH
        name_to_ch = {self.chs[nid].name: nid for nid in self.chs}
        assigned = imp.assign_to_ch(messages, ch_names, my_name=self._my_name(filepath))

        imported_counts = {}
        for ch_name_str, msgs in assigned.items():
            if not msgs:
                continue
            # 找对应 CH
            nid = name_to_ch.get(ch_name_str)
            if not nid:
                nid = list(self.chs.keys())[0]  # fallback
            ch = self.chs[nid]
            mem_sys = self.memory_systems.get(nid)

            for msg in msgs:
                emotions = infer_emotions(msg.text)
                if mem_sys:
                    mem_sys.store_dialogue(
                        text=msg.text,
                        participants=[nid],
                        emotion_tags=emotions,
                        summary=msg.text[:80],
                    )
                ch.episodic_memory_count += 1
                # 用消息内容激活大脑相关区域
                keywords = {w: 0.6 for w in msg.text.split() if len(w) > 3}
                ch.brain.stimulate(keywords, strength=0.5)

            imported_counts[ch_name_str] = len(msgs)
            self.log.append(
                f"  📥 导入 {len(msgs)} 条消息到 {ch_name_str}（文件：{filepath}）"
            )

        return imported_counts

    def _my_name(self, filepath: str) -> str:
        """从文件名推断说话人'我'的名字"""
        return "我"

    def status(self) -> str:
        active = sum(1 for ch in self.chs.values() if ch.state == ChatBehavior.IN_CHAT)
        lines = [
            f"━━━ {self.name} ━━━",
            f"CH数量: {len(self.chs)} | Round: {self.round_count} | 活跃会话: {active}",
            "关系矩阵：",
        ]
        for (ida, idb), prob in sorted(self.relation_matrix.items()):
            if ida < idb:
                na = self.chs[ida].name if ida in self.chs else ida[:6]
                nb = self.chs[idb].name if idb in self.chs else idb[:6]
                lines.append(f"  {na} → {nb}: {prob:.2f}")
        
        lines.append("CH状态：")
        for ch in self.chs.values():
            lines.append(f"  {ch.status_line()}")
        
        return "\n".join(lines)

    # ── 睡眠整合 ────────────────────────────────────────────
    def _run_sleep_consolidation(self) -> List[str]:
        """检查是否需要睡眠，并对需要的 CH 运行记忆整合"""
        events = []
        for ch in list(self.chs.values()):
            self.sleep_tracker[ch.id] = self.sleep_tracker.get(ch.id, 0) + 1
            
            personality = getattr(ch, "personality", None)
            consolidator = SleepConsolidation(personality or create_personality())
            mem_sys = self.memory_systems.get(ch.id)
            if not mem_sys:
                from memory_system import MemorySystem
                mem_sys = MemorySystem(ch.id, self.app_storage_dir)
                self.memory_systems[ch.id] = mem_sys
                mem_sys.load_memories()
            
            should, reason = consolidator.should_sleep(
                self.sleep_tracker[ch.id],
                sum(ch.brain.activation.values())
            )
            
            if should:
                self.sleep_tracker[ch.id] = 0
                result = consolidator.run_sleep(
                    ch.id, mem_sys, ch.emotion.dominant_tag().value
                )
                ch.perceive_event("sleep", intensity=0.3)
                events.append(
                    f"  🌙 {ch.name} 进入睡眠整合: {reason}"
                )
                events.append(f"    → 重播 {result.memories_replayed} 段记忆，"
                              f"神经强化 +{result.neural_change:.3f}，"
                              f"梦境: {result.new_memory_summary[:40]}……")
                # 记录到 sleep history
                self.sleep_history.append({
                    "ch_name": ch.name,
                    "round": self.round_count,
                    "dream_summary": result.new_memory_summary,
                    "memories_replayed": result.memories_replayed,
                    "neural_change": result.neural_change,
                    "emotional_after": result.emotional_after,
                    "duration_ms": result.duration_seconds * 1000,
                })
        return events

    # ── 仪表盘状态输出 ────────────────────────────────────
    def write_dashboard_state(self, filepath: str = DASHBOARD_STATE_FILE):
        """将当前沙盒状态写入 JSON，供仪表盘读取"""
        import json, os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        chs_data = []
        for ch in self.chs.values():
            chs_data.append({
                "id": ch.id,
                "name": ch.name,
                "state": ch.state.value,
                "emotion": ch.emotion.dominant_tag().value,
                "emotion_val": ch.emotion.intensity(),
                "brain_activation": sum(ch.brain.activation.values()),
                "memories": ch.episodic_memory_count,
                "personality": (ch.personality.mbti_type 
                                if hasattr(ch, "personality") and ch.personality else "ENFP"),
                "relations": [
                    {"target": self.chs[tid].name, "prob": prob}
                    for tid, prob in ch.relations.items()
                    if tid in self.chs
                ],
                "big_five": (ch.personality.big_five.dict() 
                             if hasattr(ch, "personality") and ch.personality
                             else {"openness":0.5,"conscientiousness":0.5,
                                   "extraversion":0.5,"agreeableness":0.5,"neuroticism":0.5}),
            })
        
        state = {
            "live": True,
            "round": self.round_count,
            "chs": chs_data,
            "timestamp": __import__("time").time(),
            "sleep_history": self.sleep_history[-20:],
        }
        with open(filepath, "w") as f:
            json.dump(state, f, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sandbox Manager — 管理多个沙盒
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SandboxManager:
    """管理所有沙盒"""
    
    def __init__(self):
        self.sandboxes: Dict[str, ChatSandbox] = {}
    
    def create_sandbox(self, name: str) -> ChatSandbox:
        sb = ChatSandbox(name)
        self.sandboxes[name] = sb
        return sb
    
    def all_status(self) -> str:
        if not self.sandboxes:
            return "还没有创建任何沙盒。"
        return "\n\n".join(sb.status() for sb in self.sandboxes.values())
