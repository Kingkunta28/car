@echo off
REM Starts the Rafiki Car Hire backend (Django) and frontend (Vite) in two windows.
cd /d "%~dp0"
start "Rafiki backend :8000" cmd /k "cd /d "%~dp0backend" && "%~dp0venv\Scripts\python.exe" manage.py runserver"
start "Rafiki frontend :5173" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo.
echo   Website:   http://localhost:5173
echo   Dashboard: http://localhost:5173/admin
echo.
