# ============================================================
#  ADAPTIVE-ATTACKER PIPELINE (paper-ready, density 0.27, 500 maps) - group 5
#  Filter-aware attacker sweeps (FIXED radius so the swept axis isn't confounded):
#    offset  = stealth/harm bind  (THE reviewer-rebuttal figure)
#    gap     = surface-gap robustness
#    jitter  = zero-mean jitter doesn't beat the mean test
#    duty    = intermittent lying only dilutes
#  Each at f = 1, 2, 3  (Option 2 full symmetry) = 12 runs.
#  All shown live AND saved to Phase_CD\Noise_added\results_027\adaptive_*.txt
#  Run (single command, from D:\Swarm\BTP):
#    powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_adaptive_027_pipeline.ps1
#  Subset, e.g. only the bind figure across f:
#    powershell ... run_adaptive_027_pipeline.ps1 -Sweeps offset
# ============================================================
param([int]$Maps = 500, [int[]]$F = @(1,2,3), [string[]]$Sweeps = @("offset","gap","jitter","duty"))

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
$M2 = "models\noise_robust_ON_stage2_final.zip"
if (-not (Test-Path $M2)) { Write-Host "[!] model not found: $M2 - aborting" -ForegroundColor Red; exit 1 }

$t0 = Get-Date
$total = $Sweeps.Count * $F.Count
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ADAPTIVE PIPELINE | maps=$Maps | f=$($F -join ',') | sweeps=$($Sweeps -join ',') | $total runs | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$i = 0
foreach ($s in $Sweeps) {
    foreach ($f in $F) {
        $i++
        $log = "$out\adaptive_${s}_f${f}_$Maps.txt"
        Write-Host "`n--- [$i/$total] $s  f=$f  ->  $log ---" -ForegroundColor Yellow
        # live display + UTF-8 log (PS 5.1 Tee-Object writes UTF-16, so use Write-Host + Out-File utf8)
        & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps $f 10 $s |
            ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] $s f=$f failed (exit $LASTEXITCODE)" -ForegroundColor Red }
    }
}

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" ADAPTIVE COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
