# SereneX Phase 1 运行指南

> 项目地址：https://github.com/guhz18/serenex-phase1

---

## 一、项目简介

SereneX Phase 1 是一个 AI 对话智能体项目，集成了以下核心模块：

| 模块 | 文件 | 说明 |
|------|------|------|
| 对话引擎 | `serenex.py` | 主入口 CLI，支持多个子命令 |
| LLM 接口 | `llm_interface.py` | 支持 DeepSeek 等模型 |
| 人格系统 | `personality.py` | MBTI + Big Five 人格建模 |
| 记忆系统 | `memory_system.py` + `sleep_consolidation.py` | 长期记忆 + 睡眠整合 |
| Web 仪表盘 | `dashboard_server.py` | 可视化状态面板 |
| 内容爬虫 | `content_scraper.py` | 抓取博主数据 |
| 聊天记录导入 | `chatlog_importer.py` | 导入微信/QQ 等聊天记录 |
| 训练脚本 | `train_hertz.py` | 个性化训练 |

---

## 二、环境要求

- **Python**: 3.10 或更高
- **操作系统**: Linux / macOS / Windows (WSL)
- **网络**: 需要能够访问 DeepSeek API（国内需考虑代理）

---

## 三、安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/guhz18/serenex-phase1.git
cd serenex-phase1
```

如果只需要 `phase1` 目录（实际代码所在）：

```bash
git clone https://github.com/guhz18/serenex-phase1.git
cd serenex-phase1/phase1
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat
```

### 3. 安装依赖

先查看项目是否有 `requirements.txt`：

```bash
# 如果有
pip install -r requirements.txt

# 如果没有（根据源码推断，至少需要以下包）
pip install requests python-dotenv flask flask-cors
```

> ⚠️ 注意：实际依赖请参考仓库根目录的 `requirements.txt`（如果存在）。本指南基于代码结构推断。

---

## 四、配置

### 1. 复制并编辑环境变量文件

```bash
cp .env.example .env   # 如果仓库中有 .env.example
# 或直接编辑
nano .env
```

### 2. 填写必要配置

`.env` 文件中至少需要配置以下内容：

```env
# LLM 配置（以 DeepSeek 为例）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的DeepSeek_API_Key
DEEPSEEK_MODEL=deepseek-chat

# 可选：代理（如果无法直接访问 API）
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

> 🔑 **如何获取 DeepSeek API Key？**
> 访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并创建 API Key。

---

## 五、运行

### 主程序入口 `serenex.py`

```bash
# 查看帮助
python serenex.py --help
```

常见子命令：

```bash
# 对话模式
python serenex.py chat

# 播放/演示模式
python serenex.py play

# 导入聊天记录
python serenex.py import <聊天记录文件路径>

# 爬取内容
python serenex.py scrape <URL>

# 训练人格模型
python serenex.py train

# 查看统计
python serenex.py stats

# 启动 Web 仪表盘
python serenex.py web

# 启动 GUI（如果实现了的话）
python serenex.py gui
```

### 直接运行各模块

```bash
# 启动 Web 仪表盘（Flask 服务）
python dashboard_server.py

# 导入聊天记录
python chatlog_importer.py

# 训练
python train_hertz.py
```

---

## 六、目录结构

```
serenex-phase1/
├── phase1/
│   ├── serenex.py          # 主入口 CLI
│   ├── llm_interface.py    # LLM 模型接口
│   ├── personality.py      # 人格系统
│   ├── memory_system.py    # 记忆系统
│   ├── sleep_consolidation.py  # 睡眠整合
│   ├── dashboard_server.py # Web 仪表盘
│   ├── content_scraper.py  # 内容爬虫
│   ├── chatlog_importer.py # 聊天记录导入
│   ├── train_hertz.py      # 训练脚本
│   ├── chat_history.json   # 聊天记录数据
│   ├── .env                # 环境变量（勿上传 Git！）
│   ├── memory_store/       # 记忆存储目录
│   └── examples/           # 示例文件
└── README.md
```

---

## 七、注意事项

### ⚠️ 安全提醒

- **`.env` 文件包含敏感信息**（API Key 等），已配置在 `.gitignore` 中，**请勿将其提交到 GitHub**。
- 如果需要修改 API Key，直接编辑 `phase1/.env` 文件即可。
- 不要把 `memory_store/` 目录中的内容同步到 GitHub（包含私有对话数据）。

### 🔧 常见问题

**Q: 运行时报 `ModuleNotFoundError`**
```bash
pip install <缺失的模块名>
```

**Q: API 调用失败**
- 检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确
- 检查网络是否能访问 DeepSeek API（可能需要配置代理）

**Q: Web 仪表盘无法访问**
默认端口为 5000，访问 http://localhost:5000

---

## 八、后续更新

如果仓库有更新，可以拉取最新代码：

```bash
git pull origin main
```

---

*文档由 AI 助手根据仓库代码结构自动生成，如有出入请参考仓库最新内容。*
