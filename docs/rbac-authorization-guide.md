# RBAC Authorization System Guide

## Overview

The Gateway Management system now includes a comprehensive Role-Based Access Control (RBAC) system that provides fine-grained permissions management for users, roles, and resources.

## Features

### 1. User Management with Email
- Users are identified by their email address
- Each user can have multiple roles assigned
- First user registered automatically gets admin/root access
- Support for both legacy (string-based) and modern (table-based) role systems

### 2. Root Access on Registration
- **First User**: The very first user to register automatically receives:
  - `admin` role
  - `is_superuser` flag set to `true`
  - Full system access
- **Subsequent Users**: By default receive `viewer` role with read-only access
- **Optional**: Set `GRANT_ADMIN_ON_REGISTER=true` environment variable to grant admin access to ALL new registrations (useful for development/testing)

### 3. Role and Permission Mapping
The system uses a hierarchical role structure:

#### Default Roles
- **admin**: Full system access - all permissions
- **developer**: API development access - create, read, update APIs and keys
- **editor**: Edit existing resources - read and update only
- **viewer**: Read-only access - view resources only

#### Permission Format
Permissions follow the pattern: `resource:action`
- Resources: `api`, `user`, `key`, `role`, `permission`, `connector`, `audit`, `metrics`, `secret`
- Actions: `create`, `read`, `update`, `delete`, `list`, `assign`

Examples:
- `api:create` - Create new APIs
- `user:read` - View user details
- `role:assign` - Assign roles to users

## Setup Instructions

### 1. Run Database Migrations

Ensure all tables are created:

```powershell
# From backend directory
cd backend
alembic upgrade head
```

### 2. Seed Default Roles and Permissions

Run the seeding script to populate default roles and permissions:

```powershell
python scripts\seed_rbac.py
```

This creates:
- 30+ default permissions covering all resources
- 4 default roles (admin, developer, editor, viewer)

### 3. Register First User (Root Access)

```bash
# Using the API
POST /auth/register
{
  "email": "admin@example.com",
  "password": "secure_password"
}

# Response will include:
{
  "message": "User registered",
  "email": "admin@example.com",
  "role": "admin",
  "is_first_user": true
}
```

## API Endpoints

### User Management

#### List All Users
```http
GET /user/
Authorization: Bearer <token>
```

#### Get User by ID
```http
GET /user/{user_id}
Authorization: Bearer <token>
```
Returns detailed user info including roles and permissions.

#### Get Current User Info
```http
GET /user/me
Authorization: Bearer <token>
```

#### Update User
```http
PUT /user/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "new@example.com",
  "is_active": true,
  "is_superuser": false
}
```

#### Delete User
```http
DELETE /user/{user_id}
Authorization: Bearer <token>
```

### Role Management

#### Create Role
```http
POST /api/authorizers/roles
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "custom_role",
  "description": "Custom role for specific use case",
  "permissions": ["api:read", "api:list"]
}
```

#### List All Roles
```http
GET /api/authorizers/roles
Authorization: Bearer <token>
```

#### Get Role by ID
```http
GET /api/authorizers/roles/{role_id}
Authorization: Bearer <token>
```

#### Update Role
```http
PUT /api/authorizers/roles/{role_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "description": "Updated description",
  "permissions": ["api:read", "api:list", "api:create"]
}
```

#### Delete Role
```http
DELETE /api/authorizers/roles/{role_id}
Authorization: Bearer <token>
```

### Permission Management

#### Create Permission
```http
POST /api/authorizers/permissions
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "custom:action",
  "resource": "custom",
  "action": "action",
  "description": "Custom permission"
}
```

#### List All Permissions
```http
GET /api/authorizers/permissions
Authorization: Bearer <token>
```

#### Delete Permission
```http
DELETE /api/authorizers/permissions/{permission_id}
Authorization: Bearer <token>
```

### User-Role Assignment

#### Assign Role to User
```http
POST /api/authorizers/users/assign-role
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 2,
  "role_id": 3
}
```

#### Remove Role from User
```http
DELETE /api/authorizers/users/{user_id}/roles/{role_id}
Authorization: Bearer <token>
```

