@echo off
echo ================================================================================
echo ARCHITEXT - Testing Shap-E Model (SELECTED MODEL)
echo ================================================================================
echo.
echo This will generate a house using Shap-E (our selected model)
echo Expected time: ~30 seconds
echo Output: outputs\shap_e_house_TIMESTAMP.obj
echo.
echo Press any key to start...
pause >nul

echo.
echo [1/2] Activating virtual environment...
call venv\Scripts\activate

echo [2/2] Running Shap-E test...
python tests\test_shap_e.py

echo.
echo ================================================================================
echo Test complete! Check outputs\ folder for the generated .obj file
echo ================================================================================
echo.
pause
