"""
SereneX Phase 3 — 感知系统（Senses）
视觉：截图 → LLM图像理解 → 场景描述
听觉：声音事件 → LLM理解 → 声音描述
触觉：方块/实体交互事件 → 解析 → 触觉描述

注意：截图存在时使用 DeepSeek API 做视觉理解；不存在时使用模拟感知。
"""
import os
import re
import json
import base64
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from memory import MemoryEntry, new_memory_id, calc_emotion_weight, EmotionVector
from datetime import datetime


@dataclass
class SenseInput:
    sensory_type: str  # visual | auditory | tactile
    raw_data: str
    context: str = ""
    timestamp: str = ""


@dataclass
class SenseOutput:
    description: str
    sensory_type: str = "internal"
    emotion_shift: dict = field(default_factory=lambda: {"calm": 0.5})
    tags: list = field(default_factory=list)
    importance: float = 0.5


# ── DeepSeek 视觉理解 ──────────────────────────────────────

def _call_deepseek_vision(screenshot_path: str, prompt: str, location: str = "", nearby: str = "") -> str:
    """
    调用 DeepSeek Chat API 对截图进行视觉理解
    （支持 base64 编码图片）
    """
    try:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key or api_key == "Your API keys":
            return ""

        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        full_prompt = (
            f"{prompt}\n\n"
            f"当前位置：{location}\n"
            f"{nearby}"
        )

        body = {
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ]
            }],
            "max_tokens": 300,
            "temperature": 0.8
        }

        import urllib.request
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


# ── 感知基类 ──────────────────────────────────────────────

