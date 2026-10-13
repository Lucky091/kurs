@echo off
setlocal
cd /d "%~dp0"
set "PYGAME_HIDE_SUPPORT_PROMPT=1"

if exist ".venv\Scripts\python.exe" goto check_runtime
echo Creating a local Python environment...
where py >nul 2>&1
if errorlevel 1 goto use_python
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto use_python
py -3 -m venv ".venv"
goto environment_created

:use_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto python_error
python -m venv ".venv"

:environment_created
if errorlevel 1 goto setup_error

:check_runtime
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto python_error
".venv\Scripts\python.exe" -c "import pygame" >nul 2>&1
if not errorlevel 1 goto start_game
echo Installing Pygame. Internet is needed only for this first installation.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_error

:start_game
echo Starting Star Frontier...
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 goto game_error
exit /b 0

:python_error
echo Python 3.11 or newer was not found. Install it from https://www.python.org/
echo If this project has an old .venv, rename that folder and run this launcher again.
pause
exit /b 1

:setup_error
echo Environment setup failed. Check the messages above and your network connection.
echo You can install requirements manually using the commands in README.md.
pause
exit /b 1

:game_error
echo The game stopped with an error. Check the messages above.
pause
exit /b 1
