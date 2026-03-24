# SereneX Phase 3 — 文明演化沙盒

> 从两个灵魂到一座城邦

## 核心设定

- **起点**：亚当（Adam）+ 伊娃（Eve），Minecraft 出生点
- **载体**：纯虚拟 Avatar，Mineflayer API 控制
- **记忆格式**：纯文本 JSON，每日日记
- **演化路线**：个体 → 聚落 → 部落 → 城邦 → 国家 → 文明
- **LLM**：DeepSeek（.env 配置）
- **环境**：Minecraft（Mineflayer Node.js）

## 目录结构

```
phase3/
├── consciousness/       意识核心（意图/反思/内心独白）
├── minecraft/           Minecraft 世界接口
├── memory/              长期记忆系统
│   ├── adam/           亚当的记忆
│   └── eve/            伊娃的记忆
├── agents/              Cyber Human agent
├── simulation/          文明演化引擎
└── tools/               共享工具
```

## CH 每日循环

1. 感知阶段 → 扫描周围（视觉+听觉+触觉）
2. 意识阶段 → 内心独白 + 自我反思
3. 规划阶段 → 形成意图 → 动作序列
4. 执行阶段 → Mineflayer 操作
5. 反馈阶段 → 感知结果
6. 情绪阶段 → 评估体验
7. 日记阶段 → LLM生成日记 → 写入 memory/

## 情绪权重

```
weight = base_emotion_score * recency_decay * reinforcement

- joy/sorrow强度 → 权重0.8~1.0
- 日常体验 → 权重0.1~0.3
- 重要事件（发现/冲突/合作）→ 权重0.6~0.8
```

## 演化里程碑

- Day 1~10：个体生存，搭建庇护所
- Day 10~30：两人形成合作关系，建造工具
- Day 30~60：第一个聚落（3~5人）
- Day 60~180：部落形成，引入更多CH
- Day 180~365：城邦雏形，分工出现
- Day 365+：城市、国家、贸易、文化