class PerceptionSystem:
    """CH 的感知系统：将 Minecraft 世界的信息转化为可记忆的体验"""

    def __init__(self, ch_name: str):
        self.ch_name = ch_name
        self.vision_prompt = (
            "你是一个有意识的观察者，描述你看到的内容。"
            "这个场景发生在 Minecraft 虚拟世界中。"
            "请用一句话描述：你在哪里？看到了什么？有什么让你印象深刻？"
            "然后列出你注意到的物体、生物、环境细节。"
        )

    def see(self, screenshot_path: str, location: str = "", nearby_chs: list = None) -> SenseOutput:
        """视觉感知：截图 → LLM理解 → 场景描述"""
        nearby = f"附近有：{', '.join(nearby_chs)}" if nearby_chs else "附近没有人"

        # 有截图 → 调用 API
        if screenshot_path and Path(screenshot_path).exists():
            raw = _call_deepseek_vision(
                screenshot_path,
                self.vision_prompt,
                location=location,
                nearby=nearby
            )
            if raw:
                return self._parse_vision_output(raw, has_ch=bool(nearby_chs))

        # 无截图或 API 失败 → 模拟感知
        return self._simulate_see(location, nearby_chs)

    def _parse_vision_output(self, text: str, has_ch: bool = False) -> SenseOutput:
        """解析 LLM 视觉输出"""
        lines = text.strip().split("\n")
        description = lines[0] if lines else "什么都没看到"

        emotion = {"joy": 0.0, "sorrow": 0.0, "surprise": 0.0, "curiosity": 0.5, "calm": 0.5, "fear": 0.0}
        importance = 0.5
        tags = []

        for line in lines[1:]:
            lo = line.lower().strip()
            if "情绪" in line or "emotion" in lo:
                match = re.search(r'\{[^}]+\}', line)
                if match:
                    try:
                        parsed = json.loads(match.group())
                        for k, v in parsed.items():
                            if k in emotion:
                                emotion[k] = float(v)
                    except Exception:
                        pass
            elif "重要性" in line or "importance" in lo:
                m = re.search(r'0?\.?\d+', line)
                if m:
                    importance = float(m.group())
            elif "标签" in line or "tag" in lo:
                tags = [t.strip() for t in re.split(r'[,，、]', line) if t.strip()]
                if tags and ("标" in line or "tag" in lo):
                    tags = tags[1:]

        if has_ch:
            emotion["curiosity"] = max(emotion.get("curiosity", 0), 0.5)

        return SenseOutput(
            description=description,
            sensory_type="visual",
            emotion_shift=emotion,
            tags=tags,
            importance=importance
        )

    def _simulate_see(self, location: str, nearby_chs: list) -> SenseOutput:
        """无截图时的模拟视觉感知"""
        if nearby_chs:
            desc = f"我看到{', '.join(nearby_chs[:2])}，这个世界有人陪伴真好。"
            emo = {"joy": 0.5, "curiosity": 0.4}
        elif "森林" in location:
            desc = "阳光透过树叶的缝隙洒落，周围是静谧的树林。"
            emo = {"calm": 0.6, "curiosity": 0.3}
        elif "平原" in location:
            desc = "广阔的天空下，是一望无际的草地，风吹过的时候有种自由的感觉。"
            emo = {"calm": 0.5, "joy": 0.3}
        elif "水域" in location:
            desc = "波光粼粼的水面，偶尔有鱼儿跃出水面。"
            emo = {"calm": 0.7, "surprise": 0.2}
        elif "山地" in location:
            desc = "险峻的山崖和岩石，视野开阔，但需要小心脚下。"
            emo = {"curiosity": 0.4, "fear": 0.2}
        else:
            desc = "我站在这里，感受着 Minecraft 世界的气息，周遭安静而神秘。"
            emo = {"calm": 0.5, "curiosity": 0.3}

        return SenseOutput(
            description=desc,
            sensory_type="visual",
            emotion_shift=emo,
            tags=["simulated", "visual"],
            importance=0.5
        )

    def hear(self, sound_event: str, source_direction: str = "") -> SenseOutput:
        """听觉感知"""
        event_emotions = {
            "下雨": {"calm": 0.7, "sorrow": 0.1},
            "牛": {"joy": 0.2, "calm": 0.5},
            "羊": {"calm": 0.5, "joy": 0.1},
            "猪": {"calm": 0.4},
            "苦力怕": {"fear": 0.7, "surprise": 0.5},
            "僵尸": {"fear": 0.8, "surprise": 0.3},
            "骷髅": {"fear": 0.6},
            "爆炸": {"surprise": 0.8, "fear": 0.4},
            "村民": {"curiosity": 0.5, "joy": 0.2},
            "脚步声": {"surprise": 0.3},
            "风声": {"calm": 0.4},
            "水声": {"calm": 0.6},
        }

        emotion = {k: 0.0 for k in ("joy", "sorrow", "fear", "surprise", "curiosity", "calm")}
        for keyword, emo in event_emotions.items():
            if keyword in sound_event:
                for k, v in emo.items():
                    emotion[k] = max(emotion[k], v)

        emotion.setdefault("calm", 0.5)
        return SenseOutput(
            description=f"听到：{sound_event}" + (f"（来自{source_direction}）" if source_direction else ""),
            sensory_type="auditory",
            emotion_shift=emotion,
            tags=[sound_event],
            importance=0.4
        )

    def touch(self, block_type: str, action: str = "") -> SenseOutput:
        """触觉感知"""
        tactile_data = {
            "树": {"description": "粗糙的树皮，指尖感受到木质的纹理", "emotion": {"calm": 0.4, "curiosity": 0.3}},
            "水": {"description": "清凉的水流穿过手指，波纹荡漾", "emotion": {"calm": 0.7, "surprise": 0.1}},
            "岩浆": {"description": "炽热灼烧，极度危险！", "emotion": {"fear": 0.9, "surprise": 0.8}},
            "石头": {"description": "冰冷的石头，坚硬而沉重", "emotion": {"calm": 0.3, "curiosity": 0.2}},
            "羊毛": {"description": "柔软的羊毛，温暖舒适", "emotion": {"joy": 0.5, "calm": 0.5}},
            "泥土": {"description": "松软的泥土，有些湿润", "emotion": {"calm": 0.4, "curiosity": 0.2}},
            "铁": {"description": "冰凉的金属，表面光滑", "emotion": {"curiosity": 0.4}},
            "火": {"description": "炽热的火焰，极度危险", "emotion": {"fear": 0.8, "surprise": 0.7}},
            "雪": {"description": "冰冷的雪花，手心微微发凉", "emotion": {"surprise": 0.4, "calm": 0.3}},
            "沙": {"description": "细软的沙子，从指缝间流下", "emotion": {"calm": 0.5, "curiosity": 0.3}},
        }

        for keyword, data in tactile_data.items():
            if keyword in block_type:
                return SenseOutput(
                    description=f"触摸{block_type}：{data['description']}",
                    sensory_type="tactile",
                    emotion_shift=data["emotion"],
                    tags=["触摸", keyword],
                    importance=0.3
                )

        return SenseOutput(
            description=f"触摸了{block_type}（{action}）",
            sensory_type="tactile",
            emotion_shift={"curiosity": 0.4, "calm": 0.3},
            tags=["触摸", "未知"],
            importance=0.2
        )


# ── Senses 整合类（供 agent.py 调用）────────────────────────

class Senses:
    """
    感知系统整合接口
    agent.py 调用入口
    """

    def __init__(self, ch_name: str):
        self.ch_name = ch_name
        self.perception = PerceptionSystem(ch_name)

    def perceive_world(
        self,
        screenshot_path: str = "",
        location: str = "",
        nearby_chs: list = None,
    ) -> SenseOutput:
        """
        主感知入口：整合视觉 + 模拟环境感知
        """
        if nearby_chs is None:
            nearby_chs = []

        # 视觉感知（截图或模拟）
        visual = self.perception.see(screenshot_path, location, nearby_chs)

        # 如果没有其他 CH，进行一些随机的环境感知
        if not nearby_chs and visual.description != "[无视觉数据]":
            import random
            possible_touches = ["树", "水", "石头", "泥土", "草"]
            touche = random.choice(possible_touches)
            tactile = self.perception.touch(touche)
            # 合并描述
            combined = (
                f"{visual.description} "
                f"我还触摸到了{random.choice(['脚下的草地', '旁边的树木', '周围的空气'])}。"
            )
            visual.description = combined
            # 情绪取平均
            merged = dict(visual.emotion_shift)
            for k, v in tactile.emotion_shift.items():
                merged[k] = (merged.get(k, 0.5) + v) / 2

        return visual
