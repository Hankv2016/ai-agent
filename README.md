# AI 对话客户端

一个支持**多模态（图片）**、**多会话管理**、**本地持久化**与**导入/导出**的 AI 对话工具，提供图形界面（PyQt5）与命令行两种模式，底层对接任意 OpenAI 兼容 API。

## ✨ 项目亮点

- **纯本地优先，隐私友好**：所有对话历史与设置都保存在本地 JSON，API Key 仅存放于本地 `.env`，不上传、不依赖任何云端账户。
- **极简依赖**：第三方包仅 `PyQt5` 与 `openai`；Markdown 渲染、`.env` 解析均为零依赖自实现，安装轻快、可移植性强。
- **GUI / CLI 双形态**：上层是 PyQt5 图形界面，底层是统一的 `AIClient` 核心，命令行与脚本同样可调用，同一份逻辑两套前端。
- **会话可移植**：支持 `.md` / `.json` 导入导出，导出文件名自动带时间戳，便于归档、备份与分享；并可自定义本地保存目录。
- **工程稳健**：内置 offscreen 自动化冒烟测试（`_smoke2.py`，无需联网即可回归核心流程），并带 `faulthandler` 崩溃日志与全局异常弹窗兜底，便于定位问题。

## 功能特性

- **OpenAI 兼容**：通过 `OPENAI_BASE_URL` 对接官方、中转或本地模型服务。
- **多模态看图**：在 GUI 粘贴图片 URL，模型即可"看图"作答；图片以缩略图内嵌显示。
- **双模式**：图形界面（GUI）+ 命令行交互（CLI）。
- **多会话管理**：新建 / 切换 / 重命名 / 删除会话，左侧栏操作。
- **自动持久化**：对话按会话保存为本地 JSON，重启自动恢复。
- **导入 / 导出**：支持 `.md` 与 `.json`；导出文件名带时间戳。
- **自定义保存位置**：可在 GUI「设置」中指定自动保存目录。
- **流式回复 / 停止生成 / 侧栏折叠**等体验细节。
- **GUI 运行时连接设置**：通过「设置」打开对话框，运行时临时配置 `base_url` / `API Key` / 模型 / 保存目录，仅本次进程有效，不写入 `.env`。
- **消息排队与自动续发**：请求进行中输入框保持可编辑，发送按钮变为「排队」，可继续输入并加入队列；上一条结束后自动发送队首。右键「发送/排队」按钮可查看、取消（双击删除 / 清空全部）排队消息。

## 目录结构

```
.
├── gui.py            # PyQt5 图形界面（可直接 py gui.py 启动）
├── cli.py            # 命令行交互 / 单次问答
├── client.py         # AIClient：封装 OpenAI 兼容接口 + 加载 .env
├── mdrender.py       # Markdown -> HTML 渲染
├── gui/
│   └── main.ui       # Qt Designer 界面布局
├── run.cmd           # Windows 启动脚本（依赖检查 + 选 GUI/CLI + 参数透传）
├── run.sh            # Linux/macOS 启动脚本（同上）
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

> `run` 会在每次启动时自动把 `.env` 加载为环境变量，改完即时生效，无需重启终端。

## 使用

### 启动脚本（自动检查依赖）

项目提供跨平台启动脚本，运行前会**自动检测 `PyQt5` / `openai`**，缺失则提示并安装：

- **Windows**：`run.cmd`
- **Linux / macOS**：先赋可执行权限 `chmod +x run.sh`，再 `./run.sh`

无参数运行会交互式选择 GUI / CLI 模式。

### 图形界面

```bash
run.cmd gui          # Windows
./run.sh gui         # Linux / macOS
# 或直接：
py gui.py
```

### 命令行（参数透传）

启动脚本会把 CLI 参数直接透传给 `cli.py`，支持 `-m/--model`、`-u/--base-url`、`-k/--api-key`、`-i/--interactive` 及问题文本：

> GUI 模式同样支持 `--api-key` / `--base-url` / `--model` 三个参数，用于临时覆盖 `.env` 中的连接配置（仅本次进程有效），例如 `run.cmd gui --api-key sk-xxx --base-url https://xxx/v1 --model gpt-4o`。

