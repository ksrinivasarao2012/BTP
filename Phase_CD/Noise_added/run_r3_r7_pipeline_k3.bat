@echo off
REM cmd wrapper -> R3 comm-loss + R7 density at k=3 traitors. Run AFTER the k=1 pipeline finishes.
powershell -ExecutionPolicy Bypass -File "%~dp0run_r3_r7_pipeline_k3.ps1" %*
