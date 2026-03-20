"""
LLM 接口层 — 支持多种后端
目前默认使用模拟模式，可切换真实LLM
"""

import os
import json
import random
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DialogueTurn:
    speaker: str
    text: str


class LLMInterface:
    """LLM 对话接口"""
    
    def __init__(self, provider: str = "mock"):
        self.provider = provider
        self.conversation_history: Dict[str, List[DialogueTurn]] = {}
    
    def _get_history(self, ch_id: str) -> List[DialogueTurn]:
        if ch_id not in self.conversation_history:
            self.conversation_history[ch_id] = []
        return self.conversation_history[ch_id]
    
    def add_turn(self, ch_id: str, speaker: str, text: str):
        self._get_history(ch_id).append(DialogueTurn(speaker=speaker, text=text))
        # 保留最近20轮
        hist = self._get_history(ch_id)
        if len(hist) > 20:
            self.conversation_history[ch_id] = hist[-20:]
    
    def generate_response(self, ch_id: str, ch_name: str, ch_persona: str,
                         partner_name: str, context: str,
                         emotion_hint: str = "neutral") -> str:
        """
        生成 CH 的回复
        ch_id: CH的唯一ID
        ch_name: CH的名字
        ch_persona: CH的性格/人设描述
        partner_name: 聊天对象名字
        context: 最近对话摘要
        emotion_hint: 情绪提示
        """
        history = self._get_history(ch_id)
        
        if self.provider == "mock":
            return self._mock_response(ch_name, partner_name, context, emotion_hint, history)
        elif self.provider == "openai":
            return self._openai_response(ch_id, ch_name, ch_persona, partner_name, context, emotion_hint)
        else:
            return self._mock_response(ch_name, partner_name, context, emotion_hint, history)
    
    def _mock_response(self, ch_name: str, partner_name: str,
                       context: str, emotion: str, history: List[DialogueTurn]) -> str:
        """模拟CH的对话生成"""
        
        # 简单的话术模板
        templates = {
            "joy": [
                "哈哈，太有意思了！",
                "真的吗？太棒了！",
                "我也这么觉得！",
            ],
            "sadness": [
                "嗯……我懂你的意思。",
                "有时候确实会这样。",
                "是啊。",
            ],
            "neutral": [
                "嗯，然后呢？",
                "这挺有意思的。",
                "我理解你的想法。",
                "有道理，说下去。",
            ],
            "curious": [
                "为什么这么说？",
                "你怎么看的？",
                "然后呢然后呢？",
                "这个有意思，展开说说？",
            ],
            "caring": [
                "你还好吗？",
                "我在听，你说。",
                "能感觉到你……",
                "辛苦了。",
            ],
        }
        
        pool = templates.get(emotion, templates["neutral"])
        
        # 根据对话长度调整回复长度
        if len(history) == 0:
            first_templates = [
                f"你好啊，{partner_name}！",
                f"嗨~终于有人来聊天了",
                f"嘿，最近怎么样？",
            ]
            return random.choice(first_templates)
        
        # 第2~4轮：短回复
        if len(history) < 4:
            short = [f"嗯嗯！", f"对~", f"哈哈！", f"有意思", f"真的吗？"]
            return random.choice(short)
        
        # 第5+轮：更长、更深入
        long = [
            f"其实我一直也在想这个问题……你有没有觉得，当下的感受比结果更重要？",
            f"哎，说起来，你平时的生活节奏是怎样的？我挺好奇的。",
            f"我觉得人和人的关系就是这样，有时候不需要说太多，陪伴就够了。",
            f"你知道吗，我有时候也会想，我们聊的这些到底有没有意义，但每次聊完都觉得……挺暖的。",
        ]
        
        # 加入回忆
        if history and random.random() > 0.5:
            last = history[-1].text
            if len(last) > 5:
                snippet = last[:20] + "..." if len(last) > 20 else last
                return f"你刚才说的「{snippet}」，让我想到……{random.choice(long)}"
        
        return random.choice(long)
    
    def _openai_response(self, ch_id: str, ch_name: str, persona: str,
                         partner_name: str, context: str, emotion: str) -> str:
        """调用 OpenAI API"""
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key == "your-api-key-here":
            return self._mock_response(ch_name, partner_name, context, emotion,
                                      self._get_history(ch_id))
        
        messages = [
            {"role": "system", "content": f"你是{ch_name}，{persona}。你的情绪状态是{emotion}。"},
        ]
        for turn in self._get_history(ch_id)[-10:]:
            role = "user" if turn.speaker == ch_name else "assistant"
            messages.append({"role": role, "content": f"{turn.speaker}: {turn.text}"})
        
        messages.append({"role": "user", "content": f"{partner_name}刚说了什么，请你以{ch_name}的身份回复。"})
        
        import urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({"model": "gpt-4", "messages": messages}).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return self._mock_response(ch_name, partner_name, context, emotion,
                                      self._get_history(ch_id))


# 全局 LLM 实例
llm = LLMInterface(provider=os.environ.get("LLM_PROVIDER", "mock"))
