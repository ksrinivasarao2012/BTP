# ============================================================
#  FULL 0.27 PIPELINE (paper-ready)
#    STEP 2 : Stage-2 lock-in training (1.5M steps, sigma~U[0,0.6] @ density 0.27)
#    STEP 3 : f = 1,2,3 eval matrix @ 500 maps  (wall + camouflage, randomized attack ON)
#  Each eval is shown live AND saved to Phase_CD\Noise_added\results_027\*.txt
#  Run (single command, from D:\Swarm\BTP):
#    powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_full_027_pipeline.ps1
#  Skip training (model already exists) and only run the evals:
#    powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_full_027_pipeline.ps1 -SkipTrain
# ============================================================
param([switch]$SkipTrain, [int]$Maps = 500)

# NOTE: do NOT use "Stop" here. Native-exe stderr (e.g. pygame's harmless pkg_resources warning)
# gets wrapped by PowerShell as a NativeCommandError; with Stop that would abort the run.
$ErrorActionPreference = "Continue"
# Force Python UTF-8 output (avoids cp1252 UnicodeEncodeError on ~ / box-drawing chars when piped to Tee).
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}   # render UTF-8 box chars cleanly
$py   = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
$root = "D:\Swarm\BTP"
Set-Location $root
$out  = "Phase_CD\Noise_added\results_027"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
$M = "models\noise_robust_ON_stage2_final.zip"

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " FULL 0.27 PIPELINE  | maps=$Maps | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ---- STEP 2: training ----
if ($SkipTrain) {
    Write-Host "[*] -SkipTrain set; using existing $M" -ForegroundColor Yellow
} else {
    Write-Host "`n=== STEP 2: Stage-2 0.27 lock-in training (1.5M steps) ===" -ForegroundColor Cyan
    & $py Phase_CD\Noise_added\train_noise_robust.py 2
    if ($LASTEXITCODE -ne 0) { Write-Host "[!] training failed (exit $LASTEXITCODE) - aborting" -ForegroundColor Red; exit 1 }
}
if (-not (Test-Path $M)) { Write-Host "[!] model not found: $M - aborting" -ForegroundColor Red; exit 1 }
Write-Host "[*] model ready: $M" -ForegroundColor Green

# ---- STEP 3: f = 1,2,3 eval matrix @ $Maps maps ----
Write-Host "`n=== STEP 3: f=1,2,3 eval matrix @ $Maps maps ===" -ForegroundColor Cyan
foreach ($f in 1,2,3) {
    foreach ($a in "wall","camouflage") {
        $log = Join-Path $out ("eval_f{0}_{1}_{2}.txt" -f $f, $a, $Maps)
        Write-Host "`n--- f=$f  $a  ->  $log ---" -ForegroundColor Yellow
        # stdout -> Tee (console + file); stderr (pygame warning) flows straight to the console, NOT
        # into the pipeline, so it is never wrapped as a NativeCommandError.
        & $py Phase_CD\Noise_added\eval_temporal.py $M $Maps $f 10 $a |
            ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] eval f=$f $a failed (exit $LASTEXITCODE)" -ForegroundColor Red }
    }
}

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" PIPELINE COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
