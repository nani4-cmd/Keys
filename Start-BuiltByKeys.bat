@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 beginner.py
if errorlevel 1 pause
exit /b
:use_python
where python >nul 2>nul
if errorlevel 1 goto missing
python beginner.py
if errorlevel 1 pause
exit /b
:missing
echo Install Python 3.10 or newer from python.org with Tcl/Tk and the Python launcher enabled.
echo See WINDOWS.md for setup instructions.
pause
