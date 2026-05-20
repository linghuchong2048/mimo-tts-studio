"""
OmniVoice 本地 TTS 服务
提供 HTTP API 供 Mimo Audio Workstation 调用

用法:
  python server.py --model-path F:\OmniVoice-srt\OmniVoice\checkpoints --port 8000

首次运行如未指定 --model-path，会自动从 HuggingFace 下载模型（约 14GB）。
"""

import argparse
import base64
import io
import os
import sys

# 国内网络环境：HuggingFace 被墙，需要手动下载 Whisper 模型。
# 方案 1（推荐）: 在 CMD 中设置环境变量后启动
#   set HF_ENDPOINT=https://hf-mirror.com
# 方案 2: 用 modelscope 下载后放本地
#   pip install modelscope
#   python -c "from modelscope import snapshot_download; snapshot_download('openai/whisper-large-v3-turbo')"
# 方案 3: 用代理
#   set HTTPS_PROXY=http://127.0.0.1:你的代理端口
#
# Whisper 模型缓存路径（首次需下载约 1.5GB）:
#   Windows: C:\Users\你的用户名\.cache\huggingface\hub\models--openai--whisper-large-v3-turbo\
#
# 如果已有本地模型，可在下面指定路径:
# _LOCAL_WHISPER_PATH = r"C:\Users\...\.cache\huggingface\hub\models--openai--whisper-large-v3-turbo\snapshots\..."
_LOCAL_WHISPER_PATH = os.environ.get("WHISPER_MODEL_PATH", "")

# 在导入 omnivoice 前设置镜像（omnivoice 内部会用到 transformers）
if not os.environ.get("HF_ENDPOINT"):
    # 尝试多个国内镜像
    for mirror in ["https://hf-mirror.com", "https://huggingface.sukaka.com"]:
        os.environ["HF_ENDPOINT"] = mirror
        break  # 只设第一个，后面的备用

# 将项目根目录加入 sys.path，以便导入 omnivoice 包
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import tempfile
import time
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MODEL = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32
SAMPLE_RATE = 24000

# 串行锁：防止并行请求导致 GPU 显存溢出
import threading as _threading
_GENERATE_LOCK = _threading.Lock()


def ensure_whisper_model():
    """确保 Whisper ASR 模型已下载，然后开启离线模式。"""
    from pathlib import Path
    from huggingface_hub import snapshot_download, scan_cache_dir

    whisper_id = "openai/whisper-large-v3-turbo"

    # 检查是否已在 HF 缓存中
    cached = False
    try:
        hf_cache = scan_cache_dir()
        for repo in hf_cache.repos:
            if repo.repo_id == whisper_id and repo.revisions:
                cached = True
                break
    except Exception:
        pass

    if not cached:
        local = os.environ.get("WHISPER_MODEL_PATH", "")
        if local and Path(local).exists():
            cached = True

    if not cached:
        print(f"[OmniVoice] Downloading Whisper ASR model ({whisper_id})...")
        try:
            snapshot_download(whisper_id)
            cached = True
        except Exception as e:
            print(f"[OmniVoice] WARNING: Failed to download Whisper: {e}")

    if cached:
        # 强制离线：在导入 transformers 之前设置，并做 monkey-patch 兜底
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        # monkey-patch huggingface_hub 强制离线
        try:
            import huggingface_hub.constants as hf_constants
            hf_constants.HF_HUB_OFFLINE = True
        except Exception:
            pass
        print("[OmniVoice] Whisper model ready, offline mode ON")
    else:
        print("[OmniVoice] WARNING: Voice cloning unavailable, voice design only")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODEL
    model_path = app.state.model_path

    # 1. 确保 ASR 模型可用
    ensure_whisper_model()

    # 2. 加载 TTS 模型
    print(f"[OmniVoice] Loading TTS model on {DEVICE} ({DTYPE})...")
    print(f"[OmniVoice] Model path: {model_path}")
    from omnivoice import OmniVoice

    MODEL = OmniVoice.from_pretrained(
        model_path,
        device_map=DEVICE,
        dtype=DTYPE,
    )
    print("[OmniVoice] TTS model loaded. Ready.")
    yield
    MODEL = None


