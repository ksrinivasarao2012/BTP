@echo off
REM cmd wrapper -> recovery run (5 lost adaptive + anchor_OFF + dropout + naive). Run AFTER missing-6 finishes.
powershell -ExecutionPolicy Bypass -File "%~dp0run_recover_027.ps1" %*
