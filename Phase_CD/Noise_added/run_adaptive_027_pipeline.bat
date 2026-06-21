@echo off
REM cmd wrapper -> adaptive-attacker pipeline (offset/gap/jitter/duty x f=1,2,3). Pass-through args.
powershell -ExecutionPolicy Bypass -File "%~dp0run_adaptive_027_pipeline.ps1" %*
