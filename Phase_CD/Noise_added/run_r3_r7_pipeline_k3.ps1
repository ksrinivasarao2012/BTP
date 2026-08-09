# ============================================================
#  R3 (comm-loss) + R7 (density) rebuttal experiments — f=3 traitors.
#  Same protocol as run_r3_r7_pipeline.ps1 (k=2 default) but for k=3.
#  Filenames carry a _k3 suffix so they do NOT collide with the k=2 logs.
#  Est. ~10-12 h (same scope as the k=2 run: comm-loss ~9-10h + density ~2.5h).
#  DO NOT run this at the same time as the k=1 or k=2 pipeline — all three
#  want the full 10 cores; run them one after another.
#  Run:  Phase_CD\Noise_added\run_r3_r7_pipeline_k3.bat
# ============================================================
param([int]$Maps = 500, [int]$Workers = 10)

$K = 3
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
Write-Host " R3+R7 REBUTTAL (k=3) | maps=$Maps | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Go "R3 comm-loss camouflage (k=3)" "$out\comm_loss_camouflage_${Maps}_k3.txt" `
   { & $py Phase_CD\Noise_added\eval_comm_loss.py $M2 $Maps $K $Workers camouflage }

Go "R7 density camouflage (k=3)" "$out\density_sweep_camouflage_${Maps}_k3.txt" `
   { & $py Phase_CD\Noise_added\eval_density_sweep.py $M2 $Maps $K $Workers camouflage }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" R3+R7 (k=3) COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
