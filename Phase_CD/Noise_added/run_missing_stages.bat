@echo off
REM ============================================================================
REM  run_missing_stages.bat
REM  Runs 3 of the 4 stages the old batch skipped on 2026-07-20 (cmd.exe jumped
REM  from "f=1 wall done" straight to the bias sweep, leaping over these).
REM      1) anchor ON     2) probe oracle     3) probe realistic
REM
REM  f=3 wall is DEFERRED on purpose (user's call, 2026-07-20). It is still
REM  OUTSTANDING -- one of the 7 reconstructed files is not yet pristine.
REM  When you want it, run this single line from D:\Swarm\BTP :
REM      "%PY%" "%TEMPORAL%" %BASE% 500 3 6 wall > "%OUT%\eval_f3_wall_500.txt" 2>&1
REM  NOTE: a PARTIAL eval_f3_wall_500.txt from the aborted 15:10 run is on disk.
REM  It is INCOMPLETE -- delete it or overwrite it before trusting that filename.
REM
REM  SKIP-PROOF: no CALL, no GOTO, no labels, no parenthesised blocks -- purely
REM  sequential lines. cmd has no seek-back offset to corrupt this time.
REM  MEMORY-SAFE: 6 workers instead of 10. The bias sweep deadlocked at 85%% RAM
REM  with 10 workers all at 0%% CPU; 6 keeps well clear of that wall.
REM
REM  Output -> results_027\rerun\ . Markers also appended to
REM  rerun\_missing_stages_log.txt . Est. total ~1 h 55 m at 6 workers.
REM ============================================================================

set PY=C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe
set TEMPORAL=D:\Swarm\BTP\Phase_CD\Noise_added\eval_temporal.py
set PROBE=D:\Swarm\BTP\Phase_CD\Noise_added\probe_temporal_offset.py
set ANCHOR=D:\Swarm\BTP\Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py
set OUT=D:\Swarm\BTP\Phase_CD\Noise_added\results_027\rerun
set LOG=%OUT%\_missing_stages_log.txt
set BASE=models/noise_robust_ON_stage2_final.zip
set ONMODEL=models/raster_slot_fusion_ON_stage2_final.zip

cd /d D:\Swarm\BTP
if not exist "%OUT%" mkdir "%OUT%"

echo ============================================================
echo  MISSING-STAGES RERUN START  -  6 workers, 3 stages
echo  f=3 wall is deferred and still outstanding.
echo ============================================================
echo [%DATE% %TIME%] MISSING-STAGES RERUN START, 6 workers, 3 stages >>"%LOG%"

REM ---- 1/3  anchor ON  -- reconstructed file, approx 20 min at 6w ----------
echo [%DATE% %TIME%] 1/3  anchor ON start, approx 20m
echo [%DATE% %TIME%] 1/3  anchor ON start >>"%LOG%"
"%PY%" "%ANCHOR%" %ONMODEL% 500 0.27 6 > "%OUT%\anchor_ON_500.txt" 2>&1
echo [%DATE% %TIME%] 1/3  anchor ON done, ON arm should read approx 87.7
echo [%DATE% %TIME%] 1/3  anchor ON done >>"%LOG%"
if exist "%OUT%\anchor_ON_500.txt" echo        OK file created
if not exist "%OUT%\anchor_ON_500.txt" echo        WARNING file MISSING

REM ---- 2/3  probe ORACLE at 500 maps -- approx 45 min at 6w ----------------
echo [%DATE% %TIME%] 2/3  probe oracle start, approx 45m
echo [%DATE% %TIME%] 2/3  probe oracle start >>"%LOG%"
"%PY%" "%PROBE%" %BASE% 500 2 6 camouflage 0.6 > "%OUT%\probe_oracle_500.txt" 2>&1
echo [%DATE% %TIME%] 2/3  probe oracle done, AUC approx 0.99 expected
echo [%DATE% %TIME%] 2/3  probe oracle done >>"%LOG%"
if exist "%OUT%\probe_oracle_500.txt" echo        OK file created
if not exist "%OUT%\probe_oracle_500.txt" echo        WARNING file MISSING

REM ---- 3/3  probe REALISTIC at 500 maps -- approx 50 min at 6w -------------
echo [%DATE% %TIME%] 3/3  probe realistic start, approx 50m
echo [%DATE% %TIME%] 3/3  probe realistic start >>"%LOG%"
"%PY%" "%PROBE%" %BASE% 500 2 6 camouflage 0.6 --assoc realistic > "%OUT%\probe_realistic_500.txt" 2>&1
echo [%DATE% %TIME%] 3/3  probe realistic done, AUC approx 0.85 to 0.90 expected
echo [%DATE% %TIME%] 3/3  probe realistic done >>"%LOG%"
if exist "%OUT%\probe_realistic_500.txt" echo        OK file created
if not exist "%OUT%\probe_realistic_500.txt" echo        WARNING file MISSING

echo ============================================================
echo  MISSING-STAGES RERUN COMPLETE  -  3 of 3 done
echo  STILL OUTSTANDING: f=3 wall  -  6 of 7 reconstructed files
echo  are pristine; eval_f3_wall_500.txt is NOT yet redone.
echo ============================================================
echo [%DATE% %TIME%] MISSING-STAGES RERUN COMPLETE, f=3 wall still outstanding >>"%LOG%"
