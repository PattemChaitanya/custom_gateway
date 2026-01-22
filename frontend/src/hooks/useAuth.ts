import create from "zustand";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  profile?: { email?: string | null } | null;
  setTokens: (access: string, refresh: string) => void;
  clearAuth: () => void;
  setProfile: (p: { email?: string | null } | null) => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  profile: null,
  setTokens: (access, refresh) => set(() => ({ accessToken: access, refreshToken: refresh })),
  setProfile: (p) => set(() => ({ profile: p })),
  clearAuth: () => {
    set(() => ({ accessToken: null, refreshToken: null, profile: null }));
  },
}));

// helper to get store outside React components (for api client)
export function getAuthStore() {
  return useAuthStore.getState();
}

export default useAuthStore;
