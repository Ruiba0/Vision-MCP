# Vision MCP

让没有视觉能力的 LLM（如 GLM）也能在 Claude Code / Codex 中处理图片。

## 工作原理

主模型遇到图片时，调用本 MCP 提供的 `describe_image` 工具：

1. 工具读取本地图片文件
2. 调用你配置的视觉模型（Qwen-VL / GPT-4o / GLM-4V / Doubao 等任意 OpenAI 兼容接口）
3. 返回文字描述给主模型
4. 主模型基于文字继续推理

主模型全程不接触图片二进制，所以纯文本模型也能用。

## 一键安装

```bash
git clone https://github.com/yourname/vision-mcp.git
cd vision-mcp
python install.py
```

安装脚本会交互式地完成：

- 安装 Python 依赖（`mcp`、`openai`）
- 让你选择视觉模型并填入 API key
- 注册 MCP 到 Claude Code（`claude mcp add`）
- 注册 MCP 到 Codex（写入 `~/.codex/config.toml`）
- 在 `~/.claude/CLAUDE.md` 和 `~/.codex/AGENTS.md` 中添加图片处理规则

脚本幂等，可重复运行。

## 手动安装

如果不想用安装脚本：

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **配置视觉模型**

   复制 `config.example.json` 为 `config.json`，填入你的视觉模型配置：

   ```json
   {
     "vision_api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "vision_model": "qwen-vl-max",
     "vision_api_key": "sk-你的key",
     "max_image_bytes": 10485760
   }
   ```

3. **注册到 Claude Code**

   ```bash
   claude mcp add vision -- python /绝对路径/server.py
   ```

4. **注册到 Codex**

   编辑 `~/.codex/config.toml`，加入：

   ```toml
   [mcp_servers.vision]
   command = "python"
   args = ["/绝对路径/server.py"]
   ```

5. **添加图片处理规则**

   在 `~/.claude/CLAUDE.md` 和 `~/.codex/AGENTS.md` 中加入以下内容（让主模型遇到图片时主动调用工具）：

   ```markdown
   ## 图片处理

   当用户提到图片文件路径（.png/.jpg/.jpeg/.gif/.webp/.bmp），或要求查看/分析/识别某个图片文件时：

   - 先判断当前主模型自身是否具备视觉能力
   - 具备视觉（如 Claude Sonnet/Opus、GPT-4o、Qwen-VL 等多模态模型）→ 直接读取图片并分析
   - 不具备视觉（如 GLM 等纯文本模型）→ 调用 vision MCP 的 describe_image 工具，传入图片路径和问题
   - 不确定自身是否支持视觉时，默认调用 describe_image 工具作为兜底
   - 用户明确要求"用 MCP 看"或"调视觉模型"时，无论主模型是否支持视觉，都调用 describe_image 工具
   ```

## 支持的视觉模型

任意兼容 OpenAI 协议的视觉模型都可使用：

| 平台 | vision_api_base | vision_model |
|---|---|---|
| Qwen-VL (阿里 DashScope) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-max` |
| GLM-4V (智谱) | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v-plus` |
| GPT-4o (OpenAI) | `https://api.openai.com/v1` | `gpt-4o` |
| Doubao (火山引擎) | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-1.5-vision-pro` |

如需使用 Anthropic 原生协议（如 Claude），需自行修改 `vision_client.py`，当前仅支持 OpenAI 兼容协议。

## 使用方式

安装完成后重启 Claude Code / Codex，在对话中：

- "去 D:/temp/diagram.png 看看这张图"
- "分析一下 C:/screenshots/error.jpg 里的报错"
- "识别 D:/notes/page1.jpeg 里所有文字"

主模型会自动调用 `describe_image` 工具，工具返回视觉模型的文字描述，主模型基于描述继续回答。

## 工具参数

`describe_image(path: str, question: str = "详细描述这张图片的内容") -> str`

- `path`：图片文件的绝对路径，支持 png/jpg/jpeg/gif/webp/bmp
- `question`：想问视觉模型的问题，可按场景调整（"识别文字"、"描述布局"、"分析图表" 等）

## 项目结构

```
vision-mcp/
├── server.py              # MCP 服务，注册 describe_image 工具
├── vision_client.py       # 视觉模型调用（OpenAI 兼容协议）
├── config.example.json    # 配置模板（提交到 git）
├── config.json            # 你的实际配置（gitignored）
├── requirements.txt
├── install.py             # 一键安装脚本
└── README.md
```

## 常见问题

**Q: 调用报 `APIConnectionError`**
检查 `vision_api_base` 路径是否正确。OpenAI SDK 会在 base URL 后拼 `/chat/completions`，所以 base URL 不要带 `/chat/completions` 后缀。

**Q: 调用报 `401 AuthenticationError`**
API key 无效或没有该模型权限，检查 `vision_api_key` 和 `vision_model` 是否匹配对应平台。

**Q: 主模型不主动调用工具**
确认 `CLAUDE.md` / `AGENTS.md` 里的图片处理规则已添加。规则里的关键词（图片、查看、分析）会引导主模型调用 `describe_image`。

**Q: 想换视觉模型**
编辑 `config.json` 修改三个字段即可，代码不用动。或重跑 `python install.py` 重新配置。

## 依赖

- Python 3.10+
- `mcp` >= 1.2.0
- `openai` >= 1.50.0

## License

MIT
