# Stop SSH Tunnel
$pidFile = "tunnel.pid"

if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    
    if ($process) {
        Stop-Process -Id $pid -Force
        Write-Host "Tunnel stopped (PID: $pid)" -ForegroundColor Green
    } else {
        Write-Host "No tunnel process found" -ForegroundColor Yellow
    }
    
    Remove-Item $pidFile
} else {
    Write-Host "No tunnel is running" -ForegroundColor Yellow
}
