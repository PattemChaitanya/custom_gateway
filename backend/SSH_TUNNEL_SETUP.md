# SSH Tunnel Setup for AWS RDS Access

## Overview

This setup creates an SSH tunnel from your local machine to AWS RDS through an EC2 bastion host, allowing secure database access without making RDS publicly accessible.

## Prerequisites

1. **EC2 Bastion Host**: You need an EC2 instance in the same VPC as your RDS
2. **SSH Key**: Your private key file (`.pem` or `.ppk`)
3. **Security Groups**:
   - EC2: Allow SSH (port 22) from your IP
   - RDS: Allow PostgreSQL (port 5432) from EC2's security group

## Quick Start

### Windows (PowerShell)

```powershell
# 1. Configure your tunnel settings
.\setup_tunnel.ps1 -Configure

# 2. Start the tunnel
.\setup_tunnel.ps1 -Start

# 3. Run your application (in another terminal)
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# 4. Stop the tunnel when done
.\setup_tunnel.ps1 -Stop
```

### Linux/Mac (Bash)

```bash
# 1. Configure your tunnel settings
./setup_tunnel.sh configure

# 2. Start the tunnel
./setup_tunnel.sh start

# 3. Run your application (in another terminal)
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# 4. Stop the tunnel when done
./setup_tunnel.sh stop
```

## Configuration

Create a `tunnel_config.json` file with your AWS details:

```json
{
  "ec2_host": "ec2-xx-xx-xx-xx.ap-south-1.compute.amazonaws.com",
  "ec2_user": "ec2-user",
  "ec2_key": "C:\\path\\to\\your\\key.pem",
  "rds_host": "database-1.cteiwsow8b4a.ap-south-1.rds.amazonaws.com",
  "rds_port": 5432,
  "local_port": 5432
}
```

## Environment Variables

When tunnel is active, use these settings in `.env`:

```env
# Local tunnel endpoint (forwarding to RDS)
AWS_DB_HOST=localhost
AWS_DB_PORT=5432
AWS_DB_NAME=postgres
AWS_DB_USER=postgres
AWS_DB_PASSWORD=your_password
AWS_REQUIRE_SSL=false  # SSL handled by tunnel
```

## How It Works

```
Your App (localhost:5432)
    ↓ [SSH Tunnel]
EC2 Bastion (public IP)
    ↓ [VPC Private Network]
RDS Instance (private IP: 172.31.48.114)
```

The SSH tunnel encrypts and forwards PostgreSQL traffic through the EC2 instance.

## Troubleshooting

### "Permission denied (publickey)"
```bash
# Fix permissions on your key file
chmod 400 /path/to/your/key.pem
```

### "Connection refused"
- Verify EC2 security group allows SSH from your IP
- Check EC2 instance is running
- Verify SSH service is active on EC2

### "Could not resolve hostname"
- Check EC2 public DNS/IP is correct
- Ensure internet connectivity

### Application can't connect to database
- Verify tunnel is running (`.\setup_tunnel.ps1 -Status`)
- Check local port 5432 is not used by another service
- Confirm RDS allows connections from EC2 security group

## Security Best Practices

1. **Restrict EC2 Access**: Only allow SSH from your IP in security group
2. **Use Key Authentication**: Never use passwords for SSH
3. **Rotate Keys**: Regularly update your SSH keys
4. **Monitor Access**: Review CloudWatch logs
5. **Use Session Manager**: Consider AWS Systems Manager Session Manager as alternative

## Automatic Tunnel Management

The scripts include automatic reconnection and health checks:

- Auto-reconnects if connection drops
- Health check every 30 seconds
- Graceful shutdown on exit
- Process cleanup

## Alternative: AWS Systems Manager Session Manager

For even better security, use Session Manager (no open SSH port needed):

```bash
# Install AWS Session Manager plugin
# Then use port forwarding:
aws ssm start-session \
  --target i-xxxxxxxxxxxxx \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "host=database-1.cteiwsow8b4a.ap-south-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5432"
```

## Multiple Environments

Create environment-specific configs:

```
tunnel_config.dev.json
tunnel_config.staging.json
tunnel_config.prod.json
```

Use with:
```powershell
.\setup_tunnel.ps1 -Start -Config tunnel_config.dev.json
```
