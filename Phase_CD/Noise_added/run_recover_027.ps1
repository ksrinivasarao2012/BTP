# ============================================================
#  RECOVERY run - re-creates the results lost to the bad UTF-16 converter, plus the 3 pending.
#  Lost adaptive (must re-run): offset f2, offset f3, gap f3, jitter f3, duty f3
#  Pending: anchor_OFF, naive, dropout
#  500 maps, density 0.27, 10 cores, clean ASCII + UTF-8 logs.
#  RUN ONLY AFTER the missing-6 (duty f1/f2) pipeline has finished.
#  Run:  Phase_CD\Noise_added\run_recover_027.bat
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
$OFF = "models\raster_slot_fusion_OFF_stage2_final.zip"

$t0 = Get-Date
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " RECOVERY 027 | maps=$Maps | ${Workers}w | started $t0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# helper: run a command, show live + save UTF-8
function Go($title, $log, [scriptblock]$cmd) {
    Write-Host "`n--- $title  ->  $log ---" -ForegroundColor Yellow
    & $cmd | ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $log -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Write-Host "[!] $title failed (exit $LASTEXITCODE)" -ForegroundColor Red }
}

# --- 5 lost adaptive runs (fixed radius) ---
Go "offset f=2" "$out\adaptive_offset_f2_$Maps.txt" { & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 2 $Workers offset }
Go "offset f=3" "$out\adaptive_offset_f3_$Maps.txt" { & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 3 $Workers offset }
Go "gap f=3"    "$out\adaptive_gap_f3_$Maps.txt"    { & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 3 $Workers gap }
Go "jitter f=3" "$out\adaptive_jitter_f3_$Maps.txt" { & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 3 $Workers jitter }
Go "duty f=3"   "$out\adaptive_duty_f3_$Maps.txt"   { & $py Phase_CD\Noise_added\eval_adaptive_attack.py $M2 $Maps 3 $Workers duty }

# --- 3 pending ---
Go "anchor OFF" "$out\anchor_OFF_$Maps.txt" { & $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py $OFF $Maps 0.27 $Workers }
Go "dropout"    "$out\dropout_sweep_$Maps.txt" { & $py Phase_CD\Collab_Perception\eval_dropout_sweep.py $Maps 0.27 $Workers }
Go "naive"      "$out\naive_sweep_$Maps.txt"   { & $py Phase_CD\Noise_added\eval_noise_sweep.py $M2 $Maps 2 $Workers }

$dt = (Get-Date) - $t0
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host (" RECOVERY COMPLETE in {0:hh\:mm\:ss}.  Logs: {1}\" -f $dt, $out) -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
