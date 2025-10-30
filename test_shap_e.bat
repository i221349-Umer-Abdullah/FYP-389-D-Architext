@echo off
REM Test Shap-E model

echo ============================================================
echo Architext - Testing Shap-E Model
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

echo Running Shap-E tests...
echo This may take several minutes (5-10 min for all tests)
echo.
echo ============================================================
echo.

python tests\test_shap_e.py

echo.
echo ============================================================
echo Test Complete!
echo ============================================================
echo.
echo Check the outputs\shap_e_tests\ directory for generated models
echo Open .obj files in Blender, MeshLab, or your 3D viewer
echo.

pause
