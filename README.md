# SereneX Phase 2 — Game Sandbox

> AI社群模拟 · DeepSeek LLM驱动 · 交互式CLI + Web仪表盘

**项目地址**：https://github.com/guhz18/serenex-phase1  
**分支**：`phase2`（基于 `phase1` 构建）

---

## 一、项目概述

SereneX Phase 2 在 Phase 1 的 ChatSandbox 基础上叠加了**游戏世界框架**，将多个 AI 角色（CH）从纯对话智能体扩展为具有生活轨迹、情感需求和社交目标的模拟个体。

**核心玩法**：玩家作为"上帝视角"的观察者+干预者，管理一个由 4 个 AI 角色组成的小社群，看它们在游戏世界中自主生活、社交、成长，同时可以随时介入发消息、调动角色或触发事件。

---

## 二、架构设计

```
SereneX/
├── phase1/          # Phase 1：对话引擎（ChatSandbox + CyberHuman）
│   ├── cyber_human.py      # AI角色核心定义
│   ├── chat_sandbox.py     # 聊天沙盒（继承自Phase1）
│   ├── llm_interface.py    # DeepSeek LLM接口
│   ├── personality.py      # MBTI人格系统
│   ├── memory_system.py    # 长期记忆
│   └── ...
│
└── phase2/         # Phase 2：Game Sandbox（新增）
    ├── game_world.py       # 游戏世界（时间/地点/事件）
    ├── needs_system.py     # 需求系统（能量/心情/社交）
    ├── quest_system.py     # 任务系统（每日任务/成就）
    ├── game_sandbox.py     # 核心GameSandbox类
    ├── game_cli.py         # 交互式CLI（彩色UI）
    ├── game_dashboard.py   # Web仪表盘（Flask 端口5002）
    ├── run_game.py         # 快速演示（自动跑10轮）
    └── README.md           # 本文档
```

---

## 三、游戏机制详解

### 3.1 时间系统

- 每 `tick()` = 游戏内 **1 小时**
- 24 小时日夜循环（`game_world.py` TIME_SLOTS）
- 凌晨（23:00~6:00）强制回家休息
- 每天 8:00 重置每日任务

### 3.2 地点系统

| 地点 | 中文名 | 适合活动 |
|------|--------|---------|
| `home` | 家 | 休息、居家聊天 |
| `park` | 公园 | 散步、户外聊天、锻炼 |
| `cafe` | 咖啡馆 | 室内聊天、深度对话、工作 |
| `office` | 办公室 | 工作、会议 |
| `mall` | 商场 | 购物、吃饭、社交 |
| `library` | 图书馆 | 阅读、独处、工作 |

### 3.3 需求系统（NeedsSystem）

每个 CH 有 3 个核心需求，数值 0.0~1.0，随时间自然消耗：

| 需求 | 消耗率/tick | 危急阈值 | 补充途径 |
|------|------------|---------|---------|
| ⚡ 能量 | 0.06 | < 0.25 | rest +0.35, eat +0.10 |
| 😊 心情 | 0.04 | < 0.25 | chat +0.10, exercise +0.08 |
| 💬 社交 | 0.05 | < 0.25 | chat +0.15 |

**行为决策优先级**：
1. 能量危急 → 强制回家休息
2. 心情危急 → 去咖啡馆/公园散心
3. 工作时间（8~18点）→ 30%概率去办公室
4. 下午茶（14~16点）→ 50%概率去咖啡馆
5. 傍晚（18~20点）→ 50%概率去公园散步
6. 随机探索新地点（每CH每2天一次）

### 3.4 任务系统（QuestSystem）

**每日任务**（每天 8:00 自动刷新 2 个）：

| 任务ID | 标题 | 条件 | 奖励 |
|--------|------|------|------|
| `q_daily_chat_2` | 社交达人 | 任意2位CH聊天1次 | 社交值+0.2 |
| `q_daily_group` | 三人聚会 | 3个CH同地点 | 全员心情+0.15 |
| `q_daily_explore` | 探索者 | 任意CH去新地点 | 能量+0.1 |
| `q_daily_deep` | 深度对话 | 指定2位CH聊3轮以上 | 关系+0.15 |

**玩家自定义任务**：通过 `quest add` 命令创建

### 3.5 关系系统

- 关系值 0.0~1.0，初始 0.20~0.45（随机）
- 每次聊天后：正面情绪 +0.05~0.10，负面情绪 -0.03
- 3轮无互动：关系缓慢衰减（每tick -0.008）

### 3.6 DeepSeek LLM 集成

当同地点有 ≥2 个 CH 时，自动触发真实对话：

```
CH_A → DeepSeek API → 生成回复（考虑MBTI、情绪、场景）
CH_B → DeepSeek API → 生成回复
↓
存入记忆 → 更新关系值 → 触发任务检测
```

---

## 四、CLI 命令参考

```bash
cd /workspace/SereneX/phase2
python3 game_cli.py
```

| 命令 | 示例 | 说明 |
|------|------|------|
| `tick [N]` | `tick 5` | 运行 N 轮（1~20）|
| `status` / `st` | `st` | 显示完整状态 |
| `go <CH> <地点>` | `go 小明 cafe` | 移动角色 |
| `msg <CH> <内容>` | `msg 小明 今天开心吗？` | 私信角色 |
| `broadcast <内容>` | `broadcast 大家晚安` | 广播给所有人 |
| `event <描述>` | `event 突然下大雨了！` | 触发特殊事件 |
| `do <CH> <活动>` | `do 小明 rest` | 指定活动 |
| `quest` / `q` | `q` | 查看任务列表 |
| `log` / `l` | `l` | 查看事件日志 |
| `clear` | `clear` | 清屏 |
| `help` / `h` | `h` | 帮助 |

---

## 五、Web 仪表盘

```bash
# 后台运行（另一个终端）
python3 game_dashboard.py
# 访问 http://localhost:5002
```

仪表盘功能：
- 实时角色状态（需求条、情绪、地点）
- 关系矩阵可视化
- 任务进度条
- 今日事件标签
- 自动每 3 秒刷新

---

## 六、快速开始

### 方式1：CLI 交互（推荐）

```bash
cd /workspace/SereneX/phase2
python3 game_cli.py
```

### 方式2：快速演示（自动10轮）

```bash
python3 run_game.py
```

### 方式3：Web 仪表盘

```bash
python3 game_dashboard.py
# 然后用 CLI 另外开一轮 tick
python3 game_cli.py
# 或在 CLI 内运行 tick 后刷新仪表盘
```

---

## 七、玩家介入玩法

### 场景1：主动组织活动

```
serenex> go 小明 cafe
serenex> go 小雨 cafe
serenex> go 阿华 cafe
# → 自动触发三人聚会，任务完成
```

### 场景2：私信引导剧情

```
serenex> msg 小明 最近有什么烦恼吗？
# → 小明回复，玩家介入推动对话
```

### 场景3：制造事件改变走向

```
serenex> event 流星雨划过夜空
# → 所有CH心情+0.1，影响当日行为
```

### 场景4：紧急干预

```
serenex> do Hertz rest
# → Hertz 强制休息，能量恢复
```

---

## 八、依赖

```
Phase1 依赖：
  - python-dotenv
  - flask / flask-cors
  - requests

Phase2 新增：
  - flask（仪表盘）
```

---

## 九、后续计划

- **Phase 3**：多沙盒互联（多个城市/社群互通）
- **Phase 4**：长期记忆进化 + 社交网络可视化
- **Phase 5**：玩家扮演特定角色（第一/第三人称混合）

---

*文档版本：v2.0 | 构建于 Phase 1 基础之上*
