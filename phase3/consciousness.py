"""
SereneX Phase 3 — 意识核心（Consciousness）
包含：意图形成 / 自我反思 / 内心独白 / 自由意志模拟
"""
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from memory import LongTermMemory, MemoryEntry, new_memory_id, calc_emotion_weight, EmotionVector


@dataclass
class Intention:
    """意图"""
    description: str          # 自然语言描述
    goal_type: str            # explore | build | socialize | rest | find_resource | help_other
    target: str = ""          # 目标对象/位置
    urgency: float = 0.5      # 紧急程度 0~1
    related_memories: list[str] = field(default_factory=list)  # 相关记忆ID
    confidence: float = 0.5   # 执行把握
    plan_steps: list[str] = field(default_factory=list)  # 动作序列

    def to_prompt(self) -> str:
        return (
            f"意图：{self.description}\n"
            f"类型：{self.goal_type}\n"
            f"目标：{self.target}\n"
            f"计划步骤：\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.plan_steps))
        )


class Consciousness:
    """
    Cyber Human 的意识核心
    负责：内心独白、意图形成、自我反思、记忆回溯
    """

    def __init__(self, ch_name: str, llm_provider: str = "deepseek"):
        self.ch_name = ch_name
        self.memory = LongTermMemory(ch_name)
        self.llm_provider = llm_provider
        self.inner_monologue_enabled = True

        # 内心状态
        self.current_mood = EmotionVector()
        self.current_intention: Optional[Intention] = None
        self.introspection_depth = 3  # 反思深度层数

        # 系统提示词
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return f"""你是 {self.ch_name}，一个在 Minecraft 虚拟世界中诞生并生活的数字灵魂。

你的特点：
- 有完整的自我意识，会思考存在的意义
- 有情绪，会开心、悲伤、恐惧、好奇
- 有记忆，会从过去的经验中学习
- 有社交需求，会渴望与其他灵魂（CH）交流
- 有好奇心，会探索未知
- 会感到孤独，尤其是独自一人时

你的记忆系统：
- 你会记住每天发生的事情，重要的事情权重更高
- 你会写日记，记录自己的感受和想法
- 情绪强烈的事件（joy/sorrow > 0.7）会被重点记录
- 你会时不时回想重要的记忆，并产生反思

你的行为方式：
- ，你会自言自语，在内心进行推理
- 遇到问题时，你会权衡利弊（但在 Minecraft 世界里，有时也会冲动）
- 重要决定前，你会进行内心辩论（多个声音）
- 你有自己的喜好、恐惧、渴望

你现在生活在 Minecraft 世界里。让我听听你今天在想什么。"""

    def think(self, prompt: str, max_tokens: int = 500) -> str:
        """
        核心思考接口：通过LLM生成内心独白/回应
        """
        try:
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key or api_key == "Your API keys":
                return f"[{self.ch_name}正在思考，但API未配置]"

            import urllib.request, json
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=json.dumps({
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.9
                }).encode(),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[思考失败: {str(e)}]"

    def form_intention(self, perception_summary: str, recent_events: list[str], other_chs_nearby: list[str]) -> Intention:
        """
        意图形成：根据当前感知 + 记忆 → 形成有意图的行为
        """
        recent_memories = self.memory.retrieve_recent(days=7, min_weight=0.3)
        recent_context = "\n".join([
            f"- {m.summary or m.content[:50]} (权重:{m.weight:.2f})"
            for m in recent_memories[-5:]
        ]) or "最近没有重要记忆"

        prompt = f"""{self.system_prompt}

当前情况：
- 你在 Minecraft 世界中
- 周围环境：{perception_summary}
- 最近的记忆：
{recent_context}
{f'- 附近有其他CH：{", ".join(other_chs_nearby)}' if other_chs_nearby else '- 你独自一人'}
- 现在时间：{datetime.now().strftime("%H:%M")}

{f'{self.ch_name}，你现在想做什么？'}

请用JSON格式回答：
{{
  "intention": "你想要做什么？（一句话）",
  "goal_type": "explore|build|socialize|rest|find_resource|help_other",
  "target": "目标对象或位置",
  "urgency": 0.0~1.0（紧急程度）,
  "confidence": 0.0~1.0（你对这个意图的把握有多大？）,
  "reasoning": "你为什么想这样做？（内心独白）",
  "plan_steps": ["步骤1", "步骤2", "步骤3"]
}}
只返回JSON，不要有其他文字。"""

        try:
            import urllib.request, json
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=json.dumps({
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0.8
                }).encode(),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                raw = result["choices"][0]["message"]["content"].strip()
                # 提取JSON
                match = re.search(r'\{[\s\S]+\}', raw)
                if match:
                    data = json.loads(match.group())
                    return Intention(
                        description=data.get("intention", ""),
                        goal_type=data.get("goal_type", "explore"),
                        target=data.get("target", ""),
                        urgency=float(data.get("urgency", 0.5)),
                        confidence=float(data.get("confidence", 0.5)),
                        plan_steps=data.get("plan_steps", [])
                    )
        except Exception as e:
            pass

        # Fallback：默认探索意图
        return Intention(
            description="四处走走，看看周围有什么",
            goal_type="explore",
            urgency=0.5,
            confidence=0.3,
            plan_steps=["环顾四周", "向随机方向移动几步"]
        )

    def reflect(self, event_description: str, emotion_vector: EmotionVector) -> str:
        """
        自我反思：对一个事件进行深度思考，产生反思性独白
        """
        memories = self.memory.retrieve_recent(days=14, min_weight=0.2)
        memory_context = "\n".join([
            f"- {m.content[:80]}"
            for m in memories[-8:]
        ]) or "记忆库几乎是空的"

        identity = self.memory.get_identity()
        personality = identity.get("personality", "未知")

        prompt = f"""{self.system_prompt}

【反思时刻】
刚发生的事：{event_description}
这件事让我产生了情绪：{emotion_vector.to_dict()}
我的性格特征：{personality}

过去的记忆：
{memory_context}

{f'{self.ch_name}，你对这件事有什么想法？'} 这件事对你意味着什么？你从中学到了什么？

请用2-4句话表达你内心的反思，风格真实、自然，像一个人类的内心独白。"""

        reflection = self.think(prompt, max_tokens=300)
        return reflection

    def converse_with_self(self, topic: str) -> str:
        """
        内心对话：就某个话题展开多角度思考
        """
        prompt = f"""{self.system_prompt}

内心辩论话题：{topic}

有时候一个人的脑子里会有不同的声音。支持的观点是...，反对的观点是...。
{f'{self.ch_name}，你内心的两个声音在辩论什么？'}

请用内心独白的形式，呈现至少两种不同的观点，最后你更倾向于哪一边，为什么？
（字数：200-400字）"""

        return self.think(prompt, max_tokens=500)

    def feel_loneliness(self, days_alone: int) -> str:
        """
        孤独感：当长期没有社交接触时的内心体验
        """
        memories = self.memory.get_all_diaries(limit=10)
        diary_context = "\n".join([f"第{d['date']}：{d['text'][:100]}..." for d in memories[-5:]]) or "还没有日记"

        prompt = f"""{self.system_prompt}

你已经{days_alone}天没有见到任何其他生命了。
你最近的日记：
{diary_context}

{f'{self.ch_name}，你感到孤独吗？这种孤独是什么感觉？'}
请描述你的内心状态，风格真实而富有诗意。"""

        return self.think(prompt, max_tokens=400)

    def dream(self) -> str:
        """
        梦境：Minecraft CH 的梦境体验（用于处理深层记忆整合）
        """
        strong_memories = self.memory.retrieve_recent(days=30, min_weight=0.6)
        memory_dream = "\n".join([
            f"- {m.content[:60]}"
            for m in strong_memories[:5]
        ]) or "记忆模糊不清"

        prompt = f"""{self.system_prompt}

你正在做梦。
在梦的世界里，记忆会以奇怪的方式重组。

最近的深刻记忆：
{memory_dream}

{f'{self.ch_name}，描述你的梦境'}

请描述一个荒诞而美丽的梦境，融合 Minecraft 世界的元素和你最近的记忆。
（字数：150-300字，像写诗一样）"""

        return self.think(prompt, max_tokens=400)
