@echo off
echo ================================================================================
echo ARCHITEXT - Testing Point-E Model (Alternative/Comparison)
echo ================================================================================
echo.
echo This will generate a house using Point-E for comparison
echo Expected time: ~7 minutes (much slower than Shap-E)
echo Output: outputs\point_e_house_TIMESTAMP.obj
echo.
echo WARNING: This takes 7 minutes! Only run if panel specifically requests.
echo.
echo Press any key to start, or close this window to cancel...
pause >nul

echo.
echo [1/2] Activating virtual environment...
call venv\Scripts\activate

echo [2/2] Running Point-E test (this will take several minutes)...
python tests\test_point_e_ultra_optimized.py

echo.
echo ================================================================================
echo Test complete! Check outputs\ folder for the generated .obj file
echo Compare quality and time with Shap-E output
echo ================================================================================
echo.
pause