```bash
# 交互模式
run.cmd -i
./run.sh -i

# 单次问答
run.cmd "用一句话解释量子纠缠"
./run.sh "用一句话解释量子纠缠"

# 临时覆盖模型 / API Key
run.cmd -m gpt-4 -k sk-xxx "你好"
./run.sh -m gpt-4 -k sk-xxx "你好"
```

> 提示：Windows 下若要显式指定 `cli` 前缀可用 `run.cmd cli -i`；直接传 CLI 参数（如上）即可，无需写 `cli` 关键字。Linux/macOS 下 `./run.sh cli -i` 同样支持。

## 图片 / 多模态

> **实现说明**：图片 URL 由 Python `urllib` 下载后以内存资源内嵌显示，不依赖 Qt 自带的 OpenSSL，从而规避了 `QTextBrowser` 直接加载 `https` 图片常见的「拉不到图 / 段错误」问题。

1. 在 GUI 的「图片链接」框中粘贴一个或多个 `http(s)` 图片 URL（多个用空格 / 逗号 / 换行分隔）。
2. 在主输入框写入问题，点击「发送」。
3. 图片会作为多模态内容发送给模型；界面内以缩略图显示（图片由 Python `urllib` 下载，绕开 Qt 自身的 SSL 限制）。
4. 点击缩略图下方的链接，可在系统浏览器中打开原图。

> 若某图片 URL 显示破图，通常是该地址防盗链 / 返回 403（任何程序都无法获取），可换用可直链的图源。

## GUI 设置与排队

### 运行时连接设置

点击工具栏「设置」打开对话框，可**运行时临时**配置：

- `base_url` / `API Key` / 模型：覆盖 `.env` 中的连接配置，**仅本次进程有效，不写入 `.env`**；
- 自动保存目录：同此前行为。

改完立即生效，适合临时切换模型 / 中转地址，不必修改 `.env` 或环境变量。

### 消息排队与自动续发

- 发送后输入框**保持可编辑**；当上一条请求进行中，发送按钮文案变为「排队」，点击（或在忙碌时按回车）即把当前输入的文字 / 图片加入队列。
- 上一条请求结束（成功 / 失败 / 停止）后，程序自动取出队首并发送，状态栏提示剩余条数。
- 按钮实时显示排队数量角标，如「排队(2)」。
- **右键**「发送/排队」按钮 → 「排队消息」对话框：列出每条排队预览，**双击删除**单条、「清空全部」一键清空；关闭后主界面角标同步。

## 会话 / 导入导出

- 左侧栏：新建、切换、重命名（双击）、删除会话。
- 「导出」按钮：将当前会话导出为 `.md` 或 `.json`，文件名自动带时间戳。
- 「导入」按钮：可导入 `.md`（按 `## 你` / `## AI` 分段）或 `.json` 历史。
- 「设置」按钮：打开设置对话框，可修改自动保存目录（默认 `conversations/`），并运行时临时配置 `base_url` / `API Key` / 模型（仅本次进程有效，不写 `.env`）。

## 测试

```bash
py -m py_compile gui.py && py _smoke2.py
```

`_smoke2.py` 在 offscreen 模式下验证控件、图片解析、Markdown 渲染、会话持久化、重命名等，无需网络。

## 已知问题 / 注意事项

- 启动时可能出现 `QFontDatabase: Cannot find font directory ...` 警告——这是 PyQt5 未自带字体目录所致，**无害**，不影响功能。如需消除，可部署 DejaVu 字体到提示目录，或设置环境变量 `QT_QPA_FONTDIR` 指向系统字体目录（如 `C:\Windows\Fonts`）。
- 启动恢复含网络图片的历史会话时，可能出现 `libpng warning: iCCP: known incorrect sRGB profile` 警告——这是远端 PNG 自带不规范的 sRGB 颜色配置文件所致，由 `QImage.loadFromData` 解码时打印，**无害**，不影响显示。程序已内置 `_strip_png_profile`：若环境装有 `Pillow` 会自动重新编码 PNG 去除 iCCP 从而消除警告；也可手动 `pip install pillow` 启用。
- 会话文件与 `settings.json` 已被 `.gitignore` 忽略，不会进入版本库。
- API Key 仅存放于本地 `.env`，请勿提交到仓库。
