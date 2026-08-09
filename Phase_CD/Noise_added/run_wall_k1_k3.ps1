# ============================================================
#  R3 comm-loss on the WALL attack — the two missing traitor counts (k=1 and k=3).
#  (k=2 wall is already done: results_027\comm_loss_wall_500_k2_run2.txt)
#  Runs ONLY the wall comm-loss sweeps — no camouflage, no density (both already complete).
#  Est. ~6-7 h each => ~13 h total. Model + defense unchanged (test-time perturbation only).
#  Run:  Phase_CD\Noise_added\run_wall_k1_k3.bat
# ============================================================
param([int]$Maps = 500, [int]$Workers = 10)

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
Write-Host " R3 WALL comm-loss | k=1 and k=3 | maps=$Maps | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Go "R3 comm-loss WALL (k=1)" "$out\comm_loss_wall_${Maps}_k1.txt" `
   { & $py Phase_CD\Noise_added\eval_comm_loss.py $M2 $Maps 1 $Workers wall }

Go "R3 comm-loss WALL (k=3)" "$out\comm_loss_wall_${Maps}_k3.txt" `
   { & $py Phase_CD\Noise_added\eval_comm_loss.py $M2 $Maps 3 $Workers wall }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" WALL k=1 + k=3 COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
