import axios from "axios";
import { getAuthStore } from "../hooks/useAuth";

const API_URL = (() => {
  // Prefer explicit VITE_API_URL via process.env (used in Jest and Node) or a
  // runtime shim on globalThis (used by Vite in the browser).
  try {
    if (typeof process !== "undefined" && (process as any).env && (process as any).env.VITE_API_URL) {
      return (process as any).env.VITE_API_URL as string;
    }
  } catch (_) {}

  try {
    const g = globalThis as any;
    if (g && g.__VITE_API_URL) return g.__VITE_API_URL as string;
  } catch (_) {}

  return "http://localhost:8000";
})();

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // allow sending/receiving HttpOnly cookies for refresh
});

// simple refresh flow with queue to avoid parallel refreshes
let isRefreshing = false;
let refreshQueue: Array<(token?: string) => void> = [];
const MAX_REFRESH_RETRIES = 3;

function processQueue(_error: any, token: string | null = null) {
  // _error reserved for symmetry with queue handler signature
  refreshQueue.forEach((cb) => cb(token || undefined));
  refreshQueue = [];
}

api.interceptors.request.use((config) => {
  const store = getAuthStore();
  const token = store.accessToken || null;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;
    if (!originalRequest) return Promise.reject(err);

    // on 401 try refresh (use cookie-based refresh when possible)
    if (err.response && err.response.status === 401 && !originalRequest.__isRetry) {
      const store = getAuthStore();

      // if a refresh is already in progress, queue
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push((token?: string) => {
            if (!token) return reject(err);
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      isRefreshing = true;
      let attempt = 0;
      let lastError: any = null;
      while (attempt < MAX_REFRESH_RETRIES) {
        try {
          // send refresh request without body to allow backend to read HttpOnly cookie
          const resp = await axios.post(`${API_URL}/auth/refresh-tokens`, {}, { withCredentials: true });
          const data = resp.data;
          const newAccess = data.access_token;
          // backend may rotate refresh token and set cookie; rely on cookie for subsequent calls
          store.setTokens(newAccess, data.refresh_token || null);
          originalRequest.__isRetry = true;
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          processQueue(null, newAccess);
          return api(originalRequest);
        } catch (e) {
          lastError = e;
          attempt += 1;
          // short backoff
          await new Promise((r) => setTimeout(r, 250 * attempt));
        }
      }
      processQueue(lastError, null);
      getAuthStore().clearAuth();
      isRefreshing = false;
      return Promise.reject(lastError);
    }
    return Promise.reject(err);
  }
);

export default api;
