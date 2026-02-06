# Frontend RBAC Integration Guide

## Overview

The frontend application now has complete RBAC (Role-Based Access Control) integration, allowing you to:
- Check user permissions and roles
- Conditionally render UI components based on permissions
- Show/hide features based on user access level
- Display user roles and permissions in the interface

## Features Implemented

### 1. **User Profile with Roles & Permissions**
- User profile now includes `roles` and `permissions` arrays
- Automatically loaded when user logs in
- Stored in Zustand auth store

### 2. **usePermissions Hook**
Located: `src/hooks/usePermissions.ts`

Provides easy permission checking:
```typescript
const { 
  hasPermission, 
  hasRole, 
  hasAnyPermission, 
  hasAllPermissions,
  isSuperuser 
} = usePermissions();

// Check single permission
if (hasPermission('api:create')) {
  // Show create button
}

// Check role
if (hasRole('admin')) {
  // Show admin panel
}

// Check multiple permissions (any)
if (hasAnyPermission('api:create', 'api:update')) {
  // User has at least one
}

// Check multiple permissions (all)
if (hasAllPermissions('api:create', 'api:delete')) {
  // User has both
}
```

### 3. **PermissionGuard Component**
Located: `src/components/PermissionGuard.tsx`

Wrap UI elements to show/hide based on permissions:
```tsx
import { PermissionGuard } from '../components/PermissionGuard';

// Show button only to users with permission
<PermissionGuard permission="api:create">
  <Button>Create API</Button>
</PermissionGuard>

// Show panel only to admins
<PermissionGuard role="admin">
  <AdminPanel />
</PermissionGuard>

// Show with fallback
<PermissionGuard 
  permission="api:create"
  fallback={<Typography>No access</Typography>}
>
  <CreateForm />
</PermissionGuard>

// Show error message if no access
<PermissionGuard permission="api:delete" showError>
  <DeleteButton />
</PermissionGuard>

// Multiple conditions
<PermissionGuard anyPermissions={["api:create", "api:update"]}>
  <EditButton />
</PermissionGuard>
```

### 4. **User Management Page**
Located: `src/pages/Users.tsx`

Full user management interface with:
- List all users with their roles and status
- View detailed user information (roles + permissions)
- Edit user details (email, active status, superuser)
- Assign roles to users
- Delete users
- Permission-based UI (buttons only shown if user has permission)

### 5. **Updated Services**

**User Service** (`src/services/users.ts`):
```typescript
import userService from '../services/users';

// Get all users
const users = await userService.listUsers();

// Get user details with roles and permissions
const user = await userService.getUser(userId);

// Get current user info
const currentUser = await userService.getCurrentUser();

// Update user
await userService.updateUser(userId, { is_active: false });

// Delete user
await userService.deleteUser(userId);
```

**Auth Service** (`src/services/auth.ts`):
```typescript
import { getCurrentUserInfo } from '../services/auth';

// Get complete user info with roles and permissions
const userInfo = await getCurrentUserInfo();
// Returns: { id, email, is_active, is_superuser, roles: [], permissions: [] }
```

### 6. **Updated Header**
- Shows user email and role badges in dropdown menu
- Displays "Superuser" badge for superusers
- Includes link to Users page
- Shows all assigned roles as chips

## Usage Examples

### Example 1: Conditional Button Rendering

```tsx
import usePermissions from '../hooks/usePermissions';
import { Button } from '@mui/material';

function APIList() {
  const { hasPermission } = usePermissions();

  return (
    <Box>
      <Typography variant="h4">APIs</Typography>
      
      {/* Only show create button to users with permission */}
      {hasPermission('api:create') && (
        <Button variant="contained" onClick={handleCreate}>
          Create API
        </Button>
      )}
      
      {/* Show list to everyone */}
      <APITable />
    </Box>
  );
}
```

### Example 2: Using PermissionGuard

