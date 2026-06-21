# ============================================================
#  DROPOUT SWEEP + NAIVE SWEEP only (density 0.27, 500 maps, 10 cores)
#    1. Dropout sweep (sec5.2)  : eval_dropout_sweep @ 0.27  (0/33/50% blind, ON vs OFF; the "why 33%" curve)
#    2. Naive-breaks (sec5.6)   : eval_noise_sweep (naive filter precision collapse) @ 0.27, k=2
#  Shown live AND saved to Phase_CD\Noise_added\results_027\*.txt
#  Run (from D:\Swarm\BTP):
#    powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_dropout_naive_027.ps1
# ============================================================
param([int]$Maps = 500, [int]$Workers = 10)

$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$py   = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
$root = "D:\Swarm\BTP"
Set-Location $root
$out  = "Phase_CD\Noise_added\results_027"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
$M2 = "models\noise_robust_ON_stage2_final.zip"

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " DROPOUT + NAIVE | maps=$Maps | 0.27 | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. dropout sweep (sec5.2)   (live display + UTF-8 log; PS5.1 Tee writes UTF-16, so Write-Host + Out-File)
$log1 = "$out\dropout_sweep_$Maps.txt"
Write-Host "`n--- dropout sweep (sec 5.2)  ->  $log1 ---" -ForegroundColor Yellow
& $py Phase_CD\Collab_Perception\eval_dropout_sweep.py $Maps 0.27 $Workers |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log1 -Encoding utf8
if ($LASTEXITCODE -ne 0) { Write-Host "[!] dropout sweep failed (exit $LASTEXITCODE)" -ForegroundColor Red }

# 2. naive-breaks (sec5.6, k=2)
$log2 = "$out\naive_sweep_$Maps.txt"
Write-Host "`n--- naive-breaks (sec 5.6)  ->  $log2 ---" -ForegroundColor Yellow
& $py Phase_CD\Noise_added\eval_noise_sweep.py $M2 $Maps 2 $Workers |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log2 -Encoding utf8
if ($LASTEXITCODE -ne 0) { Write-Host "[!] naive-breaks failed (exit $LASTEXITCODE)" -ForegroundColor Red }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" DONE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
