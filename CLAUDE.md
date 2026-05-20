# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiMo Audio Workstation (铸光音频工作站) — a visual node-based audio workstation for voice cloning and voice design using the Xiaomi MiMo TTS API. Users wire together reference audio, voice style instructions, text prompts, and TTS nodes on a React Flow canvas to generate cloned or designed audio. The UI is entirely in Chinese.

## Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Start full dev environment (backend on :3001 + Vite frontend on :5173, `/api` proxied) |
| `npm run dev:client` | Vite frontend only |
| `npm run dev:server` | Express backend only (hot-reload via tsx) |
| `npm run build` | Production build: `tsc -b` + `vite build` + esbuild bundle server to `build/server/index.cjs` |
| `npm run electron` | Build + launch Electron desktop app |
| `npm run dist:win` | Build + package Windows NSIS installer (output in `release/`) |

No test runner, linter, or formatter is configured.

## Environment

Copy `.env.example` to `.env` and set `MIMO_API_KEY`. Required variables:
- `MIMO_API_KEY` — MiMo API key for TTS and LLM calls
- `PORT` — server port (default 3001)

## Architecture

This is a monolithic full-stack TypeScript app with only **3 source files**:

- **`src/App.tsx`** (~1900 lines) — Entire React frontend: 6 custom node types, workspace management, audio recording/playback, stash panel, auto-save
- **`server/index.ts`** (~1200 lines) — Express 5 API server: TTS proxying, workspace CRUD, AI text optimization, smart workspace generation
- **`electron/main.cjs`** — Electron main process: starts server in-process, loads it in a BrowserWindow

### Node Types (React Flow)

| Node | Purpose |
|---|---|
| `referenceAudio` | Upload or record a voice sample |
| `voiceStyle` | Director text for emotion/expression (has AI optimize) |
| `prompt` | Text content to synthesize |
| `voiceClone` | Main TTS node — takes ref audio + style + text, calls MiMo voice clone API |
| `voiceDesign` | TTS with designed voice (no ref audio needed, has AI polish) |
| `artifact` | Output node with playback/download/stash |

### Backend API Endpoints

- `POST /api/tts/voiceclone` — voice cloning (multipart form with audio file)
- `POST /api/tts/voicedesign` — voice design synthesis (JSON body)
- `POST /api/voice-style/optimize` — AI optimization of voice style text
- `POST /api/voice-design/optimize` — AI polishing of voice design descriptions
- `POST /api/workspaces/smart` — AI-powered smart workspace generation
- CRUD `/api/workspaces` — workspace persistence

All TTS requests proxy to `https://api.xiaomimimo.com/v1/chat/completions` using models: `mimo-v2.5-tts-voiceclone`, `mimo-v2.5-tts-voicedesign`, `mimo-v2-flash`, `mimo-v2.5-pro`.

### Key Patterns

- **Data URL transport**: Audio stored/transmitted as base64 data URLs throughout (workspace JSON, API responses)
- **Callback hydration**: React Flow nodes hydrated with callbacks via `useMemo` before passing to graph (functions not serialized to persisted state)
- **Atomic file persistence**: Workspace data uses write-to-`.tmp`-then-rename to prevent corruption; stored at `data/workspaces.json`
- **Auto-save with 5-second debounce**: Changes to nodes/edges/stash trigger debounced save to backend

## Tech Stack

React 19 + TypeScript + Vite + @xyflow/react (React Flow) + Express 5 + Electron + electron-builder. ESM modules (`"type": "module"`).

## Build Outputs

- `dist/` — Vite frontend build (gitignored)
- `build/server/index.cjs` — esbuild-bundled server for Electron (gitignored)
- `release/` — Electron-builder installer output (gitignored)
- `data/workspaces.json` — runtime workspace store (gitignored)