#### Get User's Roles
```http
GET /api/authorizers/users/{user_id}/roles
Authorization: Bearer <token>
```

## Code Usage Examples

### Protecting Endpoints with Permissions

```python
from fastapi import APIRouter, Depends
from app.authorizers.rbac import require_permission, require_role
from app.api.auth.auth_dependency import get_current_user

router = APIRouter()

@router.post("/apis")
async def create_api(
    user = Depends(require_permission("api:create"))
):
    """Only users with api:create permission can access."""
    # Your code here
    pass

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    user = Depends(require_role("admin"))
):
    """Only admin role can access."""
    # Your code here
    pass
```

### Checking Permissions in Code

```python
from app.authorizers.rbac import RBACManager

async def my_function(session: AsyncSession, user_id: int):
    manager = RBACManager(session)
    
    # Check if user has specific permission
    has_perm = await manager.user_has_permission(user_id, "api:delete")
    
    # Check if user has specific role
    has_role = await manager.user_has_role(user_id, "admin")
    
    # Get all user permissions
    permissions = await manager.get_user_permissions(user_id)
```

### Programmatic Role Assignment

```python
from app.authorizers.rbac import RBACManager

async def assign_developer_role(session: AsyncSession, user_id: int):
    manager = RBACManager(session)
    
    # Get role by name
    role = await manager.get_role_by_name("developer")
    
    if role:
        # Assign to user
        await manager.assign_role_to_user(user_id, role.id)
```

## Environment Variables

```bash
# Grant admin access to all new registrations (default: false)
GRANT_ADMIN_ON_REGISTER=false

# Enable OTP code return in dev mode (default: false)
DEV_RETURN_OTP=false

# JWT configuration
JWT_SECRET=your-secret-key-change-this
JWT_ALGORITHM=HS256

# Database configuration (if using PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
```

## Suggestions & Best Practices

### 1. Security Recommendations

✅ **DO:**
- Always seed roles and permissions before production deployment
- Use the first user as the root admin account
- Keep `GRANT_ADMIN_ON_REGISTER=false` in production
- Regularly audit user permissions
- Use strong JWT secrets
- Implement rate limiting on authentication endpoints
- Log all role and permission changes in audit logs

❌ **DON'T:**
- Don't leave `GRANT_ADMIN_ON_REGISTER=true` in production
- Don't share admin credentials
- Don't hardcode JWT secrets
- Don't delete the admin role
- Don't assign unnecessary permissions to roles

### 2. Role Design Best Practices

**Principle of Least Privilege**: Give users only the permissions they need.

**Role Hierarchy**:
```
admin (all permissions)
  ├── developer (create/edit resources)
  │   └── editor (edit only)
  │       └── viewer (read only)
```

**Custom Roles**: Create specific roles for your organization:
```python
# Example: API Manager role
{
  "name": "api_manager",
  "description": "Manages APIs and connectors only",
  "permissions": [
    "api:create", "api:read", "api:update", "api:delete", "api:list",
    "connector:create", "connector:read", "connector:update", "connector:delete",
  ]
}
```

### 3. Database Schema

The system uses three main tables:

**permissions**: Defines available permissions
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,  -- e.g., 'api:create'
    resource VARCHAR NOT NULL,      -- e.g., 'api'
    action VARCHAR NOT NULL,        -- e.g., 'create'
    description TEXT,
    created_at TIMESTAMP
);
```

**roles**: Defines roles with their permissions
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,   -- e.g., 'admin'
    description TEXT,
    permissions JSON,               -- Array of permission names
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**user_roles**: Maps users to roles (many-to-many)
```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP
);
```

### 4. Migration Strategy

If upgrading from a system without RBAC:

1. **Run migrations**: `alembic upgrade head`
2. **Seed RBAC data**: `python scripts/seed_rbac.py`
3. **Assign roles to existing users**:
   ```python
   # Manual script or admin panel
   for user in existing_users:
       assign_appropriate_role(user)
   ```
4. **Update API endpoints** to use permission checks
5. **Test thoroughly** before production deployment

### 5. Monitoring and Auditing

Implement audit logging for all authorization changes:

```python
# Log role assignments
await create_audit_log(
    user_id=admin_id,
    action="ASSIGN_ROLE",
    resource_type="USER",
    resource_id=target_user_id,
    metadata={"role_id": role_id, "role_name": role_name}
)

