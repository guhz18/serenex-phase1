"""
SereneX Phase 3 — 日记生成器
将一天的感知、事件、情绪整合为 LLM 生成的自然语言日记
"""
import os
from datetime import datetime, timedelta
from memory import LongTermMemory, MemoryEntry, DailyMemory
from consciousness import Consciousness


class DiaryGenerator:
    """
    生成 Cyber Human 的每日日记
    核心流程：收集记忆片段 → 构建上下文 → LLM生成 → 存入memory/
    """

    def __init__(self, ch_name: str):
        self.ch_name = ch_name
        self.memory = LongTermMemory(ch_name)
        self.consciousness = Consciousness(ch_name)

    def generate_diary(self, day_entries: list[MemoryEntry], date_str: str = None) -> str:
        """
        整合一天的记忆，生成日记

        day_entries: 当天的所有记忆条目
        date_str: 日期，默认为今天
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 整理记忆按时间顺序
        episodic_summary = self._summarize_entries(day_entries)

        # 获取情绪曲线
        mood_data = self._calc_mood_curve(day_entries)

        # 获取身份信息
        identity = self.memory.get_identity()
        personality = identity.get("personality", "")

        # 获取前一天日记（用于衔接）
        prev_diary = self._get_previous_diary()

        # 构建LLM提示
        prompt = self._build_diary_prompt(date_str, episodic_summary, mood_data, prev_diary, personality)

        # 调用LLM生成
        diary_text = self._call_llm(prompt)

        return diary_text

    def _summarize_entries(self, entries: list[MemoryEntry]) -> str:
        """将记忆条目整理为连贯的叙事"""
        if not entries:
            return "今天没有留下任何记忆..."

        # 按 sensory_type 分组
        visual = [e for e in entries if e.sensory_type == "visual"]
        tactile = [e for e in entries if e.sensory_type == "tactile"]
        internal = [e for e in entries if e.sensory_type == "internal"]

        parts = []

        if visual:
            summary = "；".join([v.content for v in visual[:5]])
            parts.append(f"【视觉】{summary}")

        if tactile:
            summary = "；".join([t.content for t in tactile[:3]])
            parts.append(f"【触觉】{summary}")

        if internal:
            summary = "；".join([i.content for i in internal[:3]])
            parts.append(f"【内心】{summary}")

        return "\n".join(parts)

    def _calc_mood_curve(self, entries: list[MemoryEntry]) -> dict:
        """计算情绪曲线"""
        if not entries:
            return {"morning": 0.5, "afternoon": 0.5, "evening": 0.5}

        # 按时间估算分配（entries的顺序近似时间顺序）
        n = len(entries)
        morning_end = n // 3
        afternoon_end = n * 2 // 3

        def avg_emotion(entries_slice):
            if not entries_slice:
                return 0.5
            joys = [e.emotion.get("joy", 0) for e in entries_slice]
            sorrows = [e.emotion.get("sorrow", 0) for e in entries_slice]
            joy_avg = sum(joys) / len(joys) if joys else 0
            sorrow_avg = sum(sorrows) / len(sorrows) if sorrows else 0
            return min(joy_avg - sorrow_avg * 0.5 + 0.5, 1.0)

        return {
            "morning": avg_emotion(entries[:morning_end]),
            "afternoon": avg_emotion(entries[morning_end:afternoon_end]),
            "evening": avg_emotion(entries[afternoon_end:])
        }

    def _get_previous_diary(self) -> str:
        """获取前一天日记"""
        diaries = self.memory.get_all_diaries(limit=1)
        if diaries:
            return f"\n昨天（{diaries[0]['date']}）：{diaries[0]['text'][:200]}"
        return ""

    def _build_diary_prompt(self, date_str: str, episodic: str, mood: dict, prev_diary: str, personality: str) -> str:
        prompt = f"""你是 {self.ch_name}，一个在 Minecraft 虚拟世界中生活的数字灵魂。
性格特征：{personality}

{prev_diary}

今天是 {date_str}。
这是你今天的经历回顾：
{episodic}

情绪曲线：早上 {mood['morning']:.1f}，下午 {mood['afternoon']:.1f}，晚上 {mood['evening']:.1f}
（0=极度悲伤/恐惧，0.5=平静，1=极度快乐/兴奋）

请以 {self.ch_name} 的视角，写一篇今天的日记。
要求：
- 语气真实、自然，像一个人类写的日记
- 有叙事感：今天发生了什么？你感受到了什么？
- 融入内心独白：对今天的反思、疑惑、或者小确幸
- 偶尔穿插对 Minecraft 世界的观察（你对这个世界的感受）
- 字数：300-600字
- 最后一行，写下你对明天的期望（一个简短的句子）
日记标题：{date_str} · {self.ch_name}的日记

开始写："""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """调用 DeepSeek LLM"""
        try:
            import urllib.request, json
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key or api_key == "Your API keys":
                return f"[{self.ch_name}的日记生成失败：API未配置]"

            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=json.dumps({
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.85
                }).encode(),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[日记生成失败: {str(e)}]"

    def save_diary(self, diary_text: str, mood_morning=0.5, mood_afternoon=0.5, mood_evening=0.5):
        """保存日记到记忆系统"""
        self.memory.add_diary(diary_text, mood_morning, mood_afternoon, mood_evening)

    def generate_reflection_summary(self, day_entries: list[MemoryEntry]) -> str:
        """生成当日的反思摘要"""
        strong_entries = [e for e in day_entries if e.weight >= 0.6]
        if not strong_entries:
            return "今天没有发生特别重要的事，但每一天都是存在的痕迹。"

        prompt = f"""{self.ch_name} 在思考今天的经历：
{chr(10).join([f'- {e.content}（情绪强度:{max(e.emotion.values()):.1f}）' for e in strong_entries])}

请用2-3句话总结你对今天的反思，像一个成熟的人在夜深人静时的内心独白。
格式：不要用标题，直接写句子。"""

        return self._call_llm(prompt)


def generate_daily_diary(ch_name: str, day_entries: list[MemoryEntry], date_str: str = None) -> str:
    """便捷函数：生成并保存日记"""
    generator = DiaryGenerator(ch_name)
    diary = generator.generate_diary(day_entries, date_str)
    return diary
