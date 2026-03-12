/**
 * Unit tests for custom hooks: useAuth store and usePermissions.
 */
import { renderHook, act } from "@testing-library/react";
import { useAuthStore } from "../hooks/useAuth";
import { usePermissions } from "../hooks/usePermissions";

// ---------------------------------------------------------------------------
// useAuthStore — Zustand store
// ---------------------------------------------------------------------------
describe("useAuthStore", () => {
  beforeEach(() => {
    // Reset store state between tests
    act(() => {
      useAuthStore.setState({
        accessToken: null,
        refreshToken: null,
        profile: null,
      });
    });
    localStorage.clear();
  });

  test("initial state has null tokens and profile", () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.accessToken).toBeNull();
    expect(result.current.refreshToken).toBeNull();
    expect(result.current.profile).toBeNull();
  });

  test("setTokens updates tokens in store and localStorage", () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.setTokens("access-123", "refresh-456");
    });
    expect(result.current.accessToken).toBe("access-123");
    expect(result.current.refreshToken).toBe("refresh-456");
    expect(localStorage.getItem("access_token")).toBe("access-123");
    expect(localStorage.getItem("refresh_token")).toBe("refresh-456");
  });

  test("setProfile updates user profile", () => {
    const { result } = renderHook(() => useAuthStore());
    const profile = {
      id: 1,
      email: "alice@example.com",
      is_active: true,
      is_superuser: false,
      roles: ["user"],
      permissions: ["api:read"],
    };
    act(() => {
      result.current.setProfile(profile);
    });
    expect(result.current.profile?.email).toBe("alice@example.com");
    expect(result.current.profile?.roles).toContain("user");
  });

  test("clearAuth resets tokens and profile", () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.setTokens("tok", "ref");
      result.current.setProfile({ email: "a@b.com" });
    });
    act(() => {
      result.current.clearAuth();
    });
    expect(result.current.accessToken).toBeNull();
    expect(result.current.refreshToken).toBeNull();
    expect(result.current.profile).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  test("setProfile with null clears profile", () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.setProfile({ email: "a@b.com" });
    });
    act(() => {
      result.current.setProfile(null);
    });
    expect(result.current.profile).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// usePermissions — derives access control from auth store profile
// ---------------------------------------------------------------------------
describe("usePermissions", () => {
  beforeEach(() => {
    act(() => {
      useAuthStore.setState({
        accessToken: null,
        refreshToken: null,
        profile: null,
      });
    });
  });

  function setProfile(overrides: object = {}) {
    act(() => {
      useAuthStore.setState({
        profile: {
          id: 1,
          email: "user@example.com",
          is_active: true,
          is_superuser: false,
          roles: ["editor"],
          permissions: ["api:read", "api:create"],
          ...overrides,
        },
      });
    });
  }

  test("isAuthenticated is false when no profile", () => {
    const { result } = renderHook(() => usePermissions());
    expect(result.current.isAuthenticated).toBe(false);
  });

  test("isAuthenticated is true when profile is set", () => {
    setProfile();
    const { result } = renderHook(() => usePermissions());
    expect(result.current.isAuthenticated).toBe(true);
  });

  test("hasPermission returns true for granted permission", () => {
    setProfile();
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasPermission("api:read")).toBe(true);
  });

  test("hasPermission returns false for missing permission", () => {
    setProfile();
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasPermission("api:delete")).toBe(false);
  });

  test("superuser always has every permission", () => {
    setProfile({ is_superuser: true, permissions: [] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasPermission("api:delete")).toBe(true);
    expect(result.current.hasPermission("users:manage")).toBe(true);
  });

  test("hasRole returns true for matching role", () => {
    setProfile({ roles: ["admin"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasRole("admin")).toBe(true);
  });

  test("hasRole returns false for non-matching role", () => {
    setProfile({ roles: ["viewer"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasRole("admin")).toBe(false);
  });

  test("superuser is treated as admin role", () => {
    setProfile({ is_superuser: true, roles: [] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasRole("admin")).toBe(true);
  });

  test("hasAnyPermission returns true when at least one matches", () => {
    setProfile({ permissions: ["api:read"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasAnyPermission("api:delete", "api:read")).toBe(
      true,
    );
  });

  test("hasAnyPermission returns false when none match", () => {
    setProfile({ permissions: ["api:read"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasAnyPermission("api:delete", "users:manage")).toBe(
      false,
    );
  });

  test("hasAllPermissions returns true only when all match", () => {
    setProfile({ permissions: ["api:read", "api:create"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasAllPermissions("api:read", "api:create")).toBe(
      true,
    );
    expect(result.current.hasAllPermissions("api:read", "api:delete")).toBe(
      false,
    );
  });

  test("hasAnyRole returns true when at least one role matches", () => {
    setProfile({ roles: ["viewer", "editor"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.hasAnyRole("admin", "editor")).toBe(true);
  });

  test("getPermissions returns current permission list", () => {
    setProfile({ permissions: ["api:read", "api:create"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.getPermissions()).toEqual(["api:read", "api:create"]);
  });

  test("getRoles returns current role list", () => {
    setProfile({ roles: ["editor"] });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.getRoles()).toEqual(["editor"]);
  });

  test("isSuperuser is false for regular user", () => {
    setProfile({ is_superuser: false });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.isSuperuser).toBe(false);
  });

  test("isSuperuser is true for superuser", () => {
    setProfile({ is_superuser: true });
    const { result } = renderHook(() => usePermissions());
    expect(result.current.isSuperuser).toBe(true);
  });
});
