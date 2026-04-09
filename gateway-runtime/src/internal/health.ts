/**
 * GET /internal/health
 * Used by instance_manager.py to poll until the container is ready.
 */

import { Router } from "express";
import { storage } from "../storage/index.js";

export const healthRouter = Router();

healthRouter.get("/health", (_req, res) => {
  const routes = storage.getRoutes();
  res.json({
    status: "ok",
    account_id: process.env["ACCOUNT_ID"],
    routes_loaded: routes.length,
    uptime_seconds: Math.floor(process.uptime()),
  });
});
