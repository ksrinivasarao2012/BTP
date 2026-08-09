@echo off
REM Runs ONLY the missing WALL comm-loss sweeps: k=1 then k=3 (~13 h total).
REM k=2 wall already done. No camouflage / density re-runs.
powershell -ExecutionPolicy Bypass -File "%~dp0run_wall_k1_k3.ps1" %*
