#!/usr/bin/env python3
"""Vision MCP 服务：暴露 describe_image 工具给 Claude Code / Codex。

不依赖第三方 MCP SDK，直接实现 MCP stdio 协议
（newline-delimited JSON-RPC 2.0），因此兼容 Python 3.8+。

主模型（如 GLM）没有视觉能力时，可通过此工具查看图片：
1. 主模型调用 describe_image(path, question)
2. 工具读图 -> 调用户配置的视觉模型 -> 返回文字描述
3. 主模型基于文字继续推理
"""

import json
import sys

from vision_client import describe_image

DEFAULT_PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "describe_image",
        "description": (
            "查看指定路径的图片，返回视觉模型的文字描述。"
            "当用户让你查看、分析、识别、看某张图片时调用此工具。"
            "支持格式: png / jpg / jpeg / gif / webp / bmp"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "图片文件的绝对路径",
                },
                "question": {
                    "type": "string",
                    "description": (
                        "想问视觉模型的问题，例如 "
                        '"详细描述这张图片的内容" 或 "识别图里所有文字"'
                    ),
                },
            },
            "required": ["path"],
        },
    }
]


def make_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(req):
    """处理一条 JSON-RPC 请求，返回响应 dict / list，或 None（通知无需响应）。"""
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        params = req.get("params") or {}
        return make_response(req_id, {
            # 回显客户端请求的协议版本，保证协商总能成功
            "protocolVersion": params.get("protocolVersion", DEFAULT_PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "vision", "version": "1.0.0"},
        })

    if method == "ping":
        return make_response(req_id, {})

    if method == "tools/list":
        return make_response(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        if name != "describe_image":
            return make_error(req_id, -32602, f"未知工具: {name}")
        args = params.get("arguments") or {}
        text = describe_image(
            args.get("path", ""),
            args.get("question", "详细描述这张图片的内容"),
        )
        return make_response(req_id, {
            "content": [{"type": "text", "text": text}],
            "isError": False,
        })

    # 通知（无 id）不回复；未知请求按规范返回"方法不存在"
    if req_id is not None:
        return make_error(req_id, -32601, f"未知方法: {method}")
    return None


def dispatch(msg):
    """解析并分发一条消息，返回响应或 None。"""
    try:
        req = json.loads(msg.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return make_error(None, -32700, f"JSON 解析错误: {e}")

    # JSON-RPC 批量请求：逐条处理，过滤掉通知
    if isinstance(req, list):
        responses = [dispatch_one(item) for item in req if isinstance(item, dict)]
        responses = [r for r in responses if r is not None]
        return responses or None
    if isinstance(req, dict):
        return dispatch_one(req)
    return make_error(None, -32600, "请求必须是 JSON 对象或数组")


def dispatch_one(req):
    try:
        return handle_request(req)
    except Exception as e:
        return make_error(req.get("id"), -32603, f"内部错误: {type(e).__name__}: {e}")


def main():
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            break
        if not line.strip():
            continue
        resp = dispatch(line)
        if resp is not None:
            data = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
