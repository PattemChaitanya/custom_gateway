/**
 * Tiered storage facade.
 *
 * Write-through: every write hits L1 (memory) AND L2 (SQLite) if available.
 * Read waterfall: L1 → L2 (used on boot if control plane unreachable).
 *
 * L3 (PostgreSQL) is owned by the control plane — the runtime fetches from
 * it via HTTP (/internal/config) rather than connecting directly.
 */

import { memory } from "./memory.js";
import { sqlite } from "./sqlite.js";
import type { GatewayRoute, ApiKey } from "../types.js";

export const storage = {
  setRoutes(routes: GatewayRoute[]): void {
    // L1 always
    memory.setRoutes(routes);
    // L2 if available
    if (sqlite.isAvailable()) {
      try {
        sqlite.saveRoutes(routes);
      } catch (err) {
        console.warn("[storage] SQLite write failed for routes:", err);
      }
    }
  },

  getRoutes(): GatewayRoute[] {
    // L1 first
    const fromMemory = memory.getRoutes();
    if (fromMemory.length > 0) return fromMemory;

    // L2 fallback
    if (sqlite.isAvailable()) {
      const fromSqlite = sqlite.loadRoutes().filter((r) => r.active);
      if (fromSqlite.length > 0) {
        memory.setRoutes(fromSqlite); // warm L1
        return fromSqlite;
      }
    }

    return [];
  },

  setApiKeys(keys: ApiKey[]): void {
    memory.setApiKeys(keys);
    if (sqlite.isAvailable()) {
      try {
        sqlite.saveApiKeys(keys);
      } catch (err) {
        console.warn("[storage] SQLite write failed for api_keys:", err);
      }
    }
  },

  getApiKey(hash: string): ApiKey | undefined {
    // L1
    const fromMemory = memory.getApiKey(hash);
    if (fromMemory) return fromMemory;

    // L2 fallback — warm L1 on hit
    if (sqlite.isAvailable()) {
      const keys = sqlite.loadApiKeys();
      if (keys.length > 0) {
        memory.setApiKeys(keys);
        return keys.find((k) => k.key_hash === hash);
      }
    }

    return undefined;
  },

  clear(): void {
    memory.clear();
  },
};
