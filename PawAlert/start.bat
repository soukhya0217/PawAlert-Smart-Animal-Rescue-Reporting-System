@echo off
title PawAlert Starter
echo ================================
echo      Starting PawAlert App
echo ================================
echo.

:: STEP 1 - Check Python
echo Checking Python...
python --version
if errorlevel 1 (
    echo ❌ Python is not installed or not added to PATH
    pause
    exit /b
)

:: STEP 2 - Install backend dependencies
echo.
echo Installing backend dependencies...
python -m pip install -r backend\requirements.txt

:: STEP 3 - Start MongoDB (optional - comment if not installed)
echo.
echo Starting MongoDB...
start cmd /k mongod

:: STEP 4 - Start Backend Server
echo.
echo Starting Backend...
cd backend
start cmd /k python app.py
cd ..

:: STEP 5 - Start Frontend
echo.
echo Starting Frontend...
cd frontend
start cmd /k python -m http.server 8000
cd ..

:: STEP 6 - Open Browser
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul
start http://localhost:8000

echo.
echo ✅ All services started!
echo.
pause