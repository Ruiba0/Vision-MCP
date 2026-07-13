#!/usr/bin/env python3
"""Vision MCP 一键安装脚本

功能：
1. 安装 Python 依赖
2. 交互式配置视觉模型（提供常见模型预设）
3. 注册 MCP 到 Claude Code
4. 注册 MCP 到 Codex
5. 在 CLAUDE.md / AGENTS.md 中添加图片处理规则

幂等：可重复运行，已有配置会跳过或询问后覆盖。
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
SERVER_PATH = PROJECT_DIR / "server.py"
CONFIG_PATH = PROJECT_DIR / "config.json"
CONFIG_EXAMPLE = PROJECT_DIR / "config.example.json"
REQUIREMENTS = PROJECT_DIR / "requirements.txt"

CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
AGENTS_MD = Path.home() / ".codex" / "AGENTS.md"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"

IMAGE_RULE = """## 图片处理

当用户提到图片文件路径（.png/.jpg/.jpeg/.gif/.webp/.bmp），或要求查看/分析/识别某个图片文件时：

- 先判断当前主模型自身是否具备视觉能力
- 具备视觉（如 Claude Sonnet/Opus、GPT-4o、Qwen-VL 等多模态模型）→ 直接读取图片并分析
- 不具备视觉（如 GLM 等纯文本模型）→ 调用 vision MCP 的 describe_image 工具，传入图片路径和问题
- 不确定自身是否支持视觉时，默认调用 describe_image 工具作为兜底
- 用户明确要求"用 MCP 看"或"调视觉模型"时，无论主模型是否支持视觉，都调用 describe_image 工具
"""

PRESETS = {
    "1": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-vl-max", "Qwen-VL (阿里 DashScope)"),
    "2": ("https://open.bigmodel.cn/api/paas/v4", "glm-4v-plus", "GLM-4V (智谱)"),
    "3": ("https://api.openai.com/v1", "gpt-4o", "GPT-4o (OpenAI)"),
    "4": ("https://ark.cn-beijing.volces.com/api/v3", "doubao-1.5-vision-pro", "Doubao (火山引擎)"),
    "5": (None, None, "自定义"),
}


def step(msg):
    print(f"\n=== {msg} ===")


def install_deps():
    step("安装 Python 依赖")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    )


def configure_vision_model():
    step("配置视觉模型")

    if CONFIG_PATH.exists():
        ans = input(f"已存在 {CONFIG_PATH}，是否重新配置？(y/N): ").strip().lower()
        if ans != "y":
            print("跳过配置")
            return

    print("选择视觉模型:")
    for k, (_, _, label) in PRESETS.items():
        print(f"  {k}. {label}")

    while True:
        choice = input("选择 (1-5): ").strip()
        if choice in PRESETS:
            break
        print("无效选择，请输入 1-5")

    api_base, model, _ = PRESETS[choice]
    if api_base is None:
        api_base = input("vision_api_base: ").strip()
        model = input("vision_model: ").strip()

    api_key = input("vision_api_key: ").strip()
    if not api_key:
        print("API key 不能为空")
        sys.exit(1)

    config = {
        "vision_api_base": api_base,
        "vision_model": model,
        "vision_api_key": api_key,
        "max_image_bytes": 10485760,
    }
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"已写入 {CONFIG_PATH}")


def register_claude_code():
    step("注册到 Claude Code")
    try:
        subprocess.run(
            ["claude", "--version"], capture_output=True, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("未检测到 claude 命令，跳过 Claude Code 注册")
        print(
            "请手动执行: claude mcp add vision -- python "
            + str(SERVER_PATH).replace("\\", "/")
        )
        return

    subprocess.run(
        ["claude", "mcp", "remove", "vision"], capture_output=True
    )
    subprocess.check_call(
        [
            "claude",
            "mcp",
            "add",
            "vision",
            "--",
            sys.executable,
            str(SERVER_PATH),
        ]
    )
    print("已注册到 Claude Code")


def register_codex():
    step("注册到 Codex")
    CODEX_CONFIG.parent.mkdir(parents=True, exist_ok=True)

    existing = (
        CODEX_CONFIG.read_text(encoding="utf-8")
        if CODEX_CONFIG.exists()
        else ""
    )

    if "[mcp_servers.vision]" in existing:
        print("Codex 已有 vision MCP 配置，跳过")
        return

    python_str = sys.executable.replace("\\", "/")
    server_str = str(SERVER_PATH).replace("\\", "/")

    new_section = (
        f'\n[mcp_servers.vision]\n'
        f'command = "{python_str}"\n'
        f'args = ["{server_str}"]\n'
    )

    if existing and not existing.endswith("\n"):
        existing += "\n"
    CODEX_CONFIG.write_text(existing + new_section, encoding="utf-8")
    print(f"已写入 Codex 配置: {CODEX_CONFIG}")


def patch_md(path: Path):
    step(f"更新 {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    if "describe_image" in existing:
        print(f"{path} 已包含图片处理规则，跳过")
        return

    new_content = existing
    if existing and not existing.endswith("\n"):
        new_content += "\n"
    new_content += "\n" + IMAGE_RULE

    path.write_text(new_content, encoding="utf-8")
    print(f"已更新 {path}")


def main():
    print("Vision MCP 安装脚本")
    print(f"项目目录: {PROJECT_DIR}")
    print(f"Python: {sys.executable}")

    steps = [
        ("安装依赖", install_deps),
        ("配置视觉模型", configure_vision_model),
        ("注册 Claude Code", register_claude_code),
        ("注册 Codex", register_codex),
        ("更新 CLAUDE.md", lambda: patch_md(CLAUDE_MD)),
        ("更新 AGENTS.md", lambda: patch_md(AGENTS_MD)),
    ]

    errors = []
    for name, fn in steps:
        try:
            fn()
        except Exception as e:
            print(f"  [错误] {name} 失败: {e}")
            errors.append(name)

    step("安装结束")
    if errors:
        print(f"以下步骤失败: {', '.join(errors)}")
        print("请根据上述提示手动修复后重跑")
    else:
        print("所有步骤完成")

    print(
        "\n下一步:\n"
        "1. 重启 Claude Code 和 Codex\n"
        "2. 在对话中说\"去 D:/xxx/yyy.png 看看这张图\"测试\n"
        f"3. 如需修改视觉模型配置，编辑: {CONFIG_PATH}"
    )


if __name__ == "__main__":
    main()
