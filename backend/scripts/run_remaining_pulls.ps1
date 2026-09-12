# Runs the outstanding pulls to completion, in order, and stages each one.
#
# Run this in your OWN PowerShell window. It survives the Claude session ending;
# anything Claude launches does not.
#
# Every step is checkpointed per item in data/manifests/pull_state.json, so closing
# the window or losing the connection costs only the in-flight request. Re-running
# this script picks up exactly where it stopped.
#
# IMPORTANT: run only ONE copy at a time. The checkpoint uses a thread lock, not a
# process lock, so two concurrent runs can corrupt pull_state.json.
#
#   cd c:\Users\mikae\Coder\DataSport\DataSport\backend
#   .\scripts\run_remaining_pulls.ps1

$ErrorActionPreference = "Continue"
$backend = "c:\Users\mikae\Coder\DataSport\DataSport\backend"
Set-Location $backend
& .\.venv\Scripts\Activate.ps1

$log = "data\logs\remaining_pulls_$(Get-Date -Format yyyyMMdd_HHmmss).log"
Write-Host "Logging to $log"

function Step($label, $argline) {
    Write-Host ""
    Write-Host "=== $label ===" -ForegroundColor Cyan
    Write-Host "    started $(Get-Date -Format 'HH:mm:ss')"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & python -u $argline.Split(" ") 2>&1 | Tee-Object -Append -FilePath $log
    $sw.Stop()
    Write-Host "    finished in $([math]::Round($sw.Elapsed.TotalMinutes,1)) min"
}

# 1. Finish bio/roster/awards. player_bio is already complete; this resumes at
#    team_roster and then does player_awards (~2,860 players).
Step "Phase 7 - bio / rosters / awards (resumes)"  "-m ingestion.pull_all --phase 7 --log-file"
Step "Stage phase 7"                               "-m ingestion.stage_all --phase 7"

# 2. Shot charts. The long one: ~29,000 reads, roughly 6-7 hours.
Step "Phase 9 - LOC_X/LOC_Y shot charts"           "-m ingestion.pull_all --phase 9 --log-file"
Step "Stage phase 9"                               "-m ingestion.stage_all --phase 9"

Write-Host ""
Write-Host "All done. Restart the backend to pick up the new tables." -ForegroundColor Green
