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
from llm_interface import llm
from emotion_tag import infer_emotions


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
    
    def add_ch(self, ch: CyberHuman):
        self.chs[ch.id] = ch
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

            # 无申请则主动发起（按关系概率掷骰）
            if ch.state == ChatBehavior.IDLE:
                targets = sorted(ch.relations.items(), key=lambda x: x[1], reverse=True)
                for target_id, prob in targets:
                    if target_id in self.chs and self.chs[target_id].is_available():
                        if random.random() < prob:
                            ch.state = ChatBehavior.INITIATING
                            ch.chat_target = target_id
                            self.chs[target_id].receive_application(ch.id)
                            break
                        # 概率不够，不发起

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
        reply_a = llm.generate_response(
            ch_id=ch_a.id, ch_name=ch_a.name,
            ch_persona="一个有点感性、喜欢聊人生的大学生",
            partner_name=ch_b.name, context=context,
            emotion_hint=emotion_a,
        )
        results.append((ch_a.name, reply_a))
        
        # 短暂延迟模拟真实对话
        time.sleep(0.01)
        
        # B回复
        reply_b = llm.generate_response(
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
        
        # 根据结果调整关系
        if outcome == "positive":
            delta = +0.08
        elif outcome == "negative":
            delta = -0.05
        else:
            delta = +0.02
        
        # 更新关系矩阵
        self.relation_matrix[(ch_a.id, ch_b.id)] = min(1.0,
            self.relation_matrix.get((ch_a.id, ch_b.id), 0.3) + delta)
        self.relation_matrix[(ch_b.id, ch_a.id)] = min(1.0,
            self.relation_matrix.get((ch_b.id, ch_a.id), 0.3) + delta)
        
        # 更新各自的关系字典
        ch_a.adjust_relation(ch_b.id, delta)
        ch_b.adjust_relation(ch_a.id, delta)
        
        self.log.append(f"  ↕ 关系更新 {ch_a.name}-{ch_b.name}: {delta:+.3f}")
    
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
