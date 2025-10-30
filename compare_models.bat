@echo off
REM Run model comparison tests

echo ============================================================
echo Architext - Model Comparison
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

echo Running comprehensive model comparison...
echo This will test multiple models with the same prompts
echo Expected time: 10-15 minutes
echo.
echo ============================================================
echo.

python tests\model_comparison.py

echo.
echo ============================================================
echo Comparison Complete!
echo ============================================================
echo.
echo Results saved to outputs\comparisons\
echo Check the markdown report for detailed analysis
echo.

pause
