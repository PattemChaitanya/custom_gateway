import { useMemo } from "react";
import useAuthStore from "./useAuth";

/**
 * Hook for checking user permissions and roles
 *
 * Usage:
 * ```tsx
 * const { hasPermission, hasRole, hasAnyPermission, hasAllPermissions, isSuperuser } = usePermissions();
 *
 * if (hasPermission('api:create')) {
 *   // Show create button
 * }
 *
 * if (hasRole('admin')) {
 *   // Show admin panel
 * }
 * ```
 */
export function usePermissions() {
  const profile = useAuthStore((state) => state.profile);

  const permissions = useMemo(() => {
    return profile?.permissions || [];
  }, [profile]);

  const roles = useMemo(() => {
    return profile?.roles || [];
  }, [profile]);

  const isSuperuser = useMemo(() => {
    return profile?.is_superuser || false;
  }, [profile]);

  /**
   * Check if user has a specific permission
   * Superusers always have all permissions
   */
  const hasPermission = (permission: string): boolean => {
    if (isSuperuser) return true;
    return permissions.includes(permission);
  };

  /**
   * Check if user has a specific role
   */
  const hasRole = (role: string): boolean => {
    if (isSuperuser && role === "admin") return true;
    return roles.includes(role);
  };

  /**
   * Check if user has ANY of the specified permissions
   */
  const hasAnyPermission = (...perms: string[]): boolean => {
    if (isSuperuser) return true;
    return perms.some((perm) => permissions.includes(perm));
  };

  /**
   * Check if user has ALL of the specified permissions
   */
  const hasAllPermissions = (...perms: string[]): boolean => {
    if (isSuperuser) return true;
    return perms.every((perm) => permissions.includes(perm));
  };

  /**
   * Check if user has ANY of the specified roles
   */
  const hasAnyRole = (...rolesToCheck: string[]): boolean => {
    if (isSuperuser && rolesToCheck.includes("admin")) return true;
    return rolesToCheck.some((role) => roles.includes(role));
  };

  /**
   * Get all user permissions
   */
  const getPermissions = (): string[] => {
    return permissions;
  };

  /**
   * Get all user roles
   */
  const getRoles = (): string[] => {
    return roles;
  };

  return {
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    hasAnyRole,
    getPermissions,
    getRoles,
    isSuperuser,
    isAuthenticated: !!profile,
  };
}

export default usePermissions;
