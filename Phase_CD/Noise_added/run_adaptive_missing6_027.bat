@echo off
REM cmd wrapper -> the 6 missing adaptive runs (gap/jitter/duty x f=1,2). No array args needed.
powershell -ExecutionPolicy Bypass -File "%~dp0run_adaptive_missing6_027.ps1" %*
