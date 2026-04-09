/**
 * Sanitize middleware — strips dangerous headers forwarded to upstream.
 */

import type { Request, Response, NextFunction } from "express";

const STRIP_HEADERS = [
  "x-forwarded-for",
  "x-real-ip",
  "x-original-url",
  "x-rewrite-url",
];

export function sanitize(req: Request, _res: Response, next: NextFunction): void {
  for (const h of STRIP_HEADERS) {
    delete req.headers[h];
  }
  // Reject requests with null bytes anywhere in the URL
  if (req.url.includes("\0")) {
    _res.status(400).json({ error: "Invalid request" });
    return;
  }
  next();
}
