@echo off

echo ============================================
echo Multi-Agent LLM System Startup
echo ============================================


REM ============================================
REM Activate virtual environment
REM ============================================

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found.
    echo Creating virtual environment...

    python -m venv venv

    call venv\Scripts\activate.bat
)

echo.
echo ============================================
echo Installing requirements
echo ============================================

pip install -r requirements.txt

echo.
echo ============================================
echo Running Multi-Agent Pipeline
echo ============================================

python main.py

echo.
echo ============================================
echo Execution Finished
echo ============================================

pause