/**
 * Rate limiting middleware — Redis sorted-set sliding window.
 *
 * Key format: ratelimit:{account_id}:{api_key_hash}
 * Default: 100 req/min; overridden by ApiKey.rate_limit_rpm.
 */

import type { Request, Response, NextFunction } from "express";
import type { Redis } from "ioredis";
import { config } from "../config.js";
import type { ApiKey } from "../types.js";

const DEFAULT_RPM = 100;

export function makeRateLimitMiddleware(redis: Redis) {
  return function rateLimit(req: Request, res: Response, next: NextFunction): void {
    const apiKey: ApiKey | undefined = res.locals["apiKey"] as ApiKey | undefined;

    // No API key means route is public — skip rate limiting
    if (!apiKey) {
      next();
      return;
    }

    const rpm = apiKey.rate_limit_rpm ?? DEFAULT_RPM;
    const windowMs = 60_000;
    const now = Date.now();
    const windowStart = now - windowMs;
    const redisKey = `ratelimit:${config.accountId}:${apiKey.key_hash}`;

    // Sliding window via sorted set — run atomically with a pipeline
    const pipeline = redis.pipeline();
    pipeline.zremrangebyscore(redisKey, "-inf", windowStart);   // remove old entries
    pipeline.zadd(redisKey, now, `${now}-${Math.random()}`);    // add current request
    pipeline.zcard(redisKey);                                    // count in window
    pipeline.pexpire(redisKey, windowMs);                       // TTL cleanup

    pipeline.exec().then((results) => {
      if (!results) {
        next();
        return;
      }
      const countResult = results[2];
      const count = (countResult?.[1] as number | null) ?? 0;

      if (count > rpm) {
        const retryAfterSecs = Math.ceil(windowMs / 1000);
        res.setHeader("Retry-After", retryAfterSecs);
        res.status(429).json({
          error: "Too Many Requests",
          retry_after: retryAfterSecs,
        });
        return;
      }
      next();
    }).catch(() => next()); // fail open on Redis errors
  };
}
