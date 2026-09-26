@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM  SECURITY: Do NOT put your API Key in this file!
REM  Configure OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL in the
REM  .env file in this folder (already git-ignored), e.g.:
REM         OPENAI_API_KEY=sk-xxxx
REM         OPENAI_BASE_URL=https://api.openai.com/v1
REM         OPENAI_MODEL=gpt-6-astra
REM  .env is reloaded on EVERY run, so editing it takes effect
REM  immediately (no need to restart the terminal).
REM  To use real system environment variables instead, delete/empty
REM  the corresponding lines in .env.
REM ============================================================

REM ============================================================
REM  依赖检查：缺失 PyQt5 / openai 时提示安装
REM ============================================================
py -c "import PyQt5, openai" >nul 2>&1
if errorlevel 1 (
    echo [提示] 未检测到依赖 (PyQt5 / openai)。
    set /p "ans=是否现在安装依赖？(y/N) "
    if /i "!ans!"=="y" (
        py -m pip install -r requirements.txt
    ) else (
        echo 请先执行: py -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

REM ============================================================
REM  加载 .env（每次运行重新加载，编辑即时生效）
REM ============================================================
if exist "%~dp0.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
        if "%%B"=="" (set "%%A=") else (set "%%A=%%B")
    )
)

if not defined OPENAI_API_KEY (
    echo [ERROR] OPENAI_API_KEY not found in .env. See comments at top of run.cmd.
    pause
    exit /b 1
)

REM ============================================================
REM  模式判定与参数透传
REM    无参数                  -> 交互选择 GUI / CLI
REM    gui                     -> 启动图形界面
REM    cli ^<args^>              -> 剥离 cli 后透传 cli.py
REM    其余（含 -i/-m/问题文本）  -> 直接透传 cli.py
REM  （Windows 批处理对带空格参数不保留引号，故含空格的问题请用
REM    `run.cmd "你的问题"` 这种无 cli 关键字的形式，由 %* 直接透传）
REM ============================================================
if "%~1"=="" goto :choose

if /i "%~1"=="gui" (
    py gui.py
    goto :end
)

if /i "%~1"=="cli" (
    set "REST="
    set "first=1"
    for %%A in (%*) do (
        if !first!==0 (set "REST=!REST! %%A")
        set "first=0"
    )
    py cli.py !REST!
    goto :end
)

py cli.py %*
goto :end

:choose
echo.
echo Select mode:
echo   [1] GUI
echo   [2] CLI interactive
set /p "choice=Enter 1 or 2: "
if "%choice%"=="1" (py gui.py & goto :end)
if "%choice%"=="2" (py cli.py -i & goto :end)
echo Invalid input. Please enter 1 or 2.
goto :choose

:end