app = FastAPI(title="OmniVoice Local TTS", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---- 请求体 ----

class VoiceDesignRequest(BaseModel):
    voiceDescription: str = ""
    text: str
    format: str = "wav"


class VoiceCloneRequest(BaseModel):
    audioDataUrl: str  # data:audio/xxx;base64,...
    text: str
    instruction: str = ""
    format: str = "wav"


# ---- 工具函数 ----

def decode_data_url(data_url: str) -> tuple[bytes, str]:
    if not data_url.startswith("data:"):
        raise ValueError("Invalid data URL")
    header, b64 = data_url.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    ext = mime.split("/")[-1]
    if ext in ("x-wav", "wave"):
        ext = "wav"
    if ext == "mpeg":
        ext = "mp3"
    return base64.b64decode(b64), ext


def encode_wav_base64(audio, sample_rate: int = SAMPLE_RATE) -> str:
    # 移到 CPU 并转为 float32 numpy
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "numpy"):
        audio = audio.numpy()
    audio = np.asarray(audio, dtype=np.float32).squeeze()
    # 限制幅度
    peak = np.abs(audio).max()
    if peak > 1.0:
        audio = audio / peak * 0.95
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ---- 自然语言 → OmniVoice instruct 关键词映射 ----

# OmniVoice 支持的关键词（中英文均可混用，逗号分隔）
_CN_KEYWORD_MAP = {
    # 性别
    "男": "male", "男性": "male", "女": "female", "女性": "female",
    "中性": "",  # 中性不计入，用默认音色
    # 年龄
    "儿童": "child", "小孩": "child", "孩子": "child",
    "少年": "teenager", "青少年": "teenager", "十岁": "child",
    "青年": "young adult", "年轻": "young adult", "年轻人": "young adult",
    "二十": "young adult", "25": "young adult", "30": "young adult",
    "中年": "middle-aged", "大叔": "middle-aged", "大妈": "middle-aged",
    "四十": "middle-aged", "五十": "middle-aged", "35": "middle-aged", "40": "middle-aged",
    "老年": "elderly", "老人": "elderly", "六十": "elderly",
    # 音调
    "低沉": "low pitch", "浑厚": "low pitch",
    "低音": "low pitch", "低音调": "low pitch", "偏低": "low pitch",
    "中音": "moderate pitch", "中音调": "moderate pitch", "适中": "moderate pitch",
    "高音": "high pitch", "高音调": "high pitch", "尖利": "high pitch", "清脆": "high pitch",
    "尖细": "very high pitch", "极高": "very high pitch",
    # 风格
    "耳语": "whisper", "耳语声": "whisper", "悄悄话": "whisper",
    # 口音
    "美式": "american accent",
    "英式": "british accent", "英国": "british accent",
    # 方言
    "四川": "sichuan dialect", "四川话": "sichuan dialect",
    "东北": "northeast dialect", "东北话": "northeast dialect",
    "河南": "henan dialect", "河南话": "henan dialect",
    "陕西": "shaanxi dialect", "陕西话": "shaanxi dialect",
    "广东": "cantonese", "广东话": "cantonese",
    "贵州": "guizhou dialect", "贵州话": "guizhou dialect",
}

def parse_instruct(desc: str) -> str | None:
    """从自然语言描述中提取 OmniVoice 关键词，英文 comma+space 格式。"""
    if not desc or not desc.strip():
        return None

    found = []
    desc_lower = desc.lower()
    # 先匹配中文
    for cn, en in _CN_KEYWORD_MAP.items():
        if cn in desc:
            if en not in found:
                found.append(en)
    # 也检查英文关键词
    en_direct = ["female", "male", "child", "teenager", "young adult", "middle-aged",
                 "elderly", "low pitch", "high pitch", "very high pitch", "very low pitch",
                 "moderate pitch", "whisper", "american accent", "british accent",
                 "chinese accent", "indian accent", "japanese accent", "korean accent"]
    for kw in en_direct:
        if kw in desc_lower and kw not in found:
            found.append(kw)

    return ", ".join(found) if found else None


