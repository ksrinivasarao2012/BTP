# ============================================================
#  ADAPTIVE - the 6 MISSING runs only: gap/jitter/duty x f=1,2
#  (offset f1/f2/f3 and gap/jitter/duty f3 already completed.)
#  Lists are hardcoded here so there is NO array-arg parsing through the .bat.
#  Run:  Phase_CD\Noise_added\run_adaptive_missing6_027.bat
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
$M2 = "models\noise_robust_ON_stage2_final.zip"

$sweeps = @("gap", "jitter", "duty")
$fs     = @(1, 2)
$t0 = Get-Date
$total = $sweeps.Count * $fs.Count
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ADAPTIVE MISSING-6 | maps=$Maps | gap/jitter/duty x f=1,2 | $total runs | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$i = 0
foreach ($s in $sweeps) {
    foreach ($f in $fs) {
        $i++
        $log = "$out\adaptive_${s}_f${f}_$Maps.txt"
        Write-Host "`n--- [$i/$total] $s  f=$f  ->  $log ---" -ForegroundColor Yellow
        & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps $f $Workers $s |
            ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] $s f=$f failed (exit $LASTEXITCODE)" -ForegroundColor Red }
    }
}

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" MISSING-6 COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
