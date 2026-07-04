# ============================================================
#  PHASE 3 RESUME - offset x noise sweep, skip already-complete runs.
#  A log is "complete" if it contains the final "RESULTS -" line.
#  Re-runs partial/missing only (the 2 finished sigma=0 f1/f2 are skipped).
#  Run:  Phase_CD\Noise_added\run_offset_noise_resume_027.bat
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
$M2  = "models\noise_robust_ON_stage2_final.zip"

$sigmas = @(0.0, 0.2, 0.4)
$fs     = @(1, 2, 3)
$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " OFFSET x NOISE RESUME | maps=$Maps | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$i = 0; $total = $sigmas.Count * $fs.Count
foreach ($sigma in $sigmas) {
    foreach ($f in $fs) {
        $i++
        $log = "$out\adaptive_offset_noise_sigma${sigma}_f${f}_$Maps.txt"
        # skip if a COMPLETE log already exists (contains the final RESULTS line)
        if ((Test-Path $log) -and (Select-String -Path $log -Pattern "RESULTS -" -Quiet)) {
            Write-Host "`n--- [$i/$total] sigma=$sigma f=$f  ALREADY COMPLETE, skipping ---" -ForegroundColor DarkGray
            continue
        }
        Write-Host "`n--- [$i/$total] offset x sigma=$sigma f=$f  ->  $log ---" -ForegroundColor Yellow
        & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps $f $Workers offset $sigma |
            ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] sigma=$sigma f=$f failed (exit $LASTEXITCODE)" -ForegroundColor Red }
    }
}

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" RESUME COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
