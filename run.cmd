@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Check dependencies: PyQt5 and openai
py -c "import PyQt5, openai" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Missing dependencies: PyQt5 / openai.
    set /p "ans=Install now? [y/N] "
    if /i "!ans!"=="y" (
        py -m pip install -r requirements.txt
    ) else (
        echo Please run: py -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

REM Load .env (reloaded on every run)
if exist "%~dp0.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
        if "%%B"=="" (set "%%A=") else (set "%%A=%%B")
    )
)

if not defined OPENAI_API_KEY (
    echo [ERROR] OPENAI_API_KEY not found in .env
    pause
    exit /b 1
)

REM Mode selection and argument passing
if "%~1"=="" goto :choose

if /i "%~1"=="gui" (
    set "REST="
    set "first=1"
    for %%A in (%*) do (
        if !first!==0 (set "REST=!REST! %%A")
        set "first=0"
    )
    py gui.py !REST!
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
