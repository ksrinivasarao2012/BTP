@echo off
REM cmd wrapper -> Phase 3: offset x noise sweep (9 runs). EDIT eval_adaptive_attack.py LINE 47 FIRST!
powershell -ExecutionPolicy Bypass -File "%~dp0run_offset_noise_027.ps1" %*
