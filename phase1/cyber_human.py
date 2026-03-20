"""
SereneX Phase 1 — Chat Sandbox
Cyber Human 核心定义
"""

import uuid
import time
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


class ChatBehavior(Enum):
    IDLE = "idle"
    INITIATING = "initiating"
    WAITING = "waiting"
    PENDING = "pending"
    IN_CHAT = "in_chat"


class EmotionLabel(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    LOVE = "love"
    ANXIETY = "anxiety"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


@dataclass
class EmotionState:
    """情绪状态"""
    valence: float = 0.5      # 愉悦度 0~1
    arousal: float = 0.5       # 激活度 0~1
    dominance: float = 0.5    # 控制感 0~1
    tags: List[Tuple[EmotionLabel, float]] = field(default_factory=list)
    
    def dominant_tag(self) -> EmotionLabel:
        if not self.tags:
            return EmotionLabel.NEUTRAL
        return max(self.tags, key=lambda x: x[1])[0]
    
    def intensity(self) -> float:
        if not self.tags:
            return 0.0
        return max(t[1] for t in self.tags)


@dataclass
class Synapse:
    """突触连接"""
    target_neuron_id: str
    weight: float          # 连接强度 -1.0 ~ 1.0
    last_spike_delta: float = float('inf')  # 上次发放时间差


class NeuralNetworkBrain:
    """
    简化的神经网络大脑
    - 使用加权有向图表示神经元连接结构
    - STDP (Hebbian) 学习：一起发放的神经元连接加强
    """
    
    def __init__(self, name: str, num_neurons: int = 64):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.num_neurons = num_neurons
        
        # 神经元池：neuron_id -> [synapse_ids]
        self.neurons: Dict[str, List[str]] = {}
        # 突触池：synapse_id -> Synapse
        self.synapses: Dict[str, Synapse] = {}
        # 神经元激活状态
        self.activation: Dict[str, float] = {}  # neuron_id -> current activation
        
        self._init_network()
    
    def _init_network(self):
        """初始化全连接薄弱的网络"""
        import random
        neuron_ids = [f"n_{i}" for i in range(self.num_neurons)]
        for nid in neuron_ids:
            self.neurons[nid] = []
            self.activation[nid] = 0.0
            # 随机连接 3~8 个其他神经元
            num_conns = random.randint(3, 8)
            targets = random.sample([n for n in neuron_ids if n != nid], 
                                    min(num_conns, len(neuron_ids)-1))
            for t in targets:
                sid = str(uuid.uuid4())[:12]
                weight = random.uniform(-0.2, 0.2)  # 初始弱连接
                self.synapses[sid] = Synapse(target_neuron_id=t, weight=weight)
                self.neurons[nid].append(sid)
    
    def stimulate(self, stimulus: Dict[str, float], strength: float = 1.0):
        """
        外部刺激输入，激活相关神经元
        stimulus: {神经元ID前缀片段: 激活强度}
        """
        for nid in list(self.neurons.keys()):
            match_score = 0.0
            for pattern, score in stimulus.items():
                if pattern.lower() in nid.lower():
                    match_score += score
            self.activation[nid] += match_score * strength * 0.1
        
        # 衰减
        for nid in self.activation:
            self.activation[nid] *= 0.85
    
    def fire(self) -> List[str]:
        """
        运行一次发放：激活超阈值的神经元，返回发放的神经元ID列表
        """
        fired = []
        threshold = 0.3
        
        for nid, pot in self.activation.items():
            if pot >= threshold:
                fired.append(nid)
                # STDP: 加强所有从该神经元发出的突触
                for sid in self.neurons.get(nid, []):
                    synapse = self.synapses.get(sid)
                    if synapse:
                        synapse.weight = min(1.0, synapse.weight + 0.05)
                        synapse.last_spike_delta = 0.0
        
        # 被激活神经元的突触后神经元也轻微激活
        for nid in fired:
            for sid in self.neurons.get(nid, []):
                synapse = self.synapses.get(sid)
                if synapse:
                    target = synapse.target_neuron_id
                    self.activation[target] += synapse.weight * 0.3
        
        # 发放后衰减
        for nid in self.activation:
            self.activation[nid] *= 0.85
        
        return fired
    
    def connection_profile(self) -> List[Tuple[str, str, float]]:
        """返回所有连接的强度列表"""
        result = []
        for sid, syn in self.synapses.items():
            # 反查源神经元
            for src, syns in self.neurons.items():
                if sid in syns:
                    result.append((src, syn.target_neuron_id, syn.weight))
                    break
        return result
    
    def summary(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "neurons": self.num_neurons,
            "synapses": len(self.synapses),
            "avg_weight": sum(s.weight for s in self.synapses.values()) / max(1, len(self.synapses)),
            "total_activation": sum(self.activation.values()),
        }


@dataclass
class CyberHuman:
    """
    Cyber Human — 小龙虾
    对应一个真实的人的神经网络 + 记忆 + 情绪
    """
    name: str
    user_id: str
    
    # 神经网络
    brain: NeuralNetworkBrain = field(init=False)
    
    # 记忆片段数
    episodic_memory_count: int = 0
    image_memory_count: int = 0
    
    # 行为状态
    state: ChatBehavior = ChatBehavior.IDLE
    chat_target: Optional[str] = None           # 当前/目标聊天对象 ID
    pending_applications: List[str] = field(default_factory=list)  # 待处理的申请队列
    
    # 关系强度（自己视角）
    relations: Dict[str, float] = field(default_factory=dict)  # target_id -> 聊天概率
    
    # 情绪
    emotion: EmotionState = field(default_factory=EmotionState)
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    
    def __post_init__(self):
        self.brain = NeuralNetworkBrain(name=self.name)
    
    def is_available(self) -> bool:
        return self.state in (ChatBehavior.IDLE, ChatBehavior.WAITING)
    
    def receive_application(self, from_id: str):
        self.pending_applications.append(from_id)
        if self.state == ChatBehavior.IDLE:
            self.state = ChatBehavior.PENDING
    
    def advance_behavior(self, relation_matrix: Dict[Tuple[str,str], float]) -> Tuple[ChatBehavior, Optional[str]]:
        """
        根据关系矩阵决定下一步行为
        返回 (next_behavior, target_id)
        """
        self.last_active = time.time()
        
        # 处理待处理的申请
        if self.pending_applications:
            applicant = self.pending_applications.pop(0)
            prob = relation_matrix.get((self.id, applicant), 0.3)
            import random
            if random.random() < prob:
                self.state = ChatBehavior.IN_CHAT
                self.chat_target = applicant
                return (ChatBehavior.IN_CHAT, applicant)
            else:
                self.state = ChatBehavior.IDLE
                return (ChatBehavior.IDLE, None)
        
        # 主动发起聊天
        if self.state == ChatBehavior.IDLE:
            import random
            # 按关系强度排序，选前3
            targets = sorted(self.relations.items(), key=lambda x: x[1], reverse=True)[:3]
            if targets:
                # 按概率掷骰
                for target_id, prob in targets:
                    if random.random() < prob:
                        self.state = ChatBehavior.INITIATING
                        self.chat_target = target_id
                        return (ChatBehavior.INITIATING, target_id)
            
            self.state = ChatBehavior.WAITING
            return (ChatBehavior.WAITING, None)
        
        return (self.state, self.chat_target)
    
    def end_chat(self):
        """结束当前聊天"""
        self.state = ChatBehavior.IDLE
        self.chat_target = None
    
    def adjust_relation(self, other_id: str, delta: float):
        """调整与另一CH的关系"""
        current = self.relations.get(other_id, 0.3)
        self.relations[other_id] = max(0.0, min(1.0, current + delta))
    
    def encode_memory(self, text: str, emotion_tags: List[Tuple[EmotionLabel, float]]):
        """将一段对话编码进记忆，激活大脑相关区域"""
        self.episodic_memory_count += 1
        
        # 提取关键词激活大脑
        words = text.lower().split()
        stimulus = {}
        for i, word in enumerate(words):
            if len(word) > 4:
                stimulus[f"n_{i % self.brain.num_neurons}"] = 0.5
        
        self.brain.stimulate(stimulus, strength=1.0)
        fired = self.brain.fire()
        
        # 更新情绪
        for tag, intensity in emotion_tags:
            self.emotion.tags = [(t, i) for t, i in self.emotion.tags if t != tag]
            self.emotion.tags.append((tag, intensity))
        
        # 更新基础情绪维度
        self._update_valence_arousal(emotion_tags)
        
        return fired
    
    def _update_valence_arousal(self, tags: List[Tuple[EmotionLabel, float]]):
        """根据情绪标签更新 VAD"""
        val_map = {EmotionLabel.JOY: 0.9, EmotionLabel.LOVE: 0.85,
                   EmotionLabel.ANTICIPATION: 0.7, EmotionLabel.SURPRISE: 0.6,
                   EmotionLabel.NEUTRAL: 0.5, EmotionLabel.DISGUST: 0.2,
                   EmotionLabel.ANGER: 0.15, EmotionLabel.FEAR: 0.1,
                   EmotionLabel.SADNESS: 0.1, EmotionLabel.ANXIETY: 0.2}
        arou_map = {EmotionLabel.JOY: 0.7, EmotionLabel.ANGER: 0.9,
                    EmotionLabel.FEAR: 0.85, EmotionLabel.ANXIETY: 0.8,
                    EmotionLabel.SURPRISE: 0.8, EmotionLabel.LOVE: 0.6,
                    EmotionLabel.SADNESS: 0.3, EmotionLabel.NEUTRAL: 0.3}
        
        if tags:
            avg_val = sum(val_map.get(t, 0.5)*i for t,i in tags) / max(1, sum(i for _,i in tags))
            avg_arou = sum(arou_map.get(t, 0.5)*i for t,i in tags) / max(1, sum(i for _,i in tags))
            self.emotion.valence = avg_val * 0.3 + self.emotion.valence * 0.7
            self.emotion.arousal = avg_arou * 0.3 + self.emotion.arousal * 0.7
    
    def perceive_event(self, event_type: str, intensity: float = 0.5):
        """感知一个事件，激活大脑"""
        stimulus = {f"n_{hash(event_type) % self.brain.num_neurons}": intensity}
        self.brain.stimulate(stimulus, strength=intensity)
    
    def status_line(self) -> str:
        return (f"[{self.name}/{self.id[:6]}] "
                f"state={self.state.value} "
                f"emotion={self.emotion.dominant_tag().value} "
                f"mem={self.episodic_memory_count} "
                f"brain_act={sum(self.brain.activation.values()):.3f}")
