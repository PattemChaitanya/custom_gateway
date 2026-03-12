/**
 * MSW-based integration tests for authentication service functions.
 * These tests verify the auth service layer against MSW mock handlers,
 * without relying on full component rendering or lazy-loaded routes.
 */
import axios from "axios";

const BASE = "http://localhost:8000";

describe("Auth service via MSW handlers", () => {
  test("POST /auth/login returns access_token for valid credentials", async () => {
    const resp = await axios.post(`${BASE}/auth/login`, {
      email: "alice@example.com",
      password: "password123",
    });
    expect(resp.status).toBe(200);
    expect(resp.data.access_token).toBe("access-alice@example.com");
    expect(typeof resp.data.refresh_token).toBe("string");
  });

  test("GET /auth/me returns email derived from Bearer token", async () => {
    const resp = await axios.get(`${BASE}/auth/me`, {
      headers: { Authorization: "Bearer access-bob@example.com" },
    });
    expect(resp.status).toBe(200);
    expect(resp.data.email).toBe("bob@example.com");
  });

  test("POST /auth/register returns 201 success", async () => {
    const resp = await axios.post(`${BASE}/auth/register`, {
      email: "newuser@example.com",
      password: "securepass",
    });
    expect(resp.status).toBe(201);
    expect(resp.data.message).toBe("User registered");
  });

  test("POST /auth/refresh-tokens rotates tokens", async () => {
    // First login to seed the current refresh token in MSW state
    const loginResp = await axios.post(`${BASE}/auth/login`, {
      email: "carol@example.com",
      password: "pass",
    });
    const refreshToken = loginResp.data.refresh_token;

    const refreshResp = await axios.post(`${BASE}/auth/refresh-tokens`, {
      refresh_token: refreshToken,
    });
    expect(refreshResp.status).toBe(200);
    expect(refreshResp.data.access_token).toBe("access-refreshed");
    expect(typeof refreshResp.data.refresh_token).toBe("string");
  });

  test("concurrent GET /auth/me requests both resolve successfully", async () => {
    const token = "access-dave@example.com";
    const headers = { Authorization: `Bearer ${token}` };

    const [r1, r2] = await Promise.all([
      axios.get(`${BASE}/auth/me`, { headers }),
      axios.get(`${BASE}/auth/me`, { headers }),
    ]);

    expect(r1.data.email).toBe("dave@example.com");
    expect(r2.data.email).toBe("dave@example.com");
  });

  test("POST /auth/verify-otp accepts correct OTP", async () => {
    const resp = await axios.post(`${BASE}/auth/verify-otp`, { otp: "9999" });
    expect(resp.status).toBe(200);
    expect(resp.data.message).toBe("OTP verified");
  });
});
