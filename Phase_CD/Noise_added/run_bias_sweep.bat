@echo off
REM Assumption-(vi) sensor-bias x noise sweep. Prints live + saves to
REM results_027\bias_sweep_camouflage_500_k2.txt. ~6 h. Uses the biased subclass (pristine env untouched).
powershell -ExecutionPolicy Bypass -File "%~dp0run_bias_sweep.ps1" %*
