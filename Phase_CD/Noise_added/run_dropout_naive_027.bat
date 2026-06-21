@echo off
REM cmd wrapper -> dropout sweep + naive sweep only (0.27, 500 maps, 10 cores). Pass-through args.
powershell -ExecutionPolicy Bypass -File "%~dp0run_dropout_naive_027.ps1" %*
