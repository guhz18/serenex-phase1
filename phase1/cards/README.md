# CH Cards — 可移植 Cyber Human 卡片

存放从网页/社交媒体生成的 CH 卡片（JSON 格式）。

## 文件

- `*.json` — 可移植的 CH 卡片文件
- `UCL_Research_Assistant.json` — 示例卡片

## 使用方法

```bash
# 从网页生成卡片
python3 ../ch_cli.py gen "https://your-page.com" --name "YourName"

# 列出所有卡片
python3 ../ch_cli.py list

# 查看卡片详情
python3 ../ch_cli.py show your_card.json

# 在代码中加载
from ch_card import CHCard
card = CHCard.load("your_card.json")
ch = CyberHuman(**card.to_cyber_human_kwargs())
```

## 卡片字段说明

| 字段 | 说明 |
|------|------|
| `name` | CH 名字 |
| `source_url` | 内容来源 URL |
| `mbti` | 推断的 MBTI 类型 |
| `big_five` | O-C-E-A-N 五大人格分数 |
| `role_type` | 角色类型（developer/academic/blogger/...） |
| `persona_description` | 供 LLM 使用的人物描述 |
| `memory_snippets` | 从内容提取的关键记忆片段 |
| `writing_style` | 写作风格参数 |
| `relations` | 与其他 CH 的初始关系分 |

## 跨机器分发

1. 拷贝 `cards/<name>.json` 到目标机器的 `phase1/cards/` 目录
2. 运行 `python3 ch_cli.py load <name>.json` 查看导入代码
3. 用 `CHCard.load()` 加载并初始化 CyberHuman
