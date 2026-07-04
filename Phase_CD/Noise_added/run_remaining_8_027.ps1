# ============================================================
#  RUN THE 8 REMAINING/CRASHED ADAPTIVE SWEEPS (500 maps, 10 workers)
# ============================================================
$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$py   = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
$root = "D:\Swarm\BTP"
Set-Location $root
$out  = "Phase_CD\Noise_added\results_027"
$M2   = "models\noise_robust_ON_stage2_final.zip"
$Maps = 500
$Workers = 10

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " RESUMING REMAINING 8 SWEEPS | 10w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Re-run adaptive_offset_f1_500 (sigma=0.6)
$log1 = "$out\adaptive_offset_f1_$Maps.txt"
Write-Host "`n--- [1/8] offset f=1 (sigma=0.6) -> $log1 ---" -ForegroundColor Yellow
& $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 1 $Workers offset |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log1 -Encoding utf8

# 2. Re-run adaptive_offset_noise_sigma0_f3_500 (sigma=0.0, f=3)
$log2 = "$out\adaptive_offset_noise_sigma0_f3_$Maps.txt"
Write-Host "`n--- [2/8] offset f=3 (sigma=0.0) -> $log2 ---" -ForegroundColor Yellow
& $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 3 $Workers offset 0.0 |
    ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log2 -Encoding utf8

# 3. Run missing sigma=0.2 for f=1, 2, 3
$i = 2
foreach ($f in 1, 2, 3) {
    $i++
    $log = "$out\adaptive_offset_noise_sigma0.2_f${f}_$Maps.txt"
    Write-Host "`n--- [$i/8] offset f=$f (sigma=0.2) -> $log ---" -ForegroundColor Yellow
    & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps $f $Workers offset 0.2 |
        ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
}

# 4. Run missing sigma=0.4 for f=1, 2, 3
foreach ($f in 1, 2, 3) {
    $i++
    $log = "$out\adaptive_offset_noise_sigma0.4_f${f}_$Maps.txt"
    Write-Host "`n--- [$i/8] offset f=$f (sigma=0.4) -> $log ---" -ForegroundColor Yellow
    & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps $f $Workers offset 0.4 |
        ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
}

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" REMAINING 8 RUNS COMPLETE in {0:hh\:mm\:ss}." -f $dt) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
