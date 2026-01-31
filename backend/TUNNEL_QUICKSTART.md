# 🚀 Quick Start: SSH Tunnel to AWS RDS

## What You Need

Before starting, gather these details:

1. **EC2 Bastion/Jump Host**:
   - Public IP or DNS name (e.g., `ec2-13-127-45-67.ap-south-1.compute.amazonaws.com`)
   - SSH username (usually `ec2-user` for Amazon Linux, `ubuntu` for Ubuntu)
   - SSH private key file (`.pem` file you downloaded when creating the EC2)

2. **RDS Details** (you already have these):
   - Host: `database-1.cteiwsow8b4a.ap-south-1.rds.amazonaws.com`
   - Port: `5432`
   - Database: `postgres`
   - Username: `postgres`
   - Password: `(^$)2Chaitu`

## Step-by-Step Setup

### Step 1: Configure the Tunnel

Open PowerShell in the backend directory and run:

```powershell
cd "d:\projects\Gateway management\backend"
.\setup_tunnel.ps1 -Configure
```

You'll be prompted for:
- **EC2 Host**: Enter your EC2 instance public DNS/IP
- **EC2 User**: Enter `ec2-user` (or `ubuntu` if using Ubuntu)
- **SSH Key Path**: Enter path to your `.pem` file (e.g., `C:\Users\chait\.ssh\your-key.pem`)
- **RDS Host**: Press Enter (uses default: `database-1.cteiwsow8b4a.ap-south-1.rds.amazonaws.com`)
- **RDS Port**: Press Enter (uses default: `5432`)
- **Local Port**: Press Enter (uses default: `5432`)

### Step 2: Update Environment Variables

The configuration wizard will tell you to update `.env`. Copy the provided settings:

```env
AWS_DB_HOST=localhost
AWS_DB_PORT=5432
AWS_REQUIRE_SSL=false
```

Or simply copy the pre-configured file:
```powershell
Copy-Item .env.tunnel .env
```

### Step 3: Start the Tunnel

```powershell
.\setup_tunnel.ps1 -Start
```

You should see:
```
✓ SSH tunnel started successfully (PID: xxxxx)

You can now connect to PostgreSQL at: localhost:5432
```

### Step 4: Verify Connection

```powershell
# Run the diagnostic tool
python diagnose_db.py
```

You should see:
```
✅ AWS PostgreSQL connection is WORKING
```

### Step 5: Start Your Application

In a **separate terminal**:

```powershell
cd "d:\projects\Gateway management\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Your application will now connect to AWS RDS through the tunnel! 🎉

## Managing the Tunnel

### Check Status
```powershell
.\setup_tunnel.ps1 -Status
```

### Stop Tunnel
```powershell
.\setup_tunnel.ps1 -Stop
```

### Restart Tunnel
```powershell
.\setup_tunnel.ps1 -Restart
```

## Common Issues & Solutions

### Issue 1: "Permission denied (publickey)"

**Solution**: Your SSH key may have wrong permissions or the key isn't added to EC2.

```powershell
# Verify your key works with direct SSH:
ssh -i "C:\Users\chait\.ssh\your-key.pem" ec2-user@your-ec2-host

# If that doesn't work, check:
# 1. Key file path is correct
# 2. Key is associated with the EC2 instance
# 3. EC2 security group allows SSH (port 22) from your IP
```

### Issue 2: "Connection timeout"

**Solution**: EC2 security group needs to allow SSH from your IP.

1. Go to AWS Console → EC2 → Security Groups
2. Find your EC2's security group
3. Add inbound rule:
   - Type: SSH
   - Port: 22
   - Source: Your IP (click "My IP" button)

### Issue 3: "Could not resolve hostname"

**Solution**: Double-check your EC2 DNS name.

```powershell
# Get your EC2 public DNS from AWS Console:
# EC2 → Instances → Select your instance → Copy "Public IPv4 DNS"
```

### Issue 4: "Address already in use" (Port 5432)

**Solution**: Another service is using port 5432.

```powershell
# Check what's using port 5432:
netstat -ano | findstr :5432

# Stop the process or use a different port:
.\setup_tunnel.ps1 -Configure
# Then enter a different local port (e.g., 5433)
```

## Security Checklist

- [ ] EC2 security group restricts SSH to your IP only
- [ ] SSH key file has proper permissions (read-only)
- [ ] RDS is NOT publicly accessible (stays private)
- [ ] RDS security group only allows connections from EC2
- [ ] Using strong database password
- [ ] Regularly rotate SSH keys

## Visual Architecture

```
┌─────────────────────┐
│   Your Application  │
│   (localhost:5432)  │
└──────────┬──────────┘
           │ Tunnel
           ▼
┌─────────────────────┐
│   SSH Tunnel        │
│   (localhost:5432)  │
└──────────┬──────────┘
           │ Encrypted SSH
           ▼
┌─────────────────────┐
│   EC2 Bastion       │
│   (Public Subnet)   │
│   22.xx.xxx.xxx     │
└──────────┬──────────┘
           │ VPC Network
           ▼
┌─────────────────────┐
│   RDS PostgreSQL    │
│   (Private Subnet)  │
│   172.31.48.114     │
└─────────────────────┘
```

## What Happens Behind the Scenes

1. Your app connects to `localhost:5432`
2. SSH tunnel encrypts the connection
3. Tunnel forwards to EC2 on port 22 (SSH)
4. EC2 forwards to RDS on port 5432 (PostgreSQL)
5. All traffic is encrypted via SSH

## Alternative: If You Don't Have EC2

If you don't have an EC2 instance yet:

### Option A: Create a Free EC2 Instance

1. AWS Console → EC2 → Launch Instance
2. Select Amazon Linux 2 (Free tier eligible)
3. Instance type: `t2.micro` or `t3.micro`
4. Network: **Same VPC as your RDS**
5. Subnet: **Public subnet**
6. Auto-assign Public IP: **Enable**
7. Security Group:
   - SSH (22) from your IP
8. Create and download key pair

### Option B: Use AWS Systems Manager (No EC2 needed!)

If your RDS allows AWS Systems Manager:

```powershell
# Install AWS Session Manager plugin first
# Then use this command:
aws ssm start-session `
  --target i-xxxxxxxxx `
  --document-name AWS-StartPortForwardingSessionToRemoteHost `
  --parameters "host=database-1.cteiwsow8b4a.ap-south-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5432"
```

## Next Steps

Once the tunnel is working:

1. ✅ Develop locally with AWS database access
2. ✅ Run migrations: `alembic upgrade head`
3. ✅ Test your APIs with real data
4. ✅ Keep tunnel running during development

## Need Help?

Run the diagnostic tool anytime:
```powershell
python diagnose_db.py
```

Check tunnel status:
```powershell
.\setup_tunnel.ps1 -Status
```

View logs in real-time:
```powershell
# If you need to see SSH debug output:
ssh -v -i "C:\Users\chait\.ssh\your-key.pem" -L 5432:database-1.cteiwsow8b4a.ap-south-1.rds.amazonaws.com:5432 ec2-user@your-ec2-host
```

---

**Ready to start?** Run: `.\setup_tunnel.ps1 -Configure`
