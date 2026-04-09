/**
 * Auth middleware — validates API key on routes where auth_required = true.
 * Attaches resolved ApiKey to res.locals for downstream middleware.
 */

import crypto from "crypto";
import type { Request, Response, NextFunction } from "express";
import { storage } from "../storage/index.js";
import type { GatewayRoute } from "../types.js";

function hashKey(raw: string): string {
  return crypto.createHash("sha256").update(raw).digest("hex");
}

export function makeAuthMiddleware(route: GatewayRoute) {
  return function auth(req: Request, res: Response, next: NextFunction): void {
    if (!route.auth_required) {
      next();
      return;
    }

    const header = req.headers["authorization"] ?? "";
    const raw = header.startsWith("Bearer ") ? header.slice(7) : header;

    if (!raw) {
      res.status(401).json({ error: "Missing API key" });
      return;
    }

    const hash = hashKey(raw);
    const apiKey = storage.getApiKey(hash);

    if (!apiKey) {
      res.status(401).json({ error: "Invalid API key" });
      return;
    }

    res.locals["apiKey"] = apiKey;
    next();
  };
}
