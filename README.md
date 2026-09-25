# AI 对话客户端

一个支持**多模态（图片）**、**多会话管理**、**本地持久化**与**导入/导出**的 AI 对话工具，提供图形界面（PyQt5）与命令行两种模式，底层对接任意 OpenAI 兼容 API。

## 功能特性

- **OpenAI 兼容**：通过 `OPENAI_BASE_URL` 对接官方、中转或本地模型服务。
- **多模态看图**：在 GUI 粘贴图片 URL，模型即可"看图"作答；图片以缩略图内嵌显示。
- **双模式**：图形界面（GUI）+ 命令行交互（CLI）。
- **多会话管理**：新建 / 切换 / 重命名 / 删除会话，左侧栏操作。
- **自动持久化**：对话按会话保存为本地 JSON，重启自动恢复。
- **导入 / 导出**：支持 `.md` 与 `.json`；导出文件名带时间戳。
- **自定义保存位置**：可在 GUI「设置」中指定自动保存目录。
- **流式回复 / 停止生成 / 侧栏折叠**等体验细节。

## 目录结构

```
.
├── gui.py            # PyQt5 图形界面（可直接 py gui.py 启动）
├── cli.py            # 命令行交互 / 单次问答
├── client.py         # AIClient：封装 OpenAI 兼容接口 + 加载 .env
├── mdrender.py       # Markdown -> HTML 渲染
├── gui/
│   └── main.ui       # Qt Designer 界面布局
├── run.bat           # Windows 一键启动（选 GUI / CLI，自动加载 .env）
├── _smoke2.py        # 回归冒烟测试（offscreen，无需网络）
├── conversations/    # 自动保存的会话（已被 .gitignore 忽略）
├── settings.json     # 用户设置：自动保存目录等（已被忽略）
└── .env              # API 配置（已被忽略，请勿提交）
```

## 环境要求

- Python 3.10+
- Windows / macOS / Linux

## 安装

```bash
pip install -r requirements.txt
```

## 配置

在项目根目录创建 `.env`（已被 git 忽略，请勿提交），填入：

```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

> `run.bat` 会在每次启动时自动把 `.env` 加载为环境变量，改完即时生效，无需重启终端。

## 使用

### 图形界面（推荐）

```bash
run.bat          # 选择 1 启动 GUI
# 或直接：
py gui.py
```

### 命令行

```bash
run.bat          # 选择 2 进入 CLI 交互
# 或：
py cli.py -i                       # 交互模式
py cli.py "用一句话解释量子纠缠"     # 单次问答
```

CLI 还支持 `-m/--model`、`-u/--base-url`、`-k/--api-key` 临时覆盖配置。

## 图片 / 多模态

1. 在 GUI 的「图片链接」框中粘贴一个或多个 `http(s)` 图片 URL（多个用空格 / 逗号 / 换行分隔）。
2. 在主输入框写入问题，点击「发送」。
3. 图片会作为多模态内容发送给模型；界面内以缩略图显示（图片由 Python `urllib` 下载，绕开 Qt 自身的 SSL 限制）。
4. 点击缩略图下方的链接，可在系统浏览器中打开原图。

> 若某图片 URL 显示破图，通常是该地址防盗链 / 返回 403（任何程序都无法获取），可换用可直链的图源。

## 会话 / 导入导出

- 左侧栏：新建、切换、重命名（双击）、删除会话。
- 「导出」按钮：将当前会话导出为 `.md` 或 `.json`，文件名自动带时间戳。
- 「导入」按钮：可导入 `.md`（按 `## 你` / `## AI` 分段）或 `.json` 历史。
- 「设置」按钮：修改自动保存目录（默认 `conversations/`）。

## 测试

```bash
py -m py_compile gui.py && py _smoke2.py
```

`_smoke2.py` 在 offscreen 模式下验证控件、图片解析、Markdown 渲染、会话持久化、重命名等，无需网络。

## 已知问题 / 注意事项

- 启动时可能出现 `QFontDatabase: Cannot find font directory ...` 警告——这是 PyQt5 未自带字体目录所致，**无害**，不影响功能。如需消除，可部署 DejaVu 字体到提示目录，或设置环境变量 `QT_QPA_FONTDIR` 指向系统字体目录（如 `C:\Windows\Fonts`）。
- 会话文件与 `settings.json` 已被 `.gitignore` 忽略，不会进入版本库。
- API Key 仅存放于本地 `.env`，请勿提交到仓库。
