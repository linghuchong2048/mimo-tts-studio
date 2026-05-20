# 铸光音频工作站 (MiMo Audio Workstation)

> 基于节点连线的可视化音频工作站，支持语音克隆与语音设计。

## 原作者

本项目基于 [MiMo TTS Studio](https://github.com/anthropics/claude-code) 二次创作（二创），原作者项目完全由 Claude Code + MiMo API 生成。

## 二创新增功能

- **本地 OmniVoice TTS 引擎** — 支持离线语音克隆，无需云端 API，RTX 3060+ 6GB 显存可运行
- **自定义 LLM 推理** — 支持 DeepSeek 等 OpenAI 兼容接口，替换 MiMo 云端推理
- **智能有声书系统** — AI 自动分析角色、切分段落、标注情绪，批量生成多角色配音
- **合并下载** — 批量生成后一键合并所有片段为完整音频文件
- **一键启动** — Windows 批处理脚本，双击启动前后端 + 本地 TTS 服务
- **TTS Provider 抽象层** — 支持 MiMo 云端 / 本地 OmniVoice 双后端切换
- **LLM Provider 抽象层** — 支持 MiMo 云端 / OpenAI 兼容接口双后端切换

## 技术栈

- **前端**: React 19 + TypeScript + Vite + @xyflow/react (React Flow)
- **后端**: Express 5 + TypeScript + Node.js
- **桌面**: Electron + electron-builder
- **本地 TTS**: OmniVoice (k2-fsa, Apache 2.0) + PyTorch + FastAPI
- **云端 TTS**: 小米 MiMo API
- **LLM 推理**: DeepSeek / MiMo / OpenAI 兼容接口

## 快速开始

### 环境要求

- Node.js >= 22
- Python 3.10+ (本地 TTS 模式需要)
- NVIDIA GPU 6GB+ 显存 (本地 TTS 模式需要)

### 安装

```bash
npm install
```

### 配置 Python 环境（本地 TTS 模式）

```bash
pip install torch torchaudio soundfile fastapi uvicorn numpy --index-url https://download.pytorch.org/whl/cu121
```

### 启动

**Windows 一键启动：** 双击 `start-all.bat`

**手动启动：**
```bash
npm run dev
```

访问：
- 前端: http://localhost:5173
- 后端: http://localhost:3001
- 本地 TTS: http://localhost:8000（选择本地模式后自动启动）

### 工作模式

点击右上角 API Key 设置：

- **云端模式**：TTS + LLM 全走 MiMo API，只需填 MiMo Key
- **本地模式**：TTS 走 OmniVoice（自动启动），LLM 走 DeepSeek 等 OpenAI 兼容接口

## 项目结构

```
├── src/
│   ├── App.tsx              # 前端主应用（节点编辑器、工作区、有声书控制台）
│   ├── main.tsx             # React 入口
│   └── styles.css           # 全局样式
├── server/
│   └── index.ts             # Express API 服务（TTS/LLM Provider、工作区 CRUD）
├── omnivoice-server/
│   └── server.py            # 本地 OmniVoice TTS 服务（FastAPI）
├── omnivoice/               # OmniVoice Python 模型包
├── checkpoints/             # 模型权重文件（需自行下载）
├── electron/
│   └── main.cjs             # Electron 主进程
├── start-all.bat            # Windows 一键启动脚本
└── package.json
```

## License

- 本项目代码：Apache 2.0
- OmniVoice 模型：Apache 2.0 (k2-fsa/Xiaomi)
- 核心能力基于小米 MiMo 模型，本项目非小米官方产品
