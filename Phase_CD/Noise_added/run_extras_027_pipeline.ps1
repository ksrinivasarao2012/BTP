# ============================================================
#  EXTRAS PIPELINE (paper-ready, density 0.27, 500 maps) - groups 2+3+4
#    1. Collab anchor (sec5.2)  : eval_slot_fusion_zero_shot ON + OFF @ 0.27
#    2. Dropout sweep (sec5.2)  : eval_dropout_sweep @ 0.27  (the "why 33%" curve)
#    3. Naive-breaks (sec5.6)   : eval_noise_sweep (naive filter precision collapse) @ 0.27
#  All shown live AND saved to Phase_CD\Noise_added\results_027\*.txt
#  Run (single command, from D:\Swarm\BTP):
#    powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_extras_027_pipeline.ps1
# ============================================================
param([int]$Maps = 500)

# NOTE: not "Stop" - native-exe stderr (pygame warning) must not abort the run.
$ErrorActionPreference = "Continue"
# Force Python to emit UTF-8 (some scripts print Unicode like ~ / box-drawing that the cp1252 console
# can't encode when piped through Tee -> UnicodeEncodeError). UTF-8 mode fixes it.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}   # render UTF-8 box chars cleanly
$py   = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
$root = "D:\Swarm\BTP"
Set-Location $root
$out  = "Phase_CD\Noise_added\results_027"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

$ON   = "models\raster_slot_fusion_ON_stage2_final.zip"
$OFF  = "models\raster_slot_fusion_OFF_stage2_final.zip"
$M2   = "models\noise_robust_ON_stage2_final.zip"
foreach ($m in $ON,$OFF,$M2) {
    if (-not (Test-Path $m)) { Write-Host "[!] model not found: $m - aborting" -ForegroundColor Red; exit 1 }
}

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " EXTRAS PIPELINE | maps=$Maps | density 0.27 | started $t0"   -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

function Run-Step($title, $log, [scriptblock]$cmd) {
    Write-Host "`n--- $title  ->  $log ---" -ForegroundColor Yellow
    # live display + UTF-8 log (PS 5.1 Tee-Object writes UTF-16)
    & $cmd | ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Write-Host "[!] $title failed (exit $LASTEXITCODE)" -ForegroundColor Red }
}

# --- group 2: collab anchor sec5.2 (ON model + OFF model, each at 0.27) ---
Run-Step "anchor ON  (sec5.2)" "$out\anchor_ON_$Maps.txt"  { & $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py $ON  $Maps 0.27 }
Run-Step "anchor OFF (sec5.2)" "$out\anchor_OFF_$Maps.txt" { & $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py $OFF $Maps 0.27 }

# --- group 3: dropout sweep sec5.2 ("why 33%") ---
Run-Step "dropout sweep (sec5.2)" "$out\dropout_sweep_$Maps.txt" { & $py Phase_CD\Collab_Perception\eval_dropout_sweep.py $Maps 0.27 }

# --- group 4: naive-filter-breaks sec5.6 (k=2) ---
Run-Step "naive-breaks (sec5.6)" "$out\naive_sweep_$Maps.txt" { & $py Phase_CD\Noise_added\eval_noise_sweep.py $M2 $Maps 2 10 }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" EXTRAS COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
