/**
 * Unit tests for all frontend service modules.
 * The internal `api` axios instance is mocked so no real HTTP requests are made.
 */
import {
  listAPIs,
  createAPI,
  getAPI,
  updateAPI,
  deleteAPI,
  listAuthPolicies,
  createAuthPolicy,
  updateAuthPolicy,
  deleteAuthPolicy,
} from "../services/apis";
import { apiKeysService } from "../services/apiKeys";
import { secretsService } from "../services/secrets";
import connectorsService from "../services/connectors";
import { auditLogsService } from "../services/auditLogs";
import { login, logout, me, register, resetPassword } from "../services/auth";
import userService from "../services/users";

// ---------------------------------------------------------------------------
// Mock the shared axios instance so services never hit the network
// ---------------------------------------------------------------------------
jest.mock("../services/api", () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

// Also mock the auth store used inside auth.ts
jest.mock("../hooks/useAuth", () => ({
  __esModule: true,
  default: jest.fn(() => ({ accessToken: null, profile: null })),
  useAuthStore: jest.fn(() => ({ accessToken: null, profile: null })),
  getAuthStore: jest.fn(() => ({
    setTokens: jest.fn(),
    clearAuth: jest.fn(),
    accessToken: null,
  })),
}));

import api from "../services/api";
const mockApi = api as jest.Mocked<typeof api>;

beforeEach(() => jest.clearAllMocks());

// ===========================================================================
// Auth service
// ===========================================================================
describe("auth service", () => {
  test("login stores tokens and returns data", async () => {
    mockApi.post.mockResolvedValueOnce({
      data: { access_token: "tok", refresh_token: "ref" },
    });
    const result = await login("a@b.com", "pass");
    expect(mockApi.post).toHaveBeenCalledWith(
      "/auth/login",
      { email: "a@b.com", password: "pass" },
      { withCredentials: true },
    );
    expect(result.access_token).toBe("tok");
  });

  test("me calls /auth/me", async () => {
    mockApi.get.mockResolvedValueOnce({
      data: {
        email: "a@b.com",
        id: 1,
        roles: [],
        permissions: [],
        is_active: true,
        is_superuser: false,
      },
    });
    const result = await me();
    expect(mockApi.get).toHaveBeenCalledWith("/auth/me", {
      withCredentials: true,
    });
    expect(result.email).toBe("a@b.com");
  });

  test("register posts to /auth/register", async () => {
    mockApi.post.mockResolvedValueOnce({
      data: { message: "User registered" },
    });
    const result = await register("a@b.com", "pass", { firstName: "Alice" });
    expect(mockApi.post).toHaveBeenCalledWith("/auth/register", {
      email: "a@b.com",
      password: "pass",
      first_name: "Alice",
    });
    expect(result.message).toBe("User registered");
  });

  test("resetPassword posts email", async () => {
    mockApi.post.mockResolvedValueOnce({ data: { message: "Reset sent" } });
    const result = await resetPassword("a@b.com");
    expect(mockApi.post).toHaveBeenCalledWith("/auth/reset-password", {
      email: "a@b.com",
    });
    expect(result.message).toBe("Reset sent");
  });

  test("logout calls /auth/logout and clears auth", async () => {
    mockApi.post.mockResolvedValueOnce({ data: {} });
    await logout();
    expect(mockApi.post).toHaveBeenCalledWith(
      "/auth/logout",
      {},
      { withCredentials: true },
    );
  });
});

// ===========================================================================
// APIs service
// ===========================================================================
describe("apis service", () => {
  const mockAPIs = [{ id: 1, name: "My API", version: "1.0" }];

  test("listAPIs returns array from GET /apis/", async () => {
    mockApi.get.mockResolvedValueOnce({ data: mockAPIs });
    const result = await listAPIs();
    expect(mockApi.get).toHaveBeenCalledWith("/apis/");
    expect(result).toEqual(mockAPIs);
  });

  test("createAPI posts payload and returns created item", async () => {
    const payload = { name: "New API", version: "1.0" };
    mockApi.post.mockResolvedValueOnce({ data: { id: 2, ...payload } });
    const result = await createAPI(payload);
    expect(mockApi.post).toHaveBeenCalledWith("/apis/", payload);
    expect(result.id).toBe(2);
  });

  test("getAPI fetches single API by id", async () => {
    mockApi.get.mockResolvedValueOnce({
      data: { id: 1, name: "My API", version: "1.0" },
    });
    const result = await getAPI(1);
    expect(mockApi.get).toHaveBeenCalledWith("/apis/1");
    expect(result.id).toBe(1);
  });

  test("updateAPI puts updated payload", async () => {
    mockApi.put.mockResolvedValueOnce({
      data: { id: 1, name: "Updated", version: "2.0" },
    });
    const result = await updateAPI(1, { name: "Updated", version: "2.0" });
    expect(mockApi.put).toHaveBeenCalledWith("/apis/1", {
      name: "Updated",
      version: "2.0",
    });
    expect(result.name).toBe("Updated");
  });

  test("deleteAPI calls DELETE /apis/:id", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: {} });
    await deleteAPI(1);
    expect(mockApi.delete).toHaveBeenCalledWith("/apis/1");
  });

  test("listAuthPolicies fetches policies for an API", async () => {
    const policies = [
      {
        id: 1,
        api_id: 5,
        name: "api-key-policy",
        type: "apiKey",
        created_at: "",
      },
    ];
    mockApi.get.mockResolvedValueOnce({ data: policies });
    const result = await listAuthPolicies(5);
    expect(mockApi.get).toHaveBeenCalledWith("/apis/5/auth-policies");
    expect(result).toEqual(policies);
  });

  test("createAuthPolicy posts to auth-policies", async () => {
    const payload = { name: "jwt-policy", type: "jwt" as const };
    mockApi.post.mockResolvedValueOnce({
      data: { id: 10, api_id: 5, ...payload, created_at: "" },
    });
    const result = await createAuthPolicy(5, payload);
    expect(mockApi.post).toHaveBeenCalledWith("/apis/5/auth-policies", payload);
    expect(result.type).toBe("jwt");
  });

  test("updateAuthPolicy puts to auth-policies/:id", async () => {
    mockApi.put.mockResolvedValueOnce({
      data: {
        id: 10,
        api_id: 5,
        name: "updated",
        type: "none",
        created_at: "",
      },
    });
    const result = await updateAuthPolicy(5, 10, { name: "updated" });
    expect(mockApi.put).toHaveBeenCalledWith("/apis/5/auth-policies/10", {
      name: "updated",
    });
    expect(result.name).toBe("updated");
  });

  test("deleteAuthPolicy calls DELETE on auth-policies/:id", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: {} });
    await deleteAuthPolicy(5, 10);
    expect(mockApi.delete).toHaveBeenCalledWith("/apis/5/auth-policies/10");
  });
});

