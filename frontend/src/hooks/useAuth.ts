import create from "zustand";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  profile?: { email?: string | null } | null;
  setTokens: (access: string, refresh: string) => void;
  clearAuth: () => void;
  setProfile: (p: { email?: string | null } | null) => void;
};

// localStorage keys
const LS_ACCESS = "access_token";
const LS_REFRESH = "refresh_token";

function safeGetLS(key: string) {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

function safeSetLS(key: string, val: string | null) {
  try {
    if (typeof window === "undefined") return;
    if (val === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, val);
  } catch (_) {
    // ignore
  }
}

const initialAccess = safeGetLS(LS_ACCESS);
const initialRefresh = safeGetLS(LS_REFRESH);

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: initialAccess,
  refreshToken: initialRefresh,
  profile: null,
  setTokens: (access, refresh) => {
    set(() => ({ accessToken: access, refreshToken: refresh }));
    safeSetLS(LS_ACCESS, access);
    safeSetLS(LS_REFRESH, refresh || "");
  },
  setProfile: (p) => set(() => ({ profile: p })),
  clearAuth: () => {
    set(() => ({ accessToken: null, refreshToken: null, profile: null }));
    // clear persisted tokens
    safeSetLS(LS_ACCESS, null);
    safeSetLS(LS_REFRESH, null);
    // keep remember preference intact — user may want to remain remembered but logged out
  },
}));

// helper to get store outside React components (for api client)
export function getAuthStore() {
  return useAuthStore.getState();
}

export default useAuthStore;
