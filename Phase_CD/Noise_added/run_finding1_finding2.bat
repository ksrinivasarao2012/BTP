@echo off
REM ============================================================================
REM  run_finding1_finding2.bat
REM  Reruns the two open items from the 2026-07-18/19 review:
REM    #2  dropout single-policy ABLATION  (reconciles tab:anchor vs tab:dropout)
REM    #1  majority proof: temporal eval at f = 4,5,6,7 x CAMOUFLAGE
REM        (f=4 honest-majority | f=5 tie | f=6,7 honest-MINORITY -> proves the
REM         defense operates without an honest local majority)
REM  All output Tee-style redirected into results_027\ .
REM  Est. total wall-clock ~= 11 h (see per-stage notes). Run overnight.
REM ============================================================================

set PY=C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe
set TEMPORAL=D:\Swarm\BTP\Phase_CD\Noise_added\eval_temporal.py
set DROPABL=D:\Swarm\BTP\Phase_CD\Collab_Perception\eval_dropout_ablation.py
set DROPABLN=D:\Swarm\BTP\Phase_CD\Noise_added\eval_dropout_ablation_noisy.py
set OUT=D:\Swarm\BTP\Phase_CD\Noise_added\results_027
set BASE=models/noise_robust_ON_stage2_final.zip
set OFFMODEL=models/raster_slot_fusion_OFF_stage2_final.zip

cd /d D:\Swarm\BTP

echo ============================================================================
echo  [%DATE% %TIME%]  BATCH START
echo ============================================================================

REM ---- #2: dropout single-policy ablation (~45-60 min) -----------------------
echo [%DATE% %TIME%]  #2  dropout ablation  -^> dropout_ablation_500.txt
"%PY%" "%DROPABL%" %OFFMODEL% 500 0.27 10 > "%OUT%\dropout_ablation_500.txt" 2>&1
echo [%DATE% %TIME%]  #2  done

REM ---- #3: same ablation on the ATTACKED model (one-lineage consistency) ------
echo [%DATE% %TIME%]  #3  attacked-model ablation  -^> dropout_ablation_noisy_500.txt
"%PY%" "%DROPABLN%" %BASE% 500 0.27 10 > "%OUT%\dropout_ablation_noisy_500.txt" 2>&1
echo [%DATE% %TIME%]  #3  done  (10%% ON should read ~86, gap ~+40 pp)

REM ---- #1: majority proof, camouflage, f = 4,5,6,7 (~2.5 h each) -------------
echo [%DATE% %TIME%]  #1  f=4 camouflage  -^> eval_f4_camouflage_500.txt
"%PY%" "%TEMPORAL%" %BASE% 500 4 10 camouflage > "%OUT%\eval_f4_camouflage_500.txt" 2>&1
echo [%DATE% %TIME%]  #1  f=4 done

echo [%DATE% %TIME%]  #1  f=5 camouflage  -^> eval_f5_camouflage_500.txt
"%PY%" "%TEMPORAL%" %BASE% 500 5 10 camouflage > "%OUT%\eval_f5_camouflage_500.txt" 2>&1
echo [%DATE% %TIME%]  #1  f=5 done

echo [%DATE% %TIME%]  #1  f=6 camouflage  -^> eval_f6_camouflage_500.txt
"%PY%" "%TEMPORAL%" %BASE% 500 6 10 camouflage > "%OUT%\eval_f6_camouflage_500.txt" 2>&1
echo [%DATE% %TIME%]  #1  f=6 done

echo [%DATE% %TIME%]  #1  f=7 camouflage  -^> eval_f7_camouflage_500.txt
"%PY%" "%TEMPORAL%" %BASE% 500 7 10 camouflage > "%OUT%\eval_f7_camouflage_500.txt" 2>&1
echo [%DATE% %TIME%]  #1  f=7 done

echo ============================================================================
echo  [%DATE% %TIME%]  BATCH COMPLETE
echo    #2 result : dropout_ablation_500.txt         (10%% row should read ~89.3 / 45.9)
echo    #3 result : dropout_ablation_noisy_500.txt   (10%% ON ~86, gap ~+40 pp)
echo    #1 results: eval_f{4,5,6,7}_camouflage_500.txt  (check recovery CI ^> 0 at f=6,7)
echo ============================================================================
