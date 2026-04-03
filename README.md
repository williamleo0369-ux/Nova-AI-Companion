# 🌟 Nova AI Companion

> 有记忆 · 有情感 · 有温度的 AI 伴侣

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/williamleo0369-ux/Nova-AI-Companion?style=social)](https://github.com/williamleo0369-ux/Nova-AI-Companion)

## ✨ 特性

- **🧠 双层记忆系统** - 短期记忆维护对话上下文，长期记忆使用 SQLite 持久化存储，LLM 自动提取关键信息
- **💕 情感引擎** - 基于关键词的情绪检测，识别 8 种情绪状态，动态调整回应策略
- **🔊 语音系统** - Edge-TTS 免费语音合成，支持朗读回复
- **🔧 工具系统** - 内置时间查询、计算器、心情记录等工具，支持 OpenAI Function Calling
- **🌐 兼容性强** - 支持 OpenAI、Ollama、DeepSeek 等多种 LLM API

## 🚀 快速开始

### 环境要求

- Python 3.10 或更高版本
- 支持的 LLM API (OpenAI / Ollama / DeepSeek 等)

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/williamleo0369-ux/Nova-AI-Companion.git
cd Nova-AI-Companion

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip3 install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key

# 5. 运行
python3 main.py
```

### 配置 LLM

编辑 `.env` 文件，选择您使用的 LLM 服务：

```env
# 方案 A: OpenAI
LLM_API_KEY=sk-your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# 方案 B: Ollama 本地模型
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:14b

# 方案 C: DeepSeek
LLM_API_KEY=your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

## 💬 使用方法

启动程序后，即可与 Nova 对话：

```
👤 你: 你好，我叫小明
🌟 Nova: 小明你好！很高兴认识你~
```

### 可用命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/reset` | 重置对话，开始新的会话 |
| `/status` | 查看 Nova 的当前状态 |
| `/profile` | 查看已知的用户信息 |
| `/memories` | 查看 Nova 记住的重要事情 |
| `/voice` | 切换语音模式 |
| `/quit` | 退出程序 |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    main.py (交互式终端)                      │
│                         │                                   │
│                    ┌────▼────┐                               │
│                    │  Nova   │  核心引擎                     │
│                    └────┬────┘                               │
│          ┌──────────┬───┴───┬──────────┬──────────┐         │
│          ▼          ▼       ▼          ▼          ▼         │
│   ┌──────────┐┌─────────┐┌────────┐┌───────┐┌────────┐    │
│   │LLMClient ││ Memory  ││Emotion ││ Voice ││ Tools  │    │
│   │          ││ Manager ││ Engine ││Manager││Registry│    │
│   └─────┬────┘└────┬─────┘└───┬────┘└───┬───┘└───┬────┘    │
│         │     ┌────┴────┐     │         │        │         │
│         ▼     ▼         ▼     ▼         ▼        ▼         │
│    OpenAI   Short    Long   Emotion  Edge-TTS  Builtin     │
│    Ollama   Term     Term   Detector           Tools       │
│    DeepSeek Memory  Memory                                   │
└─────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
nova-ai/
├── main.py                     # 程序入口
├── config.yaml                 # 配置文件
├── .env.example                # 环境变量模板
├── requirements.txt             # Python 依赖
├── nova/
│   ├── __init__.py
│   ├── prompts.py              # 提示词构建
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm.py             # LLM 客户端
│   │   └── nova.py            # 核心引擎
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── models.py          # 数据模型
│   │   ├── short_term.py      # 短期记忆
│   │   ├── long_term.py       # 长期记忆 (SQLite)
│   │   └── manager.py          # 记忆管理器
│   ├── emotion/
│   │   ├── __init__.py
│   │   ├── detector.py        # 情绪检测器
│   │   └── engine.py          # 情感引擎
│   ├── voice/
│   │   ├── __init__.py
│   │   └── manager.py         # 语音管理器
│   └── tools/
│       ├── __init__.py
│       ├── registry.py        # 工具注册中心
│       └── builtin.py         # 内置工具
└── data/                      # 运行时自动创建
    ├── nova_memory.db
    ├── logs/
    └── output/voice/
```

## 💡 核心模块

### 记忆系统 (nova/memory/)

- **短期记忆**: 使用 `deque` 维护当前会话的对话历史
- **长期记忆**: 使用 SQLite 持久化存储用户档案、事实记忆和情感事件
- **自动提取**: LLM 每隔 3 轮对话自动从对话中提取关键信息

### 情感引擎 (nova/emotion/)

支持识别 8 种情绪状态：

| 情绪 | 关键词示例 | Nova 响应策略 |
|------|-----------|---------------|
| 😊 开心 | 开心、高兴、太棒了 | 活泼调皮，一起庆祝 |
| 😍 兴奋 | 激动、兴奋、冲冲冲 | 跟着兴奋，活泼回应 |
| 😢 难过 | 难过、伤心、孤独 | 温柔安慰，倾听陪伴 |
| 😤 愤怒 | 生气、烦死、不公平 | 保持冷静，理解认同 |
| 😰 焦虑 | 担心、紧张、压力大 | 给予安全感，放松陪伴 |
| 😴 疲惫 | 累、困、加班 | 轻柔关怀，不给压力 |
| 💕 爱意 | 爱你、想你、暖 | 温暖回应，亲切互动 |
| 😐 中性 | - | 自然衰减到基准 |

### 工具系统 (nova/tools/)

内置工具：

- `get_current_time` - 获取当前时间
- `calculate` - 计算数学表达式
- `record_mood` - 记录用户心情
- `sing_lyrics` - 唱歌功能（预留）

## 🔧 配置文件

编辑 `config.yaml` 自定义行为：

```yaml
nova:
  name: "Nova"
  version: "0.1.0"

llm:
  model: "gpt-4o-mini"
  temperature: 0.85
  max_tokens: 1024

memory:
  short_term_rounds: 20       # 短期记忆保留轮数
  db_path: "data/nova_memory.db"
  extraction_interval: 3      # 每 N 轮触发记忆提取

emotion:
  decay_rate: 0.15            # 情绪衰减速率

voice:
  enabled: false
  edge_voice: "zh-CN-XiaoyiNeural"
```

## 📝 示例对话

```
👤 你: 我叫小明，在北京工作，是一名程序员
🌟 Nova: 小明你好！很高兴认识你~ 程序员啊，难怪你这么晚还在聊天，程序员的加班文化我懂 😂

👤 你: 今天加班到很晚，感觉好累啊...
🌟 Nova: 🥺 辛苦你了，小明...
   加班真的很累，记得照顾好自己，早点休息哦。
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [OpenAI](https://openai.com/) - 提供强大的语言模型
- [Edge-TTS](https://github.com/rany2/edge-tts) - 免费语音合成
- 所有开源贡献者

---

Made with ❤️ by [williamleo0369-ux](https://github.com/williamleo0369-ux)
