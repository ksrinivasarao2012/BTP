@echo off
REM cmd wrapper -> re-run anchor_OFF + naive-breaks (the two gaps). 500 maps, 10 cores.
powershell -ExecutionPolicy Bypass -File "%~dp0run_anchoroff_naive_027.ps1" %*
