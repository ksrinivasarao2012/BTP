@echo off
REM ============================================================================
REM  run_rerun_verification.bat
REM  Re-runs the RECONSTRUCTED / provenance-weak artifacts to get PRISTINE
REM  console logs, written to  results_027\rerun\  (does NOT touch the
REM  originals in results_027\), so old vs new can be diffed side by side.
REM
REM  Covers the 4 review tasks (2026-07-19 data-integrity audit):
REM    A) 6 f-sweep reconstructed files : eval_f1/f2/f3 x {wall,camouflage}
REM    B) anchor ON arm (reconstructed) : eval_slot_fusion_zero_shot on ON model
REM    C) probe @ 500 maps (was 150-map dev) : oracle + realistic association
REM    D) bias sweep (empty/aborted file)    : eval_bias_sweep  [LONG, run LAST]
REM
REM  LOGS: every run is redirected  > rerun\<same-name>.txt 2>&1  so the FULL
REM  progress log + results block are captured (that IS the pristine artifact).
REM  A timestamped master log is also appended to  rerun\_rerun_batch_log.txt .
REM
REM  Realistic wall-clock (from 2026-07-19 measured timings): ~16-19 h total.
REM  Ordered so the critical HEADLINE files finish first; bias sweep is last.
REM  Run overnight. Nothing here overwrites results_027\ originals.
REM ============================================================================

set PY=C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe
set TEMPORAL=D:\Swarm\BTP\Phase_CD\Noise_added\eval_temporal.py
set BIAS=D:\Swarm\BTP\Phase_CD\Noise_added\eval_bias_sweep.py
set PROBE=D:\Swarm\BTP\Phase_CD\Noise_added\probe_temporal_offset.py
set ANCHOR=D:\Swarm\BTP\Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py
set ENVSTATS=D:\Swarm\BTP\Phase_CD\measure_env_stats.py
set OUT=D:\Swarm\BTP\Phase_CD\Noise_added\results_027\rerun
set LOG=%OUT%\_rerun_batch_log.txt
set BASE=models/noise_robust_ON_stage2_final.zip
set ONMODEL=models/raster_slot_fusion_ON_stage2_final.zip

cd /d D:\Swarm\BTP
if not exist "%OUT%" mkdir "%OUT%"

call :log "============================================================"
call :log " RERUN / VERIFICATION BATCH START"
call :log " output to results_027\rerun\  (originals untouched)"
call :log "============================================================"

REM ---- E) env stats: INSTANT smoke test + verifies setup.tex numbers --------
REM     Confirms the env loads before the ~16 h of heavy runs, and regenerates
REM     obstacle count (~29.7), range (15-56), mean radius (~0.91 m) at 0.27.
REM     NOTE: this script does NOT report the 96.8%% solvable figure -- that is
REM     a separate solvability check, not covered by this run.
call :log "E  env stats @ density 0.27, 500 maps (instant)  file env_stats_027.txt"
"%PY%" "%ENVSTATS%" 0.27 500 > "%OUT%\env_stats_027.txt" 2>&1
call :log "E  env stats done  (expect count ~29.7, range 15-56, mean r ~0.91 m)"

REM ---- A) HEADLINE f=2 first (main result table tab:temporal) ---------------
call :log "A  f=2 camouflage  (~2.0h)  file eval_f2_camouflage_500.txt"
"%PY%" "%TEMPORAL%" %BASE% 500 2 10 camouflage > "%OUT%\eval_f2_camouflage_500.txt" 2>&1
call :log "A  f=2 camouflage done"

call :log "A  f=2 wall  (~1.6h)  file eval_f2_wall_500.txt"
"%PY%" "%TEMPORAL%" %BASE% 500 2 10 wall > "%OUT%\eval_f2_wall_500.txt" 2>&1
call :log "A  f=2 wall done"

REM ---- A) f=1 and f=3 (tab:headline rows + vulnerability numbers) ------------
call :log "A  f=1 camouflage  (~1.8h)  file eval_f1_camouflage_500.txt"
"%PY%" "%TEMPORAL%" %BASE% 500 1 10 camouflage > "%OUT%\eval_f1_camouflage_500.txt" 2>&1
call :log "A  f=1 camouflage done"

call :log "A  f=3 camouflage  (~2.2h)  file eval_f3_camouflage_500.txt"
"%PY%" "%TEMPORAL%" %BASE% 500 3 10 camouflage > "%OUT%\eval_f3_camouflage_500.txt" 2>&1
call :log "A  f=3 camouflage done"

call :log "A  f=1 wall  (~1.5h)  file eval_f1_wall_500.txt"
"%PY%" "%TEMPORAL%" %BASE% 500 1 10 wall > "%OUT%\eval_f1_wall_500.txt" 2>&1
call :log "A  f=1 wall done"

call :log "A  f=3 wall  (~1.8h)  file eval_f3_wall_500.txt"
"%PY%" "%TEMPORAL%" %BASE% 500 3 10 wall > "%OUT%\eval_f3_wall_500.txt" 2>&1
call :log "A  f=3 wall done"

REM ---- B) anchor ON arm (quick ~15 min) -------------------------------------
call :log "B  anchor ON (slot-fusion zero-shot, ON model, ~15m)  file anchor_ON_500.txt"
"%PY%" "%ANCHOR%" %ONMODEL% 500 0.27 10 > "%OUT%\anchor_ON_500.txt" 2>&1
call :log "B  anchor ON done  (ON arm should read ~87.7)"

REM ---- C) probe @ 500 maps (fixes the 150-map dev provenance; ~1 h) ----------
call :log "C  probe ORACLE @500 (~30m)  file probe_oracle_500.txt"
"%PY%" "%PROBE%" %BASE% 500 2 10 camouflage 0.6 > "%OUT%\probe_oracle_500.txt" 2>&1
call :log "C  probe oracle done  (AUC ~0.99 expected)"

call :log "C  probe REALISTIC @500 (~30m)  file probe_realistic_500.txt"
"%PY%" "%PROBE%" %BASE% 500 2 10 camouflage 0.6 --assoc realistic > "%OUT%\probe_realistic_500.txt" 2>&1
call :log "C  probe realistic done  (AUC ~0.85-0.90 expected)"

REM ---- D) bias sweep (assumption vi; LONG ~6-7 h; run LAST) ------------------
call :log "D  bias sweep 64 conds (~6-7h)  file bias_sweep_camouflage_500_k2.txt"
"%PY%" "%BIAS%" %BASE% 500 2 10 camouflage > "%OUT%\bias_sweep_camouflage_500_k2.txt" 2>&1
call :log "D  bias sweep done"

call :log "============================================================"
call :log " RERUN BATCH COMPLETE.  Diff rerun\ against results_027\ to"
call :log " confirm 'numbers unchanged' on the 7 reconstructed files."
call :log "============================================================"
goto :end

:log
echo [%DATE% %TIME%] %~1
echo [%DATE% %TIME%] %~1 >>"%LOG%"
goto :eof

:end
