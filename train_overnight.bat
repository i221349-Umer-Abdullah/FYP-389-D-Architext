@echo off
echo ======================================================================
echo ArchiText Overnight Training - Starting...
echo ======================================================================
echo.

cd /d "d:\Work\Uni\FYP\architext"

set GEMINI_API_KEY=AIzaSyBZiW499uG44CyOJWVfw5GyTfK0ssfyEAY

"d:\Work\Uni\FYP\architext\venv\Scripts\python.exe" scripts\overnight_train.py

echo.
echo ======================================================================
echo Training finished! Press any key to close...
pause >nul
