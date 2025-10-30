@echo off
REM Architext Setup Script for Windows
REM This script sets up the Python environment and installs all dependencies

echo ============================================================
echo Architext FYP - Environment Setup
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM Check Python version (must be 3.8+)
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.8 or higher is required
    pause
    exit /b 1
)

echo [OK] Python version is compatible
echo.

REM Create virtual environment
echo ------------------------------------------------------------
echo Creating Python virtual environment...
echo ------------------------------------------------------------

if exist "venv\" (
    echo [WARNING] Virtual environment already exists
    echo Do you want to recreate it? (Y/N)
    set /p RECREATE=
    if /i "%RECREATE%"=="Y" (
        echo Removing old virtual environment...
        rmdir /s /q venv
        python -m venv venv
        echo [OK] Virtual environment recreated
    ) else (
        echo [OK] Using existing virtual environment
    )
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)

echo.

REM Activate virtual environment
echo ------------------------------------------------------------
echo Activating virtual environment...
echo ------------------------------------------------------------

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo ------------------------------------------------------------
echo Upgrading pip...
echo ------------------------------------------------------------

python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)

echo [OK] pip upgraded
echo.

REM Install PyTorch (with CUDA support if available)
echo ------------------------------------------------------------
echo Installing PyTorch...
echo ------------------------------------------------------------
echo.
echo Checking for NVIDIA GPU...

nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [INFO] No NVIDIA GPU detected, installing CPU version
    pip install torch torchvision torchaudio
) else (
    echo [OK] NVIDIA GPU detected, installing CUDA version
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
)

if errorlevel 1 (
    echo [ERROR] Failed to install PyTorch
    pause
    exit /b 1
)

echo [OK] PyTorch installed
echo.

REM Install other dependencies
echo ------------------------------------------------------------
echo Installing dependencies from requirements.txt...
echo ------------------------------------------------------------

pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    echo Please check requirements.txt and try again
    pause
    exit /b 1
)

echo [OK] All dependencies installed
echo.

REM Create necessary directories
echo ------------------------------------------------------------
echo Creating project directories...
echo ------------------------------------------------------------

if not exist "outputs\" mkdir outputs
if not exist "outputs\demo\" mkdir outputs\demo
if not exist "outputs\shap_e_tests\" mkdir outputs\shap_e_tests
if not exist "outputs\point_e_tests\" mkdir outputs\point_e_tests
if not exist "outputs\comparisons\" mkdir outputs\comparisons
if not exist "models\" mkdir models
if not exist "data\" mkdir data

echo [OK] Directories created
echo.

REM Verify installation
echo ------------------------------------------------------------
echo Verifying installation...
echo ------------------------------------------------------------

python -c "import torch; print(f'PyTorch {torch.__version__}')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyTorch not properly installed
    pause
    exit /b 1
)

python -c "import gradio; print(f'Gradio {gradio.__version__}')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Gradio not properly installed
    pause
    exit /b 1
)

python -c "import trimesh; print('Trimesh OK')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Trimesh not properly installed
    pause
    exit /b 1
)

python -c "import diffusers; print(f'Diffusers {diffusers.__version__}')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Diffusers not properly installed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Installation Summary
echo ============================================================
echo.

python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
python -c "import gradio; print(f'Gradio: {gradio.__version__}')"
python -c "import diffusers; print(f'Diffusers: {diffusers.__version__}')"
python -c "import trimesh; print(f'Trimesh: OK')"

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Run: test_shap_e.bat    - Test Shap-E model
echo 2. Run: test_point_e.bat   - Test Point-E model
echo 3. Run: run_demo.bat       - Launch Gradio demo
echo 4. Run: compare_models.bat - Compare all models
echo.
echo To manually activate the environment later:
echo   venv\Scripts\activate.bat
echo.

pause
