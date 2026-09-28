@echo off
setlocal
set "PIGGYPLAN_DIR=%~dp0"
set "PIGGYPLAN_PYTHONW="

for %%V in (314 313 312 311 310 39 38) do (
  if not defined PIGGYPLAN_PYTHONW if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe" set "PIGGYPLAN_PYTHONW=%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"
)

if not defined PIGGYPLAN_PYTHONW (
  for /f "delims=" %%P in ('where pythonw.exe 2^>nul') do if not defined PIGGYPLAN_PYTHONW set "PIGGYPLAN_PYTHONW=%%P"
)

if defined PIGGYPLAN_PYTHONW (
  start "PiggyPlan" "%PIGGYPLAN_PYTHONW%" "%PIGGYPLAN_DIR%piggyplan_desktop.py"
  exit /b 0
)

if exist "%PIGGYPLAN_DIR%dist\PiggyPlan\PiggyPlan.exe" (
  start "PiggyPlan" "%PIGGYPLAN_DIR%dist\PiggyPlan\PiggyPlan.exe"
  exit /b 0
)

echo PiggyPlan requires Python 3.10 or newer.
echo Please install Python from https://www.python.org/downloads/windows/
pause
exit /b 1