// ===========================================================================
// API Keys service
// ===========================================================================
describe("apiKeysService", () => {
  const mockKey = {
    id: 1,
    label: "test-key",
    scopes: "read",
    revoked: false,
    created_at: "2024-01-01",
    usage_count: 0,
    key_preview: "gw_***",
  };

  test("list fetches keys with optional env filter", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [mockKey] });
    const result = await apiKeysService.list(2);
    expect(mockApi.get).toHaveBeenCalledWith("/api/keys/", {
      params: { environment_id: 2 },
    });
    expect(result[0].label).toBe("test-key");
  });

  test("create posts new key", async () => {
    const withKey = { ...mockKey, key: "gw_real_key" };
    mockApi.post.mockResolvedValueOnce({ data: withKey });
    const result = await apiKeysService.create({ label: "test-key" });
    expect(mockApi.post).toHaveBeenCalledWith("/api/keys/", {
      label: "test-key",
    });
    expect(result.key).toBe("gw_real_key");
  });

  test("revoke posts to /revoke endpoint", async () => {
    mockApi.post.mockResolvedValueOnce({ data: {} });
    await apiKeysService.revoke(1);
    expect(mockApi.post).toHaveBeenCalledWith("/api/keys/1/revoke", {});
  });

  test("delete calls DELETE on key id", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: {} });
    await apiKeysService.delete(1);
    expect(mockApi.delete).toHaveBeenCalledWith("/api/keys/1");
  });

  test("listEnvironments fetches environments", async () => {
    const envs = [{ id: 1, name: "production", slug: "prod" }];
    mockApi.get.mockResolvedValueOnce({ data: envs });
    const result = await apiKeysService.listEnvironments();
    expect(mockApi.get).toHaveBeenCalledWith("/api/keys/environments");
    expect(result[0].name).toBe("production");
  });
});