```tsx
import { PermissionGuard } from '../components/PermissionGuard';

function APIActions({ apiId }: { apiId: number }) {
  return (
    <Box>
      {/* Read button - everyone with api:read can see */}
      <PermissionGuard permission="api:read">
        <Button onClick={() => viewAPI(apiId)}>View</Button>
      </PermissionGuard>
      
      {/* Edit button - only for users with api:update */}
      <PermissionGuard permission="api:update">
        <Button onClick={() => editAPI(apiId)}>Edit</Button>
      </PermissionGuard>
      
      {/* Delete button - only for users with api:delete */}
      <PermissionGuard permission="api:delete">
        <Button color="error" onClick={() => deleteAPI(apiId)}>
          Delete
        </Button>
      </PermissionGuard>
    </Box>
  );
}
```

### Example 3: Role-Based Entire Page Protection

```tsx
import { PermissionGuard } from '../components/PermissionGuard';

function AdminPage() {
  return (
    <PermissionGuard 
      role="admin" 
      showError
    >
      <Box>
        <Typography variant="h4">Admin Dashboard</Typography>
        {/* Admin-only content */}
      </Box>
    </PermissionGuard>
  );
}
```

### Example 4: Multiple Permission Checks

```tsx
import { PermissionGuard } from '../components/PermissionGuard';

function APIManagement() {
  return (
    <Box>
      {/* Show if user has ANY of these permissions */}
      <PermissionGuard anyPermissions={["api:create", "api:update", "api:delete"]}>
        <Typography>You can manage APIs</Typography>
      </PermissionGuard>
      
      {/* Show only if user has ALL these permissions */}
      <PermissionGuard allPermissions={["api:create", "api:delete"]}>
        <Button>Full API Management</Button>
      </PermissionGuard>
    </Box>
  );
}
```

### Example 5: Complex Permission Logic

```tsx
function APIDetail({ api }) {
  const { hasPermission, isSuperuser } = usePermissions();
  const currentUser = useAuthStore(s => s.profile);
  
  // User can edit if:
  // 1. They own the API, OR
  // 2. They have api:update permission, OR
  // 3. They are superuser
  const canEdit = 
    api.owner_id === currentUser?.id || 
    hasPermission('api:update') || 
    isSuperuser;
  
  return (
    <Box>
      <Typography>{api.name}</Typography>
      
      {canEdit && (
        <Button onClick={handleEdit}>Edit</Button>
      )}
    </Box>
  );
}
```

## Available Permissions

Based on the backend RBAC system:

### API Management
- `api:create` - Create new APIs
- `api:read` - View API details
- `api:update` - Update APIs
- `api:delete` - Delete APIs
- `api:list` - List all APIs

### User Management
- `user:create` - Create users
- `user:read` - View user details
- `user:update` - Update users
- `user:delete` - Delete users
- `user:list` - List all users

### Key Management
- `key:create` - Create API keys
- `key:read` - View keys
- `key:update` - Update keys
- `key:delete` - Delete keys
- `key:list` - List keys

### Role Management
- `role:create` - Create roles
- `role:read` - View roles
- `role:update` - Update roles
- `role:delete` - Delete roles
- `role:list` - List roles
- `role:assign` - Assign roles to users

### Permission Management
- `permission:create` - Create permissions
- `permission:read` - View permissions
- `permission:delete` - Delete permissions
- `permission:list` - List permissions

### Other Resources
- `connector:*` - Connector operations
- `secret:*` - Secret management
- `audit:read` - View audit logs
- `metrics:read` - View metrics

## Default Roles

| Role | Permissions | Description |
|------|-------------|-------------|
| **admin** | All permissions | Full system access |
| **developer** | api:*, connector:*, key:create/read/list, metrics:read | API development |
| **editor** | api:read/update/list, connector:read/update/list, key:read/list | Edit resources |
| **viewer** | api:read/list, connector:read/list, key:read/list | Read-only access |

## Best Practices

### 1. Use PermissionGuard for UI Elements
```tsx
// GOOD: Hide button if no permission
<PermissionGuard permission="api:delete">
  <Button>Delete</Button>
</PermissionGuard>

// BAD: Show button but disable it
<Button disabled={!hasPermission('api:delete')}>Delete</Button>
```

