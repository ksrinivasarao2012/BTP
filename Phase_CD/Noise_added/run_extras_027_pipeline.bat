@echo off
REM cmd wrapper -> extras pipeline (anchor + dropout + naive). Pass-through args.
powershell -ExecutionPolicy Bypass -File "%~dp0run_extras_027_pipeline.ps1" %*
