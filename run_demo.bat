@echo off
REM Launch Gradio demo application

echo ============================================================
echo Architext - Launching Demo Application
echo ============================================================
echo.

REM Activate virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting Gradio demo...
echo.
echo The demo will open in your browser automatically.
echo Press Ctrl+C to stop the server.
echo.
echo ============================================================
echo.

python app\demo_app.py

pause
