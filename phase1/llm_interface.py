"""
SereneX Phase 1 — LLM 接口层
支持 Mock / DeepSeek / OpenAI / 阿里通义Qwen

运行前设置环境变量：
  export LLM_PROVIDER=deepseek        # deepseek | openai | qwen | mock
  export DEEPSEEK_API_KEY=sk-xxx
  export OPENAI_API_KEY=sk-xxx
  export QWEN_API_KEY=sk-xxx
"""

import os, json, random, time
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class DialogueTurn:
    speaker: str
    text: str


def _load_env():
    """延迟加载环境变量"""
    return {
        "provider": os.environ.get("LLM_PROVIDER", "mock"),
        "deepseek_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "openai_key": os.environ.get("OPENAI_API_KEY", ""),
        "qwen_key": os.environ.get("QWEN_API_KEY", ""),
        "qwen_model": os.environ.get("QWEN_MODEL", "qwen-plus"),
        "deepseek_model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    }


class LLMInterface:
    """
    统一 LLM 对话接口
    provider: mock | deepseek | openai | qwen
    """

    def __init__(self, provider: str = None):
        cfg = _load_env()
        self.provider = provider or cfg["provider"]
        self.deepseek_key = cfg["deepseek_key"]
        self.openai_key = cfg["openai_key"]
        self.qwen_key = cfg["qwen_key"]
        self.qwen_model = cfg["qwen_model"]
        self.deepseek_model = cfg["deepseek_model"]
        self.conversation_history: Dict[str, List[DialogueTurn]] = {}
        self._last_request_time: Dict[str, float] = {}  # 防止频繁请求

    def _history(self, ch_id: str) -> List[DialogueTurn]:
        if ch_id not in self.conversation_history:
            self.conversation_history[ch_id] = []
        return self.conversation_history[ch_id]

    def add_turn(self, ch_id: str, speaker: str, text: str):
        hist = self._history(ch_id)
        hist.append(DialogueTurn(speaker=speaker, text=text))
        if len(hist) > 30:
            self.conversation_history[ch_id] = hist[-30:]

    def generate_response(
        self,
        ch_id: str,
        ch_name: str,
        ch_persona: str,
        partner_name: str,
        context: str,
        emotion_hint: str = "neutral",
    ) -> str:
        """生成 CH 的回复（根据配置的 provider）"""
        if self.provider == "deepseek":
            return self._deepseek_response(ch_id, ch_name, ch_persona, partner_name, context, emotion_hint)
        elif self.provider == "openai":
            return self._openai_response(ch_id, ch_name, ch_persona, partner_name, context, emotion_hint)
        elif self.provider == "qwen":
            return self._qwen_response(ch_id, ch_name, ch_persona, partner_name, context, emotion_hint)
        else:
            return self._mock_response(ch_name, partner_name, context, emotion_hint, self._history(ch_id))

    # ── DeepSeek ────────────────────────────────────────────

    def _deepseek_response(self, ch_id: str, ch_name: str, persona: str,
                           partner: str, context: str, emotion: str) -> str:
        """调用 DeepSeek API"""
        if not self.deepseek_key or self.deepseek_key == "your-key-here":
            print(f"  [LLM] DeepSeek key 未设置，回退到 mock 模式")
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))

        # 节流：同 ch_id 5秒内不重复请求（返回缓存或简单回复）
        now = time.time()
        if ch_id in self._last_request_time and now - self._last_request_time[ch_id] < 3:
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))
        self._last_request_time[ch_id] = now

        system_prompt = (
            f"你是{ch_name}，{persona}。你的当前情绪状态是「{emotion}」。\n"
            f"你现在正和{partner}聊天。注意：\n"
            f"1. 回复要简短自然，1-3句话，口语化\n"
            f"2. 符合你的性格（{persona}）\n"
            f"3. 情绪状态影响你的表达方式（{emotion}状态时语气会不同）\n"
            f"4. 直接回复内容即可，不要加引号或署名"
        )

        history = self._history(ch_id)[-12:]
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "assistant" if turn.speaker == ch_name else "user"
            messages.append({"role": role, "content": f"{turn.speaker}: {turn.text}"})
        if context:
            messages.append({"role": "user", "content": f"{partner}刚刚说了：{context[:200]}"})
        messages.append({"role": "user", "content": f"请以{ch_name}的身份回复{partner}，简短自然。"})

        import urllib.request
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps({
                "model": self.deepseek_model,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.8,
                "top_p": 0.9,
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.deepseek_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                content = data["choices"][0]["message"]["content"].strip()
                # 去掉可能的引号
                content = content.strip('"').strip("'")
                self.add_turn(ch_id, ch_name, content)
                return content
        except Exception as e:
            print(f"  [LLM] DeepSeek API 错误: {e}")
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))

    # ── OpenAI ──────────────────────────────────────────────

    def _openai_response(self, ch_id: str, ch_name: str, persona: str,
                          partner: str, context: str, emotion: str) -> str:
        """调用 OpenAI GPT API"""
        if not self.openai_key or self.openai_key == "your-key-here":
            print(f"  [LLM] OpenAI key 未设置，回退到 mock 模式")
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))

        now = time.time()
        if ch_id in self._last_request_time and now - self._last_request_time[ch_id] < 3:
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))
        self._last_request_time[ch_id] = now

        system_prompt = (
            f"You are {ch_name}. {persona}. Your emotional state is '{emotion}'.\n"
            f"You are chatting with {partner}. Keep responses short (1-3 sentences), natural, "
            f"in character. Reply only the content, no quotes or signatures."
        )

        history = self._history(ch_id)[-12:]
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "assistant" if turn.speaker == ch_name else "user"
            messages.append({"role": role, "content": f"{turn.speaker}: {turn.text}"})
        if context:
            messages.append({"role": "user", "content": f"{partner} just said: {context[:200]}"})

        import urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.8,
            }).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                content = data["choices"][0]["message"]["content"].strip()
                content = content.strip('"').strip("'")
                self.add_turn(ch_id, ch_name, content)
                return content
        except Exception as e:
            print(f"  [LLM] OpenAI API 错误: {e}")
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))

    # ── 通义Qwen ─────────────────────────────────────────────

    def _qwen_response(self, ch_id: str, ch_name: str, persona: str,
                        partner: str, context: str, emotion: str) -> str:
        """调用阿里云通义千问 API"""
        if not self.qwen_key or self.qwen_key == "your-key-here":
            print(f"  [LLM] Qwen key 未设置，回退到 mock 模式")
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))

        now = time.time()
        if ch_id in self._last_request_time and now - self._last_request_time[ch_id] < 3:
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))
        self._last_request_time[ch_id] = now

        system_prompt = (
            f"你是{ch_name}，{persona}。你现在的情绪状态是「{emotion}」。"
            f"和{partner}聊天时，要符合你的性格，口语化，简短（1-3句话）。"
            f"不要加引号或署名，直接回复。"
        )

        history = self._history(ch_id)[-12:]
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "assistant" if turn.speaker == ch_name else "user"
            messages.append({"role": role, "content": f"{turn.speaker}: {turn.text}"})
        if context:
            messages.append({"role": "user", "content": f"{partner}刚才说：{context[:200]}"})
        messages.append({"role": "user", "content": f"请以{ch_name}身份简短回复{partner}。"})

        import urllib.request
        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=json.dumps({
                "model": self.qwen_model,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.8,
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.qwen_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                content = data["choices"][0]["message"]["content"].strip()
                content = content.strip('"').strip("'")
                self.add_turn(ch_id, ch_name, content)
                return content
        except Exception as e:
            print(f"  [LLM] Qwen API 错误: {e}")
            return self._mock_response(ch_name, partner, context, emotion, self._history(ch_id))

    # ── Mock 回复 ─────────────────────────────────────────────

    def _mock_response(self, ch_name: str, partner: str,
                       context: str, emotion: str,
                       history: List[DialogueTurn]) -> str:
        """本地模拟回复（无需 API key）"""
        templates = {
            "joy": ["哈哈，太有意思了！", "真的吗？太棒了！", "我也这么觉得！"],
            "sadness": ["嗯……我懂你的意思。", "有时候确实会这样。", "是啊。"],
            "anger": ["这有点让人恼火……", "真的吗？有点生气。"],
            "fear": ["有点担心……", "真的吗？我有点怕。"],
            "surprise": ["哇！真的假的？", "没想到！", "这太意外了！"],
            "disgust": ["有点无语……", "这让人不太舒服。"],
            "love": ["你真好～", "好温暖啊！", "好感动！"],
            "anxiety": ["怎么办啊……", "有点焦虑。", "我也在想这个问题。"],
            "anticipation": ["期待！", "好想快点！", "然后呢然后呢？"],
            "neutral": ["嗯，然后呢？", "这挺有意思的。", "我理解你的想法。",
                         "有道理，说下去。", "嗯嗯！"],
            "curious": ["为什么这么说？", "你怎么看的？", "展开说说？"],
            "caring": ["你还好吗？", "我在听，你说。", "辛苦了。"],
        }

        pool = templates.get(emotion, templates["neutral"])

        if not history:
            first = [
                f"你好啊，{partner}！我是{ch_name}。",
                f"嗨~终于有人来聊天了！",
                f"嘿，{partner}，最近怎么样？",
            ]
            return random.choice(first)

        if len(history) < 3:
            return random.choice([f"嗯嗯！", f"对~", f"哈哈！", f"有意思", f"真的吗？"])

        # 第3轮以后，更长一些
        long_templates = [
            f"其实我一直也在想这个问题……你有没有觉得，当下的感受比结果更重要？",
            f"说起来，{partner}你平时的生活节奏是怎样的？挺好奇的。",
            f"人和人的关系就是这样，有时候不需要说太多，陪伴就够了。",
            f"有时候我也会想，我们聊的这些到底有没有意义，但每次聊完都觉得……挺暖的。",
            f"突然想到，你有没有那种……忽然很怀念某个时刻的感觉？",
        ]

        if history and random.random() > 0.5:
            last = history[-1].text
            snippet = last[:25] + "..." if len(last) > 25 else last
            return f"你刚才说的「{snippet}」，让我想到……{random.choice(long_templates)}"

        return random.choice(long_templates)


# ── 全局实例（懒加载）────────────────────────────────────────
_llm_instance: LLMInterface = None

def get_llm() -> LLMInterface:
    global _llm_instance
    if _llm_instance is None:
        cfg = _load_env()
        _llm_instance = LLMInterface(provider=cfg["provider"])
    return _llm_instance


# 兼容旧写法
llm = None  # 用户需要先调用 get_llm() 或设置 LLM_PROVIDER
