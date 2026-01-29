import api from "./api";
import { getAuthStore } from "../hooks/useAuth";

export async function login(email: string, password: string) {
  const resp = await api.post(`/auth/login`, { email, password }, { withCredentials: true });
  const data = resp.data;
  if (data.access_token) {
    const store = getAuthStore();
    store.setTokens(data.access_token, data.refresh_token || null);
  }
  return data;
}

export async function logout() {
  const store = getAuthStore();
  try {
    // ask backend to clear refresh cookie if it manages cookies
    await api.post(`/auth/logout`, {}, { withCredentials: true });
  } finally {
    store.clearAuth();
  }
}

export async function me() {
  const resp = await api.get(`/auth/me`, { withCredentials: true });
  return resp.data;
}

export async function register(email: string, password: string, meta?: { firstName?: string; lastName?: string }) {
  const body: any = { email, password };
  if (meta) {
    if (meta.firstName) body.first_name = meta.firstName;
    if (meta.lastName) body.last_name = meta.lastName;
  }
  const resp = await api.post(`/auth/register`, body);
  return resp.data;
}

export async function resetPassword(email: string) {
  const resp = await api.post(`/auth/reset-password`, { email });
  return resp.data;
}

export async function verifyOtp(otp: string) {
  const resp = await api.post(`/auth/verify-otp`, { otp });
  return resp.data;
}
