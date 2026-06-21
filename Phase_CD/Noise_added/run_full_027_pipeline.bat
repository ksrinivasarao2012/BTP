@echo off
REM ============================================================
REM  cmd wrapper -> runs the full 0.27 pipeline (.ps1) with Tee
REM  logging. Just type:  run_full_027_pipeline.bat
REM  Pass-through args, e.g.:  run_full_027_pipeline.bat -SkipTrain
REM ============================================================
powershell -ExecutionPolicy Bypass -File "%~dp0run_full_027_pipeline.ps1" %*
