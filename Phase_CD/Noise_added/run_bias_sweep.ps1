# ============================================================
#  Assumption-(vi) study: does a per-agent SYSTEMATIC sensor bias break the temporal filter?
#  Sweeps noise sigma {0,0.2,0.4,0.6} x per-agent bias {0,0.2,0.4,0.6} at camouflage, k=2.
#  Prints LIVE to the terminal AND saves to results_027\bias_sweep_camouflage_500_k2.txt.
#  ~6 h (64 conds x 500 maps). Uses the BIASED SUBCLASS -> pristine env untouched.
#  Run:  Phase_CD\Noise_added\run_bias_sweep.bat
# ============================================================
param([int]$Maps = 500, [int]$Workers = 10, [int]$K = 2, [string]$Attack = "camouflage")

$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$py  = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
Set-Location "D:\Swarm\BTP"
$out = "Phase_CD\Noise_added\results_027"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
$M2  = "models\noise_robust_ON_stage2_final.zip"
$log = "$out\bias_sweep_${Attack}_${Maps}_k${K}.txt"

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SENSOR-BIAS x NOISE SWEEP | $Attack | k=$K | maps=$Maps | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host " -> $log" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# live-to-terminal AND tee-to-file (same pattern as run_r3_r7_pipeline)
& $py Phase_CD\Noise_added\eval_bias_sweep.py $M2 $Maps $K $Workers $Attack |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" BIAS SWEEP COMPLETE in {0:hh\:mm\:ss}.  Log: {1}" -f $dt, $log) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