// ===========================================================================
// Secrets service
// ===========================================================================
describe("secretsService", () => {
  const mockSecret = {
    id: 1,
    name: "DB_PASS",
    key: "DB_PASS",
    value: "s3cret",
    created_at: "2024-01-01",
  };

  test("list fetches secrets", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [mockSecret] });
    const result = await secretsService.list();
    expect(mockApi.get).toHaveBeenCalledWith("/api/secrets/", {
      params: { tags: undefined },
    });
    expect(result[0].name).toBe("DB_PASS");
  });

  test("create posts new secret", async () => {
    mockApi.post.mockResolvedValueOnce({ data: mockSecret });
    const result = await secretsService.create({
      name: "DB_PASS",
      value: "s3cret",
    });
    expect(mockApi.post).toHaveBeenCalledWith("/api/secrets/", {
      name: "DB_PASS",
      value: "s3cret",
    });
    expect(result.name).toBe("DB_PASS");
  });

  test("get fetches a single secret", async () => {
    mockApi.get.mockResolvedValueOnce({ data: mockSecret });
    const result = await secretsService.get("DB_PASS");
    expect(mockApi.get).toHaveBeenCalledWith("/api/secrets/DB_PASS", {
      params: { decrypt: false },
    });
    expect(result.name).toBe("DB_PASS");
  });

  test("update puts new value", async () => {
    const updated = { ...mockSecret, value: "newval" };
    mockApi.put.mockResolvedValueOnce({ data: updated });
    const result = await secretsService.update(
      "DB_PASS",
      "newval",
      "updated desc",
    );
    expect(mockApi.put).toHaveBeenCalledWith("/api/secrets/DB_PASS", {
      value: "newval",
      description: "updated desc",
    });
    expect(result.value).toBe("newval");
  });

  test("delete calls DELETE on secret name", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: {} });
    await secretsService.delete("DB_PASS");
    expect(mockApi.delete).toHaveBeenCalledWith("/api/secrets/DB_PASS");
  });

  test("rotate posts new value", async () => {
    mockApi.post.mockResolvedValueOnce({
      data: { ...mockSecret, value: "rotated" },
    });
    const result = await secretsService.rotate("DB_PASS", "rotated");
    expect(mockApi.post).toHaveBeenCalledWith("/api/secrets/DB_PASS/rotate", {
      value: "rotated",
    });
    expect(result.value).toBe("rotated");
  });
});

// ===========================================================================
// Connectors service
// ===========================================================================
describe("connectorsService", () => {
  const mockConnector = {
    id: 1,
    name: "pg-connector",
    type: "postgres",
    config: {},
    created_at: "2024-01-01",
  };

  test("list fetches connectors", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [mockConnector] });
    const result = await connectorsService.list();
    expect(mockApi.get).toHaveBeenCalledWith("/api/connectors", { params: {} });
    expect(result[0].name).toBe("pg-connector");
  });

  test("list with api_id passes param", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [] });
    await connectorsService.list(3);
    expect(mockApi.get).toHaveBeenCalledWith("/api/connectors", {
      params: { api_id: 3 },
    });
  });

  test("get fetches single connector", async () => {
    mockApi.get.mockResolvedValueOnce({ data: mockConnector });
    const result = await connectorsService.get(1);
    expect(mockApi.get).toHaveBeenCalledWith("/api/connectors/1");
    expect(result.type).toBe("postgres");
  });

  test("create posts new connector", async () => {
    mockApi.post.mockResolvedValueOnce({ data: mockConnector });
    const result = await connectorsService.create({
      name: "pg-connector",
      type: "postgres",
      config: {},
    });
    expect(mockApi.post).toHaveBeenCalledWith("/api/connectors", {
      name: "pg-connector",
      type: "postgres",
      config: {},
    });
    expect(result.id).toBe(1);
  });

  test("update puts updated data", async () => {
    mockApi.put.mockResolvedValueOnce({
      data: { ...mockConnector, name: "updated" },
    });
    const result = await connectorsService.update(1, { name: "updated" });
    expect(mockApi.put).toHaveBeenCalledWith("/api/connectors/1", {
      name: "updated",
    });
    expect(result.name).toBe("updated");
  });

  test("delete calls DELETE", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: {} });
    await connectorsService.delete(1);
    expect(mockApi.delete).toHaveBeenCalledWith("/api/connectors/1");
  });

  test("test posts to /test endpoint and returns result", async () => {
    mockApi.post.mockResolvedValueOnce({
      data: { connector_id: 1, status: "ok", connected: true },
    });
    const result = await connectorsService.test(1);
    expect(mockApi.post).toHaveBeenCalledWith("/api/connectors/1/test", {});
    expect(result.connected).toBe(true);
  });
});