# ---- API 端点 ----

@app.get("/api/status")
def status():
    return {
        "ok": True,
        "model": "k2-fsa/OmniVoice",
        "device": DEVICE,
        "sampleRate": SAMPLE_RATE,
    }


@app.post("/api/tts/voicedesign")
def voice_design(req: VoiceDesignRequest):
    if not MODEL:
        raise HTTPException(503, "Model not loaded")
    if not req.text.strip():
        raise HTTPException(400, "text is required")

    started = time.time()
    desc = req.voiceDescription.strip() or None
    instruct = parse_instruct(desc or "")
    try:
        kwargs: dict = {"text": req.text.strip()}
        if instruct:
            kwargs["instruct"] = instruct

        print(f"[TTS:design] text={req.text[:50]}... desc_len={len(desc or '')} instruct={instruct}")
        with _GENERATE_LOCK:
            result = MODEL.generate(**kwargs)
        audio = result[0] if isinstance(result, list) else result

        if audio is None or (hasattr(audio, 'numel') and audio.numel() == 0):
            raise ValueError("model returned empty audio")

        elapsed = time.time() - started
        print(f"[TTS:design] generated {audio.shape[-1]/SAMPLE_RATE:.1f}s in {elapsed:.1f}s")

        wav_b64 = encode_wav_base64(audio)
        return {
            "audioDataUrl": f"data:audio/wav;base64,{wav_b64}",
            "fileName": f"omnivoice-design-{int(time.time())}.wav",
            "elapsedMs": int(elapsed * 1000),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Voice design failed: {e}")


@app.post("/api/tts/voiceclone")
def voice_clone(req: VoiceCloneRequest):
    if not MODEL:
        raise HTTPException(503, "Model not loaded")
    if not req.text.strip():
        raise HTTPException(400, "text is required")
    if not req.audioDataUrl.strip():
        raise HTTPException(400, "reference audio (audioDataUrl) is required")

    started = time.time()
    tmp_path = None
    try:
        audio_bytes, ext = decode_data_url(req.audioDataUrl)
        tmp_path = tempfile.mktemp(suffix=f".{ext}")
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        # 克隆模式下，instruction 是情绪指导（如"低沉缓慢，绝望寒冷"），
        # 不是 OmniVoice 的属性关键词。用 parse_instruct 提取有效关键词，
        # 提取不到就只靠参考音频，不传 instruct。
        instruct = parse_instruct(req.instruction)
        print(f"[TTS:clone] text={req.text[:50]}... instruct={instruct} audio={len(audio_bytes)}B")

        kwargs: dict = {
            "text": req.text.strip(),
            "ref_audio": tmp_path,
        }
        if instruct:
            kwargs["instruct"] = instruct

        with _GENERATE_LOCK:
            result = MODEL.generate(**kwargs)
        audio = result[0] if isinstance(result, list) else result

        if audio is None or (hasattr(audio, 'numel') and audio.numel() == 0):
            raise ValueError("model returned empty audio")

        elapsed = time.time() - started
        print(f"[TTS:clone] generated {audio.shape[-1]/SAMPLE_RATE:.1f}s in {elapsed:.1f}s")

        wav_b64 = encode_wav_base64(audio)
        return {
            "audioDataUrl": f"data:audio/wav;base64,{wav_b64}",
            "fileName": f"omnivoice-clone-{int(time.time())}.wav",
            "elapsedMs": int(elapsed * 1000),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Voice clone failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="OmniVoice Local TTS Server")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind address")
    parser.add_argument(
        "--model-path",
        type=str,
        default="k2-fsa/OmniVoice",
        help="Local checkpoint path or HuggingFace model ID (default: k2-fsa/OmniVoice)",
    )
    args = parser.parse_args()

    # 将 model_path 存到 app.state 供 lifespan 使用
    app.state.model_path = args.model_path

    print(f"[OmniVoice] Starting server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
