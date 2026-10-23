<#
  Wakes the Render free-plan backend (and the Neon database behind it) and reports how long it took.
  Run it ~5 minutes before opening, or any time the apps show "reconnecting".

  Usage (PowerShell):
    .\scripts\warmup.ps1 -Base "https://<your-render-app>.onrender.com"
#>
param(
    [Parameter(Mandatory = $true)][string]$Base,
    [int]$TimeoutSeconds = 180
)

$url = ($Base.TrimEnd('/')) + "/api/v1/health/ready"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$attempt = 0

while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
    $attempt++
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
        if ($r.StatusCode -eq 200) {
            Write-Host ("OK: backend + database ready after {0:N1}s ({1} attempt(s))" -f $sw.Elapsed.TotalSeconds, $attempt) -ForegroundColor Green
            exit 0
        }
    }
    catch {
        Write-Host ("[{0:N0}s] not ready yet ({1}) - retrying..." -f $sw.Elapsed.TotalSeconds, $_.Exception.Message)
    }
    Start-Sleep -Seconds 5
}

Write-Host ("FAILED: no healthy response within {0}s. Check the Render dashboard / logs." -f $TimeoutSeconds) -ForegroundColor Red
exit 1
