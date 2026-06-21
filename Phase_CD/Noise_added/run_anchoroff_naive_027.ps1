# ============================================================
#  Re-run the two gaps: anchor_OFF (sec 5.2) + naive-breaks (sec 5.6)
#  (anchor_OFF was interrupted earlier; naive_sweep saved incomplete.)
#  10 cores, 500 maps, density 0.27, clean ASCII + UTF-8 logs.
#  Run:  Phase_CD\Noise_added\run_anchoroff_naive_027.bat
# ============================================================
param([int]$Maps = 500, [int]$Workers = 10)

$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$py   = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
Set-Location "D:\Swarm\BTP"
$out  = "Phase_CD\Noise_added\results_027"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
$OFF = "models\raster_slot_fusion_OFF_stage2_final.zip"
$M2  = "models\noise_robust_ON_stage2_final.zip"

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ANCHOR_OFF + NAIVE | maps=$Maps | 0.27 | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. anchor OFF model (sec 5.2)
$log1 = "$out\anchor_OFF_$Maps.txt"
Write-Host "`n--- anchor OFF (sec 5.2)  ->  $log1 ---" -ForegroundColor Yellow
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py $OFF $Maps 0.27 $Workers |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log1 -Encoding utf8
if ($LASTEXITCODE -ne 0) { Write-Host "[!] anchor OFF failed (exit $LASTEXITCODE)" -ForegroundColor Red }

# 2. naive-breaks (sec 5.6, k=2)
$log2 = "$out\naive_sweep_$Maps.txt"
Write-Host "`n--- naive-breaks (sec 5.6)  ->  $log2 ---" -ForegroundColor Yellow
& $py Phase_CD\Noise_added\eval_noise_sweep.py $M2 $Maps 2 $Workers |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log2 -Encoding utf8
if ($LASTEXITCODE -ne 0) { Write-Host "[!] naive-breaks failed (exit $LASTEXITCODE)" -ForegroundColor Red }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" DONE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
