@echo off
REM Test Point-E model

echo ============================================================
echo Architext - Testing Point-E Model
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

echo Running Point-E tests...
echo This may take several minutes (3-5 min for all tests)
echo.
echo ============================================================
echo.

python tests\test_point_e.py

echo.
echo ============================================================
echo Test Complete!
echo ============================================================
echo.
echo Check the outputs\point_e_tests\ directory for generated models
echo Point cloud files (.ply) can be viewed in MeshLab or CloudCompare
echo.

pause
