# Simple SSH Tunnel Starter
$config = Get-Content tunnel.json | ConvertFrom-Json
$pidFile = "tunnel.pid"

# Check if already running
if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Tunnel is already running (PID: $pid)" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`n=== Starting SSH Tunnel ===" -ForegroundColor Cyan
Write-Host "EC2: $($config.ec2_user)@$($config.ec2_host)" -ForegroundColor White
Write-Host "Forwarding: localhost:$($config.local_port) -> $($config.rds_host):$($config.rds_port)" -ForegroundColor White

$sshArgs = @(
    '-i', $config.ec2_key,
    '-L', "$($config.local_port):$($config.rds_host):$($config.rds_port)",
    '-N',
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'ServerAliveInterval=60',
    "$($config.ec2_user)@$($config.ec2_host)"
)

$process = Start-Process -FilePath 'ssh' -ArgumentList $sshArgs -PassThru -WindowStyle Hidden
$process.Id | Out-File -FilePath $pidFile

Start-Sleep -Seconds 3

if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
    Write-Host "`nTunnel started successfully!" -ForegroundColor Green
    Write-Host "PID: $($process.Id)" -ForegroundColor Green
    Write-Host "`nConnect to: localhost:$($config.local_port)" -ForegroundColor Yellow
    Write-Host "`nTest with: python test_tunnel.py" -ForegroundColor Cyan
} else {
    Write-Host "`nFailed to start tunnel" -ForegroundColor Red
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}
