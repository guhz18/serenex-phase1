"""
SereneX Phase 3 — 感知系统（Senses）
视觉：截图 → LLM图像理解 → 场景描述
听觉：声音事件 → LLM理解 → 声音描述
触觉：方块/实体交互事件 → 解析 → 触觉描述
"""
import base64
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from images_understand import images_understand
from memory import MemoryEntry, new_memory_id, calc_emotion_weight, EmotionVector
from datetime import datetime


@dataclass
class SenseInput:
    sensory_type: str           # visual | auditory | tactile
    raw_data: str               # 截图路径 / 声音描述 / 触觉事件
    context: str = ""           # 额外上下文（位置、时间等）
    timestamp: str = ""


@dataclass
class SenseOutput:
    description: str             # 感知到的内容（自然语言描述）
    emotion_shift: dict         # 这条感知带来的情绪变化
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5     # 重要性 0.0~1.0（是否值得写入记忆）


class PerceptionSystem:
    """
    CH 的感知系统：将 Minecraft 世界的信息转化为可记忆的体验
    """

    def __init__(self, ch_name: str):
        self.ch_name = ch_name
        self.vision_prompt = (
            "你是一个有意识的观察者，描述你看到的内容。"
            "注意：这个场景发生在 Minecraft 虚拟世界中。"
            "请用一句话描述：你在哪里？看到了什么？有什么让你印象深刻？"
            "然后列出你注意到的物体、生物、环境细节。"
        )

    def see(self, screenshot_path: str, location: str = "", nearby_chs: list[str] = None) -> SenseOutput:
        """
        视觉感知：截图 → LLM理解 → 场景描述
        """
        if not Path(screenshot_path).exists():
            return SenseOutput(
                description="[无视觉数据]",
                emotion_shift={"calm": 0.5},
                tags=["未知"]
            )

        nearby = f"附近有：{', '.join(nearby_chs)}" if nearby_chs else "附近没有人"

        try:
            result = images_understand([{
                "file": screenshot_path,
                "prompt": (
                    f"{self.vision_prompt}\n\n"
                    f"当前位置：{location}\n"
                    f"{nearby}\n\n"
                    f"请描述你看到的内容，并判断这场景让你产生什么情绪（joy/sorrow/surprise/curiosity）。"
                    f"返回格式：描述【一行】；情绪【JSON格式如{{'joy':0.8,'surprise':0.3}}】；重要性【0~1】；标签【逗号分隔】"
                )
            }])
            text = result[0]["text"] if isinstance(result, list) else result.get("text", "")

            # 解析LLM输出
            description, emotion, importance, tags = self._parse_vision_output(text)

            # 如果有其他CH在场，增加社交情绪
            if nearby_chs:
                emotion["curiosity"] = max(emotion.get("curiosity", 0), 0.5)

            return SenseOutput(
                description=description,
                emotion_shift=emotion,
                tags=tags,
                importance=importance
            )

        except Exception as e:
            return SenseOutput(
                description=f"[视觉处理失败: {str(e)}]",
                emotion_shift={"calm": 0.5},
                tags=["错误"]
            )

    def _parse_vision_output(self, text: str) -> tuple[str, dict, float, list[str]]:
        """解析LLM的视觉输出"""
        lines = text.strip().split("\n")

        # 提取描述（第一行非结构化文字）
        description = lines[0] if lines else "什么都没看到"

        emotion = {"joy": 0.0, "sorrow": 0.0, "surprise": 0.0, "curiosity": 0.5, "calm": 0.5}
        importance = 0.5
        tags = []

        for line in lines[1:]:
            line_lower = line.lower().strip()
            if "情绪" in line or "emotion" in line_lower:
                # 尝试提取JSON情绪
                import re, json
                match = re.search(r'\{[^}]+\}', line)
                if match:
                    try:
                        parsed = json.loads(match.group())
                        for k, v in parsed.items():
                            if k in emotion:
                                emotion[k] = float(v)
                    except:
                        pass
            elif "重要性" in line or "importance" in line_lower:
                try:
                    importance = float(re.search(r'0?\.?\d+', line).group())
                except:
                    importance = 0.5
            elif "标签" in line or "tag" in line_lower:
                tags = [t.strip() for t in re.split(r'[,，、]', line) if t.strip()]
                tags = tags[1:] if tags else []

        return description, emotion, importance, tags

    def hear(self, sound_event: str, source_direction: str = "") -> SenseOutput:
        """
        听觉感知：解析声音事件
        sound_event 例如："生物发出叫声"、"脚步声"、"下雨"等
        """
        event_emotions = {
            "下雨": {"calm": 0.7, "sorrow": 0.1},
            "牛叫": {"joy": 0.2, "calm": 0.5},
            "羊叫": {"calm": 0.5, "joy": 0.1},
            "猪叫": {"calm": 0.4},
            "苦力怕": {"fear": 0.7, "surprise": 0.5},
            "僵尸": {"fear": 0.8, "surprise": 0.3},
            "骷髅": {"fear": 0.6},
            "爆炸": {"surprise": 0.8, "fear": 0.4},
            "村民": {"curiosity": 0.5, "joy": 0.2},
            "另一个CH": {"curiosity": 0.6, "surprise": 0.3, "joy": 0.1},
            "脚步声": {"surprise": 0.2},
            "风声": {"calm": 0.4},
            "水声": {"calm": 0.6},
        }

        emotion = {"joy": 0.0, "sorrow": 0.0, "fear": 0.0, "surprise": 0.0, "curiosity": 0.5, "calm": 0.5}
        for keyword, emo in event_emotions.items():
            if keyword in sound_event:
                for k, v in emo.items():
                    emotion[k] = max(emotion[k], v)

        return SenseOutput(
            description=f"听到：{sound_event}" + (f"（来自{source_direction}）" if source_direction else ""),
            emotion_shift=emotion,
            tags=[sound_event],
            importance=0.4
        )

    def touch(self, block_type: str, action: str, location: str = "") -> SenseOutput:
        """
        触觉感知：方块交互
        例如：触摸树木（获取树木信息）、触碰水（凉爽）、触碰岩浆（灼热）
        """
        tactile_data = {
            "树木": {"description": "粗糙的树皮，指尖感受到木质的纹理", "emotion": {"calm": 0.4, "curiosity": 0.3}},
            "水": {"description": "清凉的水流穿过手指，波纹荡漾", "emotion": {"calm": 0.7, "surprise": 0.1}},
            "岩浆": {"description": "炽热灼烧，温度极高！危险！", "emotion": {"fear": 0.9, "surprise": 0.8}},
            "石头": {"description": "冰冷的石头，坚硬而沉重", "emotion": {"calm": 0.3, "curiosity": 0.2}},
            "羊毛": {"description": "柔软的羊毛，温暖舒适", "emotion": {"joy": 0.5, "calm": 0.5}},
            "泥土": {"description": "松软的泥土，有些湿润", "emotion": {"calm": 0.4, "curiosity": 0.2}},
            "铁": {"description": "冰凉的金属，表面光滑", "emotion": {"curiosity": 0.4, "surprise": 0.2}},
            "火": {"description": "炽热的火焰，极度危险", "emotion": {"fear": 0.8, "surprise": 0.7}},
            "雪": {"description": "冰冷的雪花，手心微微发凉", "emotion": {"surprise": 0.4, "calm": 0.3}},
            "沙": {"description": "细软的沙子，从指缝间流下", "emotion": {"calm": 0.5, "curiosity": 0.3}},
        }

        for keyword, data in tactile_data.items():
            if keyword in block_type:
                return SenseOutput(
                    description=f"触摸{block_type}：{data['description']}",
                    emotion_shift=data["emotion"],
                    tags=["触摸", keyword],
                    importance=0.3
                )

        return SenseOutput(
            description=f"触摸了{block_type}（{action}）",
            emotion_shift={"curiosity": 0.4, "calm": 0.3},
            tags=["触摸", "未知"],
            importance=0.2
        )

    def sense_internal(self, thought: str) -> SenseOutput:
        """
        内部感知：内心想法、反思
        """
        return SenseOutput(
            description=f"内心想法：{thought}",
            emotion_shift={"calm": 0.5, "curiosity": 0.3},
            tags=["内心"],
            importance=0.6
        )
