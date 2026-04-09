/**
 * POST /internal/reload
 * Called by the control plane when routes are created/updated/deleted.
 * Re-fetches config from the control plane and hot-reloads routes without restart.
 */

import { Router } from "express";
import { loadConfig } from "../boot.js";
import { rebuildRoutes } from "../routeRegistry.js";
import { config } from "../config.js";
import { getRedis } from "../redisClient.js";

export const reloadRouter = Router();

reloadRouter.post("/reload", async (req, res) => {
  // Authenticate with account secret
  const secret = req.headers["x-account-secret"];
  if (secret !== config.accountSecret) {
    res.status(403).json({ error: "Forbidden" });
    return;
  }

  try {
    await loadConfig();
    rebuildRoutes(getRedis());
    res.json({ status: "reloaded" });
  } catch (err) {
    console.error("[reload] failed to reload config:", err);
    res.status(500).json({ error: "Reload failed" });
  }
});
