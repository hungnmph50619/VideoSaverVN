@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py web_app.py
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python is missing. Please install Python and try again.
        pause
        exit /b 1
    )
    python web_app.py
)
if errorlevel 1 (
    echo.
    echo VideoSaver VN could not start. Check the error above.
    pause
)
