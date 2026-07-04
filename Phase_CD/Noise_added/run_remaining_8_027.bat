@echo off
REM cmd wrapper to run the 8 remaining adaptive sweeps.
powershell -ExecutionPolicy Bypass -File "%~dp0run_remaining_8_027.ps1" %*
pause
