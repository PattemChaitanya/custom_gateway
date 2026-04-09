/**
 * Dynamic route registry — registers Express handlers for all active gateway routes.
 *
 * Middleware chain per route: sanitize → auth → rateLimit → validate → proxy
 *
 * Called once on boot, and again on every /internal/reload.
 */

import express, { type Express } from "express";
import type { Redis } from "ioredis";
import { storage } from "./storage/index.js";
import { sanitize } from "./middleware/sanitize.js";
import { makeAuthMiddleware } from "./middleware/auth.js";
import { makeRateLimitMiddleware } from "./middleware/rateLimit.js";
import { makeValidateMiddleware } from "./middleware/validate.js";
import { makeProxyMiddleware } from "./middleware/proxy.js";
import { pushLog } from "./logger/logBuffer.js";

// We swap the router on reload to avoid stale handlers
let currentRouter = express.Router();

export function getRouter(): express.Router {
  return currentRouter;
}

export function rebuildRoutes(redis: Redis): void {
  const routes = storage.getRoutes();
  const router = express.Router();

  for (const route of routes) {
    const method = route.method === "ANY" ? "all" : route.method.toLowerCase();

    (router as unknown as Record<string, (...args: unknown[]) => void>)[method](
      route.path,
      sanitize,
      makeAuthMiddleware(route),
      makeRateLimitMiddleware(redis),
      makeValidateMiddleware(route),
      makeProxyMiddleware(route)
    );
  }

  currentRouter = router;
  console.log(`[registry] registered ${routes.length} routes`);
}

/**
 * Attach request logging to every response on the app level.
 */
export function attachRequestLogger(app: Express): void {
  app.use((req, res, next) => {
    const start = Date.now();
    const routeId = res.locals["routeId"] as string | undefined ?? null;
    const apiKeyId = (res.locals["apiKey"] as { id?: string } | undefined)?.id ?? null;

    res.on("finish", () => {
      pushLog({
        route_id: routeId,
        method: req.method,
        path: req.path,
        status_code: res.statusCode,
        latency_ms: Date.now() - start,
        api_key_id: apiKeyId,
      });
    });

    next();
  });
}
