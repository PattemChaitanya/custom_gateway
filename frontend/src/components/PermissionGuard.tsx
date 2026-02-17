import React from "react";
import { Box, Alert } from "@mui/material";
import usePermissions from "../hooks/usePermissions";

interface PermissionGuardProps {
  permission?: string;
  role?: string;
  anyPermissions?: string[];
  allPermissions?: string[];
  anyRoles?: string[];
  requireSuperuser?: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showError?: boolean;
}

/**
 * Component to conditionally render children based on user permissions
 *
 * Usage:
 * ```tsx
 * <PermissionGuard permission="api:create">
 *   <Button>Create API</Button>
 * </PermissionGuard>
 *
 * <PermissionGuard role="admin">
 *   <AdminPanel />
 * </PermissionGuard>
 *
 * <PermissionGuard anyPermissions={["api:create", "api:update"]}>
 *   <EditButton />
 * </PermissionGuard>
 * ```
 */
export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permission,
  role,
  anyPermissions,
  allPermissions,
  anyRoles,
  requireSuperuser,
  children,
  fallback,
  showError = false,
}) => {
  const {
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    hasAnyRole,
    isSuperuser,
  } = usePermissions();

  let hasAccess = false;

  // Check superuser requirement first
  if (requireSuperuser) {
    hasAccess = isSuperuser;
  } else {
    // Check single permission
    if (permission && hasPermission(permission)) {
      hasAccess = true;
    }

    // Check single role
    if (role && hasRole(role)) {
      hasAccess = true;
    }

    // Check any permissions
    if (anyPermissions && hasAnyPermission(...anyPermissions)) {
      hasAccess = true;
    }

    // Check all permissions
    if (allPermissions && hasAllPermissions(...allPermissions)) {
      hasAccess = true;
    }

    // Check any roles
    if (anyRoles && hasAnyRole(...anyRoles)) {
      hasAccess = true;
    }
  }

  if (!hasAccess) {
    if (showError) {
      return (
        <Box sx={{ p: 2 }}>
          <Alert severity="error">
            You don't have permission to access this feature.
          </Alert>
        </Box>
      );
    }
    return fallback ? <>{fallback}</> : null;
  }

  return <>{children}</>;
};

export default PermissionGuard;
