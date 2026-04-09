/**
 * Proxy middleware — forwards the request to target_url.
 * Streams response back to the caller.
 */

import type { Request, Response, NextFunction } from "express";
import type { GatewayRoute } from "../types.js";

export function makeProxyMiddleware(route: GatewayRoute) {
  return async function proxy(req: Request, res: Response, next: NextFunction): Promise<void> {
    const url = `${route.target_url}${req.path}${req.url.includes("?") ? `?${req.url.split("?")[1]}` : ""}`;

    const headers: Record<string, string> = {};
    for (const [k, v] of Object.entries(req.headers)) {
      if (v !== undefined) headers[k] = Array.isArray(v) ? v.join(", ") : v;
    }
    // Inject gateway identity headers
    delete headers["host"];
    headers["x-gateway-account"] = route.account_id;
    headers["x-forwarded-host"] = req.hostname;

    try {
      const upstream = await fetch(url, {
        method: req.method,
        headers,
        body: ["GET", "HEAD"].includes(req.method) ? undefined : JSON.stringify(req.body),
        // @ts-expect-error — Node 18+ fetch supports duplex
        duplex: "half",
      });

      res.status(upstream.status);
      upstream.headers.forEach((value, key) => {
        if (!["transfer-encoding", "connection"].includes(key.toLowerCase())) {
          res.setHeader(key, value);
        }
      });

      const body = await upstream.text();
      res.send(body);
    } catch (err) {
      console.error(`[proxy] upstream error for route ${route.id}:`, err);
      next(err);
    }
  };
}
