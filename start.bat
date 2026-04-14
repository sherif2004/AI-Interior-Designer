@echo off
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║    AI Interior Designer — Starting...    ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check .env exists
if not exist "backend\.env" (
    echo  [!] backend\.env not found.
    echo  [!] Copy backend\.env.example to backend\.env and add your OpenRouter API key.
    echo.
    copy backend\.env.example backend\.env
    echo  [+] Created backend\.env from template. Please edit it and add your OPENROUTER_API_KEY.
    pause
    exit /b 1
)

echo  [+] Starting FastAPI backend on http://localhost:8000 ...
echo  [+] Frontend available at http://localhost:8000
echo.
echo  Press Ctrl+C to stop.
echo.

:: Start backend (serves frontend from /)
D:\anaconda\python.exe -m uvicorn backend.api.server:app --reload --host 0.0.0.0 --port 8000
