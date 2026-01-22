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
