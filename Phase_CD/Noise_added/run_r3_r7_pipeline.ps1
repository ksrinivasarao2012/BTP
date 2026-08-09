# ============================================================
#  R3 (comm-loss) + R7 (density) rebuttal experiments — overnight.
#  Default: comm-loss CAMOUFLAGE (~9-10 h) + density CAMOUFLAGE (~2.5 h) = ~12 h.
#  Add -Wall to also run comm-loss on the wall attack (+~10 h).
#  Model + defense are UNCHANGED (no retraining); these are test-time perturbations.
#  Run:  Phase_CD\Noise_added\run_r3_r7_pipeline.bat
# ============================================================
param([int]$Maps = 500, [int]$Workers = 10, [int]$K = 2, [switch]$Wall)

$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$py  = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
Set-Location "D:\Swarm\BTP"
$out = "Phase_CD\Noise_added\results_027"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
$M2  = "models\noise_robust_ON_stage2_final.zip"

function Go($title, $log, [scriptblock]$cmd) {
    Write-Host "`n--- $title  ->  $log ---" -ForegroundColor Yellow
    & $cmd | ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Write-Host "[!] $title failed (exit $LASTEXITCODE)" -ForegroundColor Red }
}

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " R3+R7 REBUTTAL | maps=$Maps | k=$K | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# R3 comm-loss (camouflage = the decisive stealthy attack)
Go "R3 comm-loss camouflage" "$out\comm_loss_camouflage_$Maps.txt" `
   { & $py Phase_CD\Noise_added\eval_comm_loss.py $M2 $Maps $K $Workers camouflage }

if ($Wall) {
    Go "R3 comm-loss wall" "$out\comm_loss_wall_$Maps.txt" `
       { & $py Phase_CD\Noise_added\eval_comm_loss.py $M2 $Maps $K $Workers wall }
}

# R7 density generalization (camouflage, sigma=0.6 headline cell)
Go "R7 density camouflage" "$out\density_sweep_camouflage_$Maps.txt" `
   { & $py Phase_CD\Noise_added\eval_density_sweep.py $M2 $Maps $K $Workers camouflage }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" R3+R7 COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
