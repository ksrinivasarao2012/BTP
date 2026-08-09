@echo off
REM cmd wrapper -> R3 comm-loss + R7 density at k=1 traitor. Run AFTER the k=2 pipeline finishes.
powershell -ExecutionPolicy Bypass -File "%~dp0run_r3_r7_pipeline_k1.ps1" %*