# Log permission changes
await create_audit_log(
    user_id=admin_id,
    action="UPDATE_ROLE",
    resource_type="ROLE",
    resource_id=role_id,
    metadata={"added_permissions": [...], "removed_permissions": [...]}
)
```

### 6. Testing RBAC

```python
# tests/test_rbac.py
import pytest
from app.authorizers.rbac import RBACManager

@pytest.mark.asyncio
async def test_user_has_permission(db_session):
    manager = RBACManager(db_session)
    
    # Create test user and role
    role = await manager.create_role("test_role", permissions=["api:read"])
    await manager.assign_role_to_user(user_id=1, role_id=role.id)
    
    # Test permission check
    assert await manager.user_has_permission(1, "api:read") == True
    assert await manager.user_has_permission(1, "api:delete") == False
```

### 7. Frontend Integration

Example React hook for permission checking:

```typescript
// usePermissions.ts
export const usePermissions = () => {
  const { user } = useAuth();
  
  const hasPermission = (permission: string) => {
    return user?.permissions?.includes(permission) || user?.is_superuser;
  };
  
  const hasRole = (roleName: string) => {
    return user?.roles?.includes(roleName);
  };
  
  return { hasPermission, hasRole };
};

// Usage in component
const CreateAPIButton = () => {
  const { hasPermission } = usePermissions();
  
  if (!hasPermission('api:create')) {
    return null; // Hide button
  }
  
  return <button onClick={createAPI}>Create API</button>;
};
```

### 8. Advanced Features to Consider

**Attribute-Based Access Control (ABAC)**: Already partially implemented in `policies.py`
- Owner-based access
- Resource visibility (public/private/team)
- Time-based access
- Conditional permissions

**Dynamic Permissions**: Evaluate permissions at runtime based on context
```python
# Example: User can only edit their own APIs
if resource.owner_id == user.id or user.has_permission("api:update"):
    allow_update()
```

**Role Inheritance**: Create role hierarchies
```python
# admin inherits all developer permissions
developer_role = await manager.get_role_by_name("developer")
admin_role.inherited_roles = [developer_role.id]
```

### 9. Performance Optimization

**Caching**: Cache user permissions to reduce database queries
```python
from functools import lru_cache
import redis

# Redis cache for user permissions
async def get_user_permissions_cached(user_id: int):
    cache_key = f"user:{user_id}:permissions"
    cached = await redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    permissions = await manager.get_user_permissions(user_id)
    await redis.setex(cache_key, 300, json.dumps(list(permissions)))  # 5 min TTL
    
    return permissions
```

**Batch Operations**: Load permissions for multiple users at once
```python
async def get_users_with_permissions(user_ids: List[int]):
    # Single query with joins instead of N queries
    result = await session.execute(
        select(User, Role, Permission)
        .join(UserRole)
        .join(Role)
        .where(User.id.in_(user_ids))
    )
    # Process and return
```

### 10. Troubleshooting

**Common Issues:**

1. **"Permission denied" errors after registration**
   - Ensure RBAC is seeded: `python scripts/seed_rbac.py`
   - Check user has roles assigned
   - Verify JWT token contains correct user info

2. **First user doesn't have admin access**
   - Check database for existing users
   - Manually set `is_superuser=true` in database
   - Re-assign admin role

3. **Role assignment not working**
   - Verify `user_roles` table exists
   - Check foreign key constraints
   - Ensure role IDs are correct

4. **Permissions not taking effect**
   - Clear permission cache if using caching
   - Restart application
   - Check role's permissions array in database

## Summary

The RBAC system is now fully operational with:

✅ Email-based user management
✅ Automatic root access for first user
✅ Role and permission mapping system
✅ Comprehensive API endpoints
✅ Easy-to-use decorators for endpoint protection
✅ Seeding scripts for default data
✅ Support for both legacy and modern role systems

Follow the setup instructions above to get started!
