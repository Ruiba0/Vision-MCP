"""视觉模型调用模块：读图 -> base64 -> 调 OpenAI 兼容接口 -> 返回文字。

只用标准库（urllib），不依赖 openai SDK，兼容 Python 3.8+。
"""

from __future__ import annotations

import base64
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

SUPPORTED_EXTS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
}

TIMEOUT_SECONDS = 120


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"error": f"配置文件不存在: {CONFIG_PATH}"}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"error": f"config.json 格式错误: {e}"}


def encode_image(path: str, max_bytes: int) -> tuple[str, str] | str:
    p = Path(path)
    if not p.exists():
        return f"图片文件不存在: {path}"
    if not p.is_file():
        return f"路径不是文件: {path}"

    ext = p.suffix.lower().lstrip(".")
    if ext not in SUPPORTED_EXTS:
        return f"不支持的图片格式: .{ext}，支持 {', '.join(SUPPORTED_EXTS)}"

    size = p.stat().st_size
    if size > max_bytes:
        return f"图片过大: {size} 字节，超过上限 {max_bytes} 字节"

    b64 = base64.b64encode(p.read_bytes()).decode()
    return b64, SUPPORTED_EXTS[ext]


def call_vision_api(api_base: str, api_key: str, model: str, messages: list) -> str:
    """POST {api_base}/chat/completions，返回文字或错误信息。"""
    url = api_base.rstrip("/") + "/chat/completions"
    payload = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return f"视觉模型调用失败 (HTTP {e.code}): {detail[:500]}"
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.timeout):
            return f"视觉模型调用超时（{TIMEOUT_SECONDS} 秒）"
        return f"视觉模型连接失败: {reason}，请检查 vision_api_base 是否正确"
    except socket.timeout:
        return f"视觉模型调用超时（{TIMEOUT_SECONDS} 秒）"

    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return f"视觉模型返回格式异常: {body[:500]}"

    return content or "(视觉模型返回空内容)"


def describe_image(path: str, question: str = "详细描述这张图片的内容") -> str:
    cfg = load_config()
    if isinstance(cfg, dict) and "error" in cfg:
        return cfg["error"]

    api_base = cfg.get("vision_api_base")
    api_key = cfg.get("vision_api_key")
    model = cfg.get("vision_model")
    max_bytes = cfg.get("max_image_bytes", 10485760)

    if not all([api_base, api_key, model]):
        return "config.json 缺少必要字段: vision_api_base / vision_api_key / vision_model"
    if "在此填入" in api_key:
        return "config.json 里的 vision_api_key 还是占位符，请先编辑配置文件"

    try:
        max_bytes = int(max_bytes)
    except (TypeError, ValueError):
        return f"config.json 里的 max_image_bytes 应为数字，当前值: {max_bytes!r}"

    result = encode_image(path, max_bytes)
    if isinstance(result, str):
        return result
    b64, mime = result

    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": question},
        ],
    }]
    return call_vision_api(api_base, api_key, model, messages)
