"""
SereneX — CH Card 生成器
将任意 UCL 网页内容 → 生成可移植的 Cyber Human 卡片（JSON）
"""

import os, json, time
from dataclasses import dataclass, asdict
from pathlib import Path

# 沙盒基础路径
CARDS_DIR = Path(__file__).parent / "cards"
CARDS_DIR.mkdir(exist_ok=True)


@dataclass
class CHCard:
    """Cyber Human 卡片 — 可序列化、可拷贝"""
    version: str = "1.0"
    created_at: str = ""

    # 身份
    name: str = ""
    source_url: str = ""
    source_title: str = ""
    description: str = ""

    # 性格（MBTI + Big Five）
    mbti: str = ""
    big_five: dict = None  # {O C E A N}

    # 角色定位
    persona_description: str = ""
    role_type: str = ""   # blogger / academic / developer / designer / ...

    # 写作风格
    writing_style: dict = None

    # 记忆片段（从内容提取的关键信息）
    memory_snippets: list = None  # ["在 UCL 学习 AI", "喜欢 research", ...]

    # 情绪标签
    emotion_tags: list = None

    # 关系预设（与其他 CH 的初始关系分）
    relations: dict = None  # {"other_ch_id": 0.3}

    def __post_init__(self):
        if self.big_five is None:
            self.big_five = {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}
        if self.writing_style is None:
            self.writing_style = {}
        if self.memory_snippets is None:
            self.memory_snippets = []
        if self.emotion_tags is None:
            self.emotion_tags = []
        if self.relations is None:
            self.relations = {}
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def save(self, filename: str = None) -> Path:
        if filename is None:
            # 用 name 生成安全文件名
            safe = self.name.replace(" ", "_") if self.name else "unknown"
            filename = f"{safe}_{int(time.time())}.json"
        path = CARDS_DIR / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str) -> "CHCard":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_cyber_human_kwargs(self) -> dict:
        """导出为 cyber_human.CyberHuman 的构造参数"""
        return {
            "name": self.name,
            "user_id": f"ch_{self.name}_{int(time.time())}",
        }
