# RBAC Quick Reference

## Import Statements

```typescript
// Permission checking hook
import usePermissions from '../hooks/usePermissions';

// Permission guard component
import { PermissionGuard } from '../components/PermissionGuard';

// User service
import userService from '../services/users';

// Authorizers service (roles, permissions, assignments)
import authorizersService from '../services/authorizers';
```

## usePermissions Hook

```typescript
const {
  hasPermission,        // Check single permission
  hasRole,             // Check single role
  hasAnyPermission,    // Check any of permissions
  hasAllPermissions,   // Check all permissions
  hasAnyRole,          // Check any of roles
  isSuperuser,         // Check if superuser
  getPermissions,      // Get all permissions array
  getRoles,            // Get all roles array
  isAuthenticated      // Check if logged in
} = usePermissions();
```

## Quick Examples

### 1. Conditional Button

```tsx
const { hasPermission } = usePermissions();

{hasPermission('api:create') && (
  <Button onClick={handleCreate}>Create</Button>
)}
```

### 2. PermissionGuard Component

```tsx
<PermissionGuard permission="api:delete">
  <Button color="error">Delete</Button>
</PermissionGuard>
```

### 3. Multiple Permissions (Any)

```tsx
<PermissionGuard anyPermissions={["api:create", "api:update"]}>
  <EditButton />
</PermissionGuard>
```

### 4. Multiple Permissions (All)

```tsx
<PermissionGuard allPermissions={["api:create", "api:delete"]}>
  <AdminButton />
</PermissionGuard>
```

### 5. Role Check

```tsx
<PermissionGuard role="admin">
  <AdminPanel />
</PermissionGuard>
```

### 6. Show Error Message

```tsx
<PermissionGuard permission="secret:read" showError>
  <SecretsList />
</PermissionGuard>
```

### 7. Custom Fallback

```tsx
<PermissionGuard 
  permission="api:create"
  fallback={<Alert severity="info">No access</Alert>}
>
  <CreateForm />
</PermissionGuard>
```

## Common Permissions

```
api:create, api:read, api:update, api:delete, api:list
user:create, user:read, user:update, user:delete, user:list
key:create, key:read, key:update, key:delete, key:list
role:create, role:read, role:update, role:delete, role:list, role:assign
permission:create, permission:read, permission:delete, permission:list
connector:create, connector:read, connector:update, connector:delete, connector:list
secret:create, secret:read, secret:update, secret:delete
audit:read, metrics:read
```

## Common Roles

- `admin` - All permissions
- `developer` - API/connector/key management
- `editor` - Read and update resources
- `viewer` - Read-only access

## API Services

### User Service

```typescript
// List users
const users = await userService.listUsers();

// Get user details
const user = await userService.getUser(userId);

// Get current user
const me = await userService.getCurrentUser();

// Update user
await userService.updateUser(userId, { is_active: false });

// Delete user
await userService.deleteUser(userId);
```

### Authorizers Service

```typescript
// List roles
const roles = await authorizersService.listRoles();

// Create role
await authorizersService.createRole({
  name: 'custom_role',
  description: 'Description',
  permissions: ['api:read', 'api:list']
});

// Assign role to user
await authorizersService.assignRoleToUser({
  user_id: 2,
  role_id: 3
});

// Remove role from user
await authorizersService.removeRoleFromUser(userId, roleId);

// Get user's roles
const userRoles = await authorizersService.getUserRoles(userId);

// List permissions
const permissions = await authorizersService.listPermissions();
```

## Pages & Routes

- `/users` - User management (requires `user:list`)
- `/authorizers` - Role & permission management
- All routes protected by authentication
- UI elements conditionally rendered based on permissions

## User Profile Structure

```typescript
interface UserProfile {
  id: number;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];           // ['admin', 'developer']
  permissions: string[];     // ['api:create', 'api:read', ...]
}
```

## Complete Component Example

```tsx
import React from 'react';
import { Button, Box } from '@mui/material';
import usePermissions from '../hooks/usePermissions';
import { PermissionGuard } from '../components/PermissionGuard';

function APIManagement() {
  const { hasPermission, isSuperuser } = usePermissions();

  return (
    <Box>
      {/* Method 1: Using hook */}
      {hasPermission('api:create') && (
        <Button onClick={handleCreate}>Create API</Button>
      )}

      {/* Method 2: Using PermissionGuard */}
      <PermissionGuard permission="api:update">
        <Button onClick={handleEdit}>Edit API</Button>
      </PermissionGuard>

      {/* Method 3: Role check */}
      <PermissionGuard role="admin">
        <Button onClick={handleAdvanced}>Advanced Settings</Button>
      </PermissionGuard>

      {/* Method 4: Multiple permissions */}
      <PermissionGuard anyPermissions={["api:delete", "api:update"]}>
        <Button onClick={handleManage}>Manage</Button>
      </PermissionGuard>

      {/* Method 5: Superuser check */}
      {isSuperuser && (
        <Button onClick={handleSuperAdmin}>Super Admin Panel</Button>
      )}
    </Box>
  );
}
```

## Testing Checklist

- [ ] Register first user (should get admin role)
- [ ] Register second user (should get viewer role)
- [ ] Login as admin - verify all features visible
- [ ] Login as viewer - verify limited features
- [ ] Test role assignment from Users page
- [ ] Verify permissions shown in header menu
- [ ] Test permission guards hide/show correctly
- [ ] Check console for permission errors

## Common Patterns

### Pattern 1: CRUD Operations
```tsx
<PermissionGuard permission="resource:create">
  <CreateButton />
</PermissionGuard>

<PermissionGuard permission="resource:read">
  <ViewButton />
</PermissionGuard>

<PermissionGuard permission="resource:update">
  <EditButton />
</PermissionGuard>

<PermissionGuard permission="resource:delete">
  <DeleteButton />
</PermissionGuard>
```

### Pattern 2: Owner or Permission
```tsx
const canEdit = 
  resource.owner_id === currentUser.id || 
  hasPermission('resource:update') ||
  isSuperuser;

{canEdit && <EditButton />}
```

### Pattern 3: Progressive Disclosure
```tsx
// Everyone sees list
<ResourceList />

// Only specific users see actions
<PermissionGuard permission="resource:manage">
  <ActionButtons />
</PermissionGuard>
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Permissions empty | Check ProtectedRoute loading profile |
| UI not updating | Verify exact permission name (case-sensitive) |
| First user not admin | Delete users, re-register first user |
| Role assignment fails | Check user has `role:assign` permission |

## Environment Variables

```bash
# Backend
GRANT_ADMIN_ON_REGISTER=false  # Set true for dev/testing only
JWT_SECRET=your-secret-key
DATABASE_URL=postgresql://...

# Frontend  
VITE_API_URL=http://localhost:8000
```

---

For detailed guide, see: `RBAC_INTEGRATION.md`
