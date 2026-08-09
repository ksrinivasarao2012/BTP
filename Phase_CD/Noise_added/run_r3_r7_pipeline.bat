@echo off
REM cmd wrapper -> R3 comm-loss + R7 density rebuttal experiments (overnight, ~12 h). Add -Wall for wall too.
powershell -ExecutionPolicy Bypass -File "%~dp0run_r3_r7_pipeline.ps1" %*
