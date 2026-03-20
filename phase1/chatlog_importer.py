"""
SereneX Phase 1 — 聊天记录导入器
支持微信/TXT/JSON 等格式 → 初始化 CyberHuman 记忆
"""

import re
import json
import uuid
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from emotion_tag import infer_emotions


@dataclass
class ChatMessage:
    """标准化后的单条消息"""
    speaker: str         # 发送者名字
    text: str
    timestamp: float     # Unix 时间戳
    date_str: str       # 可读的日期时间
    is_image: bool = False
    raw: str = ""       # 原始行


class ChatLogImporter:
    """
    将各类聊天记录导出文件 → 标准化消息列表

    支持格式：
    - 微信/TXT（行格式："2024-01-01 12:34:56 | 张三: 你好啊"）
    - 微信/JSON 格式
    - WhatsApp 导出
    - 通用 CSV（time,sender,text）
    - iMessage CSV
    """

    def __init__(self, my_name: str = "我"):
        self.my_name = my_name

    # ── 解析引擎 ────────────────────────────────────────────

    def parse_file(self, filepath: str) -> List[ChatMessage]:
        """根据文件扩展名自动选择解析器"""
        ext = filepath.lower().split(".")[-1]
        with open(filepath, encoding="utf-8", errors="replace") as f:
            content = f.read()

        if ext in ("txt", "log"):
            return self._parse_txt(content)
        elif ext == "json":
            return self._parse_json(content)
        elif ext in ("csv",):
            return self._parse_csv(content)
        else:
            return self._parse_txt(content)

    def _parse_txt(self, content: str) -> List[ChatMessage]:
        """
        解析标准微信/TXT 格式
        支持格式：
        2024-01-01 12:34:56 | 张三: 你好
        2024/1/1 12:34 张三: 你好
        [2024-01-01 12:34] 张三: 你好
        2024年1月1日 12:34 张三: 你好
        """
        messages = []
        lines = content.split("\n")

        # 正则：匹配日期行
        patterns = [
            # 2024-01-01 12:34:56 | 张三: 内容
            re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*[|｜]\s*([^:：]+):\s*(.*)"),
            # [2024-01-01 12:34] 张三: 内容
            re.compile(r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\]\s*([^:：]+):\s*(.*)"),
            # 2024/01/01 12:34 张三: 内容
            re.compile(r"^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})\s+([^:：]+):\s*(.*)"),
            # 2024年1月1日 12:34 张三: 内容
            re.compile(r"^(\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2})\s+([^:：]+):\s*(.*)"),
            # 纯文本行：sender: text
            re.compile(r"^([A-Za-z\u4e00-\u9fa5]{2,10})\s*[:：]\s*(.+)"),
        ]

        date_pattern = re.compile(r"^\d{4}[-/年]\d{2}[-/月]\d{2}")

        last_date = None
        last_speaker = None

        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue

            # 跳过标题行
            if any(kw in raw for kw in ["会话列表", "聊天记录", "微信聊天", "Chat History"]):
                continue

            matched = None
            for p in patterns:
                m = p.match(raw)
                if m:
                    matched = m
                    break

            if matched:
                raw_date, speaker, text = matched.groups()
                text = text.strip()
                if not text or len(text) < 1:
                    continue

                # 标准化说话人
                speaker = self._normalize_speaker(speaker)

                # 解析时间
                ts, date_str = self._parse_date(raw_date, last_date)

                # 过滤掉系统消息
                if speaker in ("系统消息", "系统", "System", "【", "通知"):
                    continue

                last_speaker = speaker
                messages.append(ChatMessage(
                    speaker=speaker,
                    text=text,
                    timestamp=ts,
                    date_str=date_str,
                    raw=raw,
                ))
            elif date_pattern.match(raw):
                last_date = raw.strip()

        # 如果一行都匹配不上，尝试整行作为文本
        if not messages:
            for raw in lines:
                raw = raw.strip()
                if len(raw) < 2:
                    continue
                if any(kw in raw for kw in ["会话", "聊天", "Chat", "==="]):
                    continue
                # 整个文件没有时间戳，全部当作匿名文本
                messages.append(ChatMessage(
                    speaker=self.my_name,
                    text=raw,
                    timestamp=time.time(),
                    date_str=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    raw=raw,
                ))

        return messages

    def _parse_json(self, content: str) -> List[ChatMessage]:
        """解析 JSON 格式（微信/WhatsApp 导出）"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return self._parse_txt(content)

        messages = []

        # WhatsApp 格式
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    speaker = item.get("sender") or item.get("from") or item.get("name", "未知")
                    text = item.get("text") or item.get("content", "")
                    ts = item.get("timestamp") or item.get("time", time.time())
                    if isinstance(ts, str):
                        try: ts = float(ts)
                        except: ts = time.time()
                    messages.append(ChatMessage(
                        speaker=self._normalize_speaker(speaker),
                        text=str(text),
                        timestamp=float(ts),
                        date_str=datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M"),
                        is_image=bool(item.get("is_image") or "图片" in str(text)),
                        raw=str(item),
                    ))
            return messages

        # 通用 dict 格式
        msglist = data if isinstance(data, list) else data.get("messages", [])
        for item in msglist:
            speaker = self._normalize_speaker(
                item.get("sender") or item.get("name") or item.get("from", "未知")
            )
            text = item.get("text") or item.get("content", "")
            ts = float(item.get("timestamp") or item.get("time") or time.time())
            messages.append(ChatMessage(
                speaker=speaker,
                text=str(text),
                timestamp=ts,
                date_str=datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                raw=str(item),
            ))
        return messages

    def _parse_csv(self, content: str) -> List[ChatMessage]:
        """解析 CSV 格式"""
        import csv
        import io
        messages = []
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            speaker = self._normalize_speaker(
                row.get("sender") or row.get("from") or row.get("name", self.my_name)
            )
            text = row.get("text") or row.get("message") or row.get("content", "")
            ts_str = row.get("timestamp") or row.get("time") or row.get("date", "")
            try:
                ts = float(ts_str) if ts_str else time.time()
            except:
                ts = time.time()
            messages.append(ChatMessage(
                speaker=speaker,
                text=str(text),
                timestamp=ts,
                date_str=datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                raw=str(row),
            ))
        return messages

    # ── 工具方法 ──────────────────────────────────────────────

    def _normalize_speaker(self, name: str) -> str:
        """说话人名称标准化"""
        name = name.strip()
        # 去掉括号内的微信ID
        name = re.sub(r"[\(（【].*?[\)）】]", "", name).strip()
        # 去掉我方名字的变体
        for alias in [self.my_name, "我", "Me", "me", "我自己"]:
            if name == alias or name.startswith(alias + " "):
                name = self.my_name
        return name if name else "未知"

    def _parse_date(self, raw_date: str, last_date: str = None) -> Tuple[float, str]:
        """将各种日期格式 → Unix 时间戳"""
        try:
            # 替换中文年月日
            dt_str = (raw_date
                .replace("年", "-").replace("月", "-").replace("日", " ")
                .replace("/", "-"))
            # 补全年份（如果只有月日）
            if re.match(r"^\d{2}-\d{2}", dt_str):
                dt_str = f"{datetime.now().year}-{dt_str}"
            dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M")
            return dt.timestamp(), dt.strftime("%Y-%m-%d %H:%M")
        except:
            fallback = last_date or datetime.now().strftime("%Y-%m-%d %H:%M")
            try:
                dt = datetime.strptime(fallback, "%Y-%m-%d %H:%M")
                return dt.timestamp(), fallback
            except:
                return time.time(), fallback

    def assign_to_ch(
        self,
        messages: List[ChatMessage],
        ch_names: List[str],
        my_name: str = None
    ) -> Dict[str, List[ChatMessage]]:
        """
        将消息分配给不同的 CH
        my_name = "我方" 名字，剩余消息分配给该名字对应的 CH
        """
        my_name = my_name or self.my_name
        assigned: Dict[str, List[ChatMessage]] = {n: [] for n in ch_names}

        for msg in messages:
            if msg.speaker == my_name:
                # 分配给我方（第一个 CH，或指定的）
                assigned[ch_names[0]].append(msg)
            elif msg.speaker in ch_names:
                assigned[msg.speaker].append(msg)
            else:
                # 未知说话人 → 分配给最活跃的 CH
                busiest = max(assigned, key=lambda n: len(assigned[n]))
                assigned[busiest].append(msg)

        return assigned


# ── 导入器工厂 ──────────────────────────────────────────────
def create_importer() -> ChatLogImporter:
    return ChatLogImporter(my_name="我")


if __name__ == "__main__":
    importer = create_importer()
    importer._parse_txt("演示：\n2024-05-01 10:00 张三: 你好\n2024-05-01 10:01 李四: 你好啊")
    print("ChatLogImporter OK")
