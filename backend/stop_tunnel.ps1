# Stop SSH Tunnel
$pidFile = "tunnel.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "No tunnel is running (no $pidFile found)." -ForegroundColor Yellow
    exit 0
}

try {
    $tunnelPid = (Get-Content $pidFile).Trim()
}
catch {
    Write-Host ("Failed to read " + $pidFile) $_ -ForegroundColor Red
    exit 1
}

try {
    $proc = Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue
    if ($null -ne $proc) {
        Stop-Process -Id $tunnelPid -Force -ErrorAction Stop
        Write-Host "Tunnel stopped (PID: $tunnelPid)" -ForegroundColor Green
    }
    else {
        Write-Host "No process with PID $tunnelPid found. Removing stale PID file." -ForegroundColor Yellow
    }
}
catch {
    Write-Host ("Error stopping process " + $tunnelPid) $_ -ForegroundColor Red
}

try {
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}
catch {
    Write-Host ("Failed to remove " + $pidFile) $_ -ForegroundColor Yellow
}
