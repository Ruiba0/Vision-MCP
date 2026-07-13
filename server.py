"""Vision MCP 服务：暴露 describe_image 工具给 Claude Code / Codex。

主模型（如 GLM）没有视觉能力时，可通过此工具查看图片：
1. 主模型调用 describe_image(path, question)
2. 工具读图 → 调用户配置的视觉模型 → 返回文字描述
3. 主模型基于文字继续推理
"""

from mcp.server.fastmcp import FastMCP

from vision_client import describe_image as _describe_image

mcp = FastMCP("vision")


@mcp.tool()
def describe_image(path: str, question: str = "详细描述这张图片的内容") -> str:
    """查看指定路径的图片，返回视觉模型的文字描述。

    当用户让你查看、分析、识别、看某张图片时调用此工具。
    支持格式: png / jpg / jpeg / gif / webp / bmp

    Args:
        path: 图片文件的绝对路径
        question: 想问视觉模型的问题，例如 "详细描述这张图片的内容" 或 "识别图里所有文字"

    Returns:
        视觉模型返回的文字描述，或错误信息
    """
    return _describe_image(path, question)


if __name__ == "__main__":
    mcp.run()
