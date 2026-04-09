/**
 * L1 — In-memory store.
 * Fastest tier. Lost on process restart.
 */

import type { GatewayRoute, ApiKey } from "../types.js";

interface MemoryStore {
  routes: Map<string, GatewayRoute>;
  apiKeys: Map<string, ApiKey>; // keyed by key_hash
}

const store: MemoryStore = {
  routes: new Map(),
  apiKeys: new Map(),
};

export const memory = {
  setRoutes(routes: GatewayRoute[]): void {
    store.routes.clear();
    for (const r of routes) store.routes.set(r.id, r);
  },

  getRoutes(): GatewayRoute[] {
    return [...store.routes.values()].filter((r) => r.active);
  },

  setApiKeys(keys: ApiKey[]): void {
    store.apiKeys.clear();
    for (const k of keys) store.apiKeys.set(k.key_hash, k);
  },

  getApiKey(hash: string): ApiKey | undefined {
    return store.apiKeys.get(hash);
  },

  clear(): void {
    store.routes.clear();
    store.apiKeys.clear();
  },
};
