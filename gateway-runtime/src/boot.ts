/**
 * Boot sequence — fetches config from control plane on startup and after /internal/reload.
 *
 * GET {CONTROL_PLANE_URL}/internal/config/{ACCOUNT_ID}
 * Authenticated with X-Account-Secret header.
 *
 * Falls back to SQLite (L2) if the control plane is unreachable.
 */

import { config } from "./config.js";
import { storage } from "./storage/index.js";
import { sqlite } from "./storage/sqlite.js";
import type { AccountConfig } from "./types.js";

export async function loadConfig(): Promise<void> {
  const url = `${config.controlPlaneUrl}/internal/config/${config.accountId}`;

  let accountConfig: AccountConfig | null = null;

  try {
    const res = await fetch(url, {
      headers: {
        "X-Account-Secret": config.accountSecret,
        "X-Account-Id": config.accountId,
      },
      signal: AbortSignal.timeout(10_000),
    });

    if (!res.ok) {
      throw new Error(`Control plane returned ${res.status}`);
    }

    accountConfig = (await res.json()) as AccountConfig;
    console.log(
      `[boot] loaded ${accountConfig.routes.length} routes and ${accountConfig.api_keys.length} API keys from control plane`
    );
  } catch (err) {
    console.warn("[boot] could not reach control plane, falling back to SQLite L2:", err);

    // L2 fallback
    if (sqlite.isAvailable()) {
      const routes = sqlite.loadRoutes();
      const apiKeys = sqlite.loadApiKeys();
      if (routes.length > 0 || apiKeys.length > 0) {
        console.warn(`[boot] L2 fallback: ${routes.length} routes, ${apiKeys.length} keys`);
        storage.setRoutes(routes);
        storage.setApiKeys(apiKeys);
        return;
      }
    }

    // Hard fail — nothing to serve
    throw new Error("Control plane unreachable and no SQLite fallback data available");
  }

  // Write-through: save to L1 + L2
  storage.setRoutes(accountConfig.routes);
  storage.setApiKeys(accountConfig.api_keys);
}
