@echo off
chcp 65001 >nul
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

REM Reload .env on every run (overwrites any stale session variables
REM left by a previous run, so edits to .env always take effect).
if exist "%~dp0.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
        if "%%B"=="" (set "%%A=") else (set "%%A=%%B")
    )
)

if not defined OPENAI_API_KEY (
    echo [ERROR] OPENAI_API_KEY not found in .env. See comments at top of run.bat.
    pause
    exit /b 1
)

:choose
echo.
echo Select mode:
echo   [1] GUI
echo   [2] CLI interactive
set /p "choice=Enter 1 or 2: "
if "%choice%"=="1" goto :run_gui
if "%choice%"=="2" goto :run_cli
echo Invalid input. Please enter 1 or 2.
goto :choose

:run_gui
py gui.py
goto :end

:run_cli
py cli.py -i
goto :end

:end
