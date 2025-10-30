@echo off
echo ================================================================================
echo ARCHITEXT - Testing TripoSR Model (Experimental)
echo ================================================================================
echo.
echo This will generate a house using TripoSR (text-to-image-to-3D pipeline)
echo Expected time: ~2 minutes
echo Output: outputs\multi_model_test\triposr_TIMESTAMP.obj
echo.
echo Note: This is an experimental model showing alternative approaches
echo.
echo Press any key to start...
pause >nul

echo.
echo [1/2] Activating virtual environment...
call venv\Scripts\activate

echo [2/2] Running TripoSR test (includes Stable Diffusion)...
python tests\test_multi_model.py

echo.
echo ================================================================================
echo Test complete! Check outputs\multi_model_test\ folder
echo ================================================================================
echo.
pause
