"""视觉模型调用模块：读图 → base64 → 调 OpenAI 兼容接口 → 返回文字。"""

import base64
import json
from pathlib import Path

from openai import OpenAI, OpenAIError

CONFIG_PATH = Path(__file__).parent / "config.json"

SUPPORTED_EXTS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
}


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
    if "在此填入你的key" in api_key:
        return "config.json 里的 vision_api_key 还没填，请先编辑配置文件"

    result = encode_image(path, max_bytes)
    if isinstance(result, str):
        return result
    b64, mime = result

    try:
        client = OpenAI(base_url=api_base, api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": question},
                ],
            }],
        )
        return resp.choices[0].message.content or "(视觉模型返回空内容)"
    except OpenAIError as e:
        return f"视觉模型调用失败: {e}"
    except Exception as e:
        return f"未知错误: {type(e).__name__}: {e}"
