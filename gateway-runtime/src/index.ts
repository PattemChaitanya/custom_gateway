/**
 * FlowGate Gateway Runtime — Entry Point
 *
 * Boot sequence:
 *   1. Load config from control plane (with SQLite L2 fallback)
 *   2. Register Express route handlers
 *   3. Start log flusher
 *   4. Start 48h self-termination timer
 *   5. Listen on GATEWAY_PORT
 */

import express from "express";
import { config } from "./config.js";
import { initRedis } from "./redisClient.js";
import { loadConfig } from "./boot.js";
import { getRouter, rebuildRoutes, attachRequestLogger } from "./routeRegistry.js";
import { healthRouter } from "./internal/health.js";
import { reloadRouter } from "./internal/reload.js";
import { startLogFlusher, stopLogFlusher } from "./logger/logBuffer.js";

// ── Redis client ──────────────────────────────────────────────────────────────
const redis = initRedis(config.redisUrl);

// ── Express app ───────────────────────────────────────────────────────────────
const app = express();

app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: true }));

// Internal endpoints (not proxied, no rate limiting)
app.use("/internal", healthRouter);
app.use("/internal", reloadRouter);

// Request logging (attaches finish listener)
attachRequestLogger(app);

// Gateway routes — uses swappable router rebuilt on each reload
app.use((req, res, next) => getRouter()(req, res, next));

// Generic error handler
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error("[gateway] unhandled error:", err);
  res.status(502).json({ error: "Bad Gateway" });
});

// ── 48-hour self-termination ──────────────────────────────────────────────────
function startInstanceTimer(): void {
  console.log(
    `[timer] instance will self-terminate in 48h at ${new Date(Date.now() + config.instanceTtlMs).toISOString()}`
  );

  // Warning at 47h
  setTimeout(() => {
    console.warn("[timer] WARNING: instance will self-terminate in 1 hour");
  }, config.instanceWarnMs);

  // Graceful shutdown at 48h
  setTimeout(() => {
    console.warn("[timer] 48h TTL reached — shutting down instance");
    gracefulShutdown("TTL_EXPIRED");
  }, config.instanceTtlMs);
}

// ── Graceful shutdown ─────────────────────────────────────────────────────────
function gracefulShutdown(reason: string): void {
  console.log(`[shutdown] reason=${reason}`);
  stopLogFlusher();
  redis.disconnect();
  process.exit(0);
}

process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGINT", () => gracefulShutdown("SIGINT"));

// ── Boot ──────────────────────────────────────────────────────────────────────
(async () => {
  try {
    console.log(`[boot] starting gateway for account=${config.accountId} port=${config.gatewayPort}`);

    await redis.connect().catch(() => {
      console.warn("[boot] Redis unavailable — rate limiting will be skipped");
    });

    await loadConfig();
    rebuildRoutes(redis);
    startLogFlusher();
    startInstanceTimer();

    app.listen(config.gatewayPort, () => {
      console.log(`[gateway] listening on :${config.gatewayPort}`);
    });
  } catch (err) {
    console.error("[boot] fatal error during startup:", err);
    process.exit(1);
  }
})();

