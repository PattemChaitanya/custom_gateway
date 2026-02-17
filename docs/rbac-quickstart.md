# RBAC System Quick Start

## Quick Setup (3 steps)

### 1. Run Migrations
```powershell
cd backend
alembic upgrade head
```

### 2. Seed Roles & Permissions
```powershell
python scripts\seed_rbac.py
```

### 3. Register First User (Gets Admin Access)
```powershell
# Start the server
uvicorn app.main:app --reload

# Then in another terminal or using Postman/curl:
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "SecurePassword123"}'
```

## Verification

### Test Admin Access
```powershell
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "SecurePassword123"}'

# Copy the access_token from response, then:

# Check your user info
curl -X GET http://localhost:8000/user/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Should show:
# - is_superuser: true
# - roles: ["admin"]
# - permissions: [all permissions]
```

### Test RBAC Endpoints
```powershell
# List all roles
curl -X GET http://localhost:8000/api/authorizers/roles \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# List all permissions  
curl -X GET http://localhost:8000/api/authorizers/permissions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create a new user (as admin)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user2@example.com", "password": "Password123"}'

# Assign developer role to user 2
curl -X POST http://localhost:8000/api/authorizers/users/assign-role \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2, "role_id": 2}'
```

## Default Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **admin** | All permissions | System administrators |
| **developer** | Create/edit APIs, keys, connectors | API developers |
| **editor** | Edit existing resources | Content editors |
| **viewer** | Read-only access | Auditors, report viewers |

## Common Tasks

### Create Custom Role
```bash
POST /api/authorizers/roles
{
  "name": "api_manager",
  "description": "Manages APIs only",
  "permissions": ["api:create", "api:read", "api:update", "api:delete", "api:list"]
}
```

### Assign Role to User
```bash
POST /api/authorizers/users/assign-role
{
  "user_id": 3,
  "role_id": 2
}
```

### Check User Permissions
```bash
GET /user/{user_id}
# Returns user with roles and permissions
```

## Environment Variables

```bash
# .env file
GRANT_ADMIN_ON_REGISTER=false  # Set to true to make ALL users admin (dev only!)
JWT_SECRET=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://...
```

## Troubleshooting

**Problem**: First user doesn't have admin
- **Solution**: Delete the user and re-register, OR manually run:
  ```sql
  UPDATE users SET is_superuser = true, roles = 'admin' WHERE id = 1;
  ```

**Problem**: "Table doesn't exist" errors
- **Solution**: Run migrations: `alembic upgrade head`

**Problem**: No default roles/permissions
- **Solution**: Run seed script: `python scripts\seed_rbac.py`

**Problem**: Permission denied errors
- **Solution**: Check user's roles: `GET /user/me`

## Next Steps

1. Read full guide: [docs/rbac-authorization-guide.md](rbac-authorization-guide.md)
2. Implement permission checks in your endpoints
3. Create custom roles for your team
4. Set up audit logging for security
5. Configure frontend to show/hide features based on permissions

## Support

For detailed documentation, see: `docs/rbac-authorization-guide.md`