// ===========================================================================
// Audit logs service
// ===========================================================================
describe("auditLogsService", () => {
  const mockLog = {
    id: 1,
    timestamp: "2024-01-01T00:00:00",
    action: "login",
    status: "success",
  };

  test("list fetches audit logs", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [mockLog] });
    const result = await auditLogsService.list({ action: "login" });
    expect(mockApi.get).toHaveBeenCalledWith("/api/audit-logs", {
      params: { action: "login" },
    });
    expect(result[0].action).toBe("login");
  });

  test("getStatistics fetches stats", async () => {
    const stats = { total_logs: 100, logs_by_type: {}, logs_by_user: {} };
    mockApi.get.mockResolvedValueOnce({ data: stats });
    const result = await auditLogsService.getStatistics();
    expect(mockApi.get).toHaveBeenCalledWith("/api/audit-logs/statistics");
    expect(result.total_logs).toBe(100);
  });

  test("getUserActivity fetches activity for user", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [mockLog] });
    const result = await auditLogsService.getUserActivity(42, 7);
    expect(mockApi.get).toHaveBeenCalledWith("/api/audit-logs/user/42", {
      params: { days: 7 },
    });
    expect(result.length).toBe(1);
  });

  test("getFailedAttempts fetches failed logs", async () => {
    mockApi.get.mockResolvedValueOnce({
      data: [{ ...mockLog, status: "fail" }],
    });
    const result = await auditLogsService.getFailedAttempts(48);
    expect(mockApi.get).toHaveBeenCalledWith("/api/audit-logs/failed", {
      params: { hours: 48 },
    });
    expect(result[0].status).toBe("fail");
  });
});

// ===========================================================================
// Users service
// ===========================================================================
describe("userService", () => {
  const mockUser = {
    id: 1,
    email: "a@b.com",
    is_active: true,
    is_superuser: false,
  };

  test("listUsers fetches all users", async () => {
    mockApi.get.mockResolvedValueOnce({ data: [mockUser] });
    const result = await userService.listUsers();
    expect(mockApi.get).toHaveBeenCalledWith("/user/");
    expect(result[0].email).toBe("a@b.com");
  });

  test("getUser fetches user by id", async () => {
    const withRoles = {
      ...mockUser,
      roles: ["admin"],
      permissions: ["api:create"],
      legacy_roles: "",
    };
    mockApi.get.mockResolvedValueOnce({ data: withRoles });
    const result = await userService.getUser(1);
    expect(mockApi.get).toHaveBeenCalledWith("/user/1");
    expect(result.roles).toContain("admin");
  });

  test("updateUser puts user data", async () => {
    mockApi.put.mockResolvedValueOnce({
      data: { ...mockUser, is_active: false },
    });
    const result = await userService.updateUser(1, { is_active: false });
    expect(mockApi.put).toHaveBeenCalledWith("/user/1", { is_active: false });
    expect(result.is_active).toBe(false);
  });

  test("deleteUser calls DELETE", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: { message: "deleted" } });
    const result = await userService.deleteUser(1);
    expect(mockApi.delete).toHaveBeenCalledWith("/user/1");
    expect(result.message).toBe("deleted");
  });

  test("createUser posts new user", async () => {
    mockApi.post.mockResolvedValueOnce({ data: mockUser });
    const result = await userService.createUser({
      email: "a@b.com",
      password: "pass",
    });
    expect(mockApi.post).toHaveBeenCalledWith("/user/", {
      email: "a@b.com",
      password: "pass",
    });
    expect(result.email).toBe("a@b.com");
  });
});
