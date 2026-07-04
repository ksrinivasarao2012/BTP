# ============================================================
#  PHASE 3 - OFFSET × NOISE SWEEP (full, 9 runs)
#  offset × σ{0.0, 0.2, 0.4} × f{1, 2, 3}
#  Proves: stealth/harm bind holds across noise levels & threat levels
#  MUST EDIT eval_adaptive_attack.py LINE 47 FIRST (see instructions above)
#  Run:  Phase_CD\Noise_added\run_offset_noise_027.bat
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

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " OFFSET x NOISE SWEEP | maps=$Maps | ${Workers}w | 9 runs | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$sigmas = @(0.0, 0.2, 0.4)
$fs     = @(1, 2, 3)
$total  = $sigmas.Count * $fs.Count
$i = 0

foreach ($sigma in $sigmas) {
    foreach ($f in $fs) {
        $i++
        $log = "$out\adaptive_offset_noise_sigma${sigma}_f${f}_$Maps.txt"
        Write-Host "`n--- [$i/$total] offset x sigma=$sigma f=$f  ->  $log ---" -ForegroundColor Yellow
        # Arguments: model, maps, k(traitors), workers, sweep, sigma
        & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps $f $Workers offset $sigma |
            ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] offset sigma=$sigma f=$f failed (exit $LASTEXITCODE)" -ForegroundColor Red }
    }
}

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" OFFSET x NOISE COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