### 2. Always Check Permissions on Backend Too
Frontend checks are for UX only. Always verify permissions on the backend:
```tsx
// Frontend: Hide button
<PermissionGuard permission="api:delete">
  <Button onClick={deleteAPI}>Delete</Button>
</PermissionGuard>

// Backend will also check permission before deleting
```

### 3. Provide Clear Feedback
```tsx
// Show error message when user lacks permission
<PermissionGuard permission="admin:panel" showError>
  <AdminPanel />
</PermissionGuard>

// Or provide custom fallback
<PermissionGuard 
  permission="api:create"
  fallback={
    <Alert severity="info">
      You need 'api:create' permission to create APIs.
      Contact your administrator.
    </Alert>
  }
>
  <CreateAPIForm />
</PermissionGuard>
```

### 4. Use Hooks for Complex Logic
```tsx
function ComplexComponent() {
  const { 
    hasPermission, 
    hasRole, 
    isSuperuser,
    getPermissions 
  } = usePermissions();
  
  // Complex permission logic
  const canManageTeam = 
    hasRole('admin') || 
    (hasRole('manager') && hasPermission('team:manage'));
  
  // Show all permissions in debug mode
  if (import.meta.env.DEV) {
    console.log('User permissions:', getPermissions());
  }
  
  return (/* ... */);
}
```

### 5. Handle Loading States
The ProtectedRoute component now handles loading user profile automatically, but for custom checks:
```tsx
function MyComponent() {
  const profile = useAuthStore(s => s.profile);
  const { hasPermission } = usePermissions();
  
  // Wait for profile to load
  if (!profile) {
    return <CircularProgress />;
  }
  
  return (
    <Box>
      {hasPermission('api:create') && <CreateButton />}
    </Box>
  );
}
```

## Testing

### Testing with Different Roles

1. **Register as first user** (gets admin role):
```bash
POST /auth/register
{ "email": "admin@test.com", "password": "pass123" }
```

2. **Register additional users** (get viewer role):
```bash
POST /auth/register
{ "email": "user@test.com", "password": "pass123" }
```

3. **Assign different roles**:
- Login as admin
- Go to Users page
- Click "Assign Role" on a user
- Select role from dropdown

4. **Test permissions**:
- Login as different users
- Verify UI elements show/hide correctly
- Check console for any permission errors

### Mock Data for Testing

```typescript
// Mock user with specific permissions
const mockUser = {
  id: 1,
  email: 'test@example.com',
  is_active: true,
  is_superuser: false,
  roles: ['developer'],
  permissions: [
    'api:create',
    'api:read',
    'api:update',
    'api:list',
    'key:create',
    'key:read',
    'key:list'
  ]
};

// Set in test
useAuthStore.setState({ profile: mockUser });
```

## Troubleshooting

### Permissions Not Loading
**Problem**: usePermissions returns empty arrays

**Solution**: 
1. Check ProtectedRoute is loading user profile
2. Verify `/user/me` endpoint returns roles and permissions
3. Check browser console for errors
4. Ensure user is logged in

### UI Elements Not Showing
**Problem**: Buttons hidden even though user has permission

**Solution**:
1. Check exact permission name (case-sensitive)
2. Verify user has the permission: `console.log(getPermissions())`
3. Check if PermissionGuard is used correctly
4. Verify backend seeded roles/permissions

### First User Not Admin
**Problem**: First registered user doesn't have admin access

**Solution**:
1. Delete all users from database
2. Re-register (first user gets admin automatically)
3. Or manually assign admin role via Users page

## Summary

✅ Complete RBAC integration
✅ usePermissions hook for easy permission checking
✅ PermissionGuard component for conditional rendering
✅ Users management page
✅ Role assignment interface
✅ Auth store updated with roles/permissions
✅ Header shows user roles
✅ All routes protected
✅ Service layer for user management

The frontend is now fully integrated with the backend RBAC system!
