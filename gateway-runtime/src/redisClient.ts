/**
 * Shared Redis client singleton.
 * Initialized in index.ts; accessed via getRedis() everywhere else
 * to avoid circular imports through index.ts.
 */

import Redis from "ioredis";

let client: Redis | null = null;

export function initRedis(url: string): Redis {
  client = new Redis(url, {
    lazyConnect: true,
    enableOfflineQueue: false,
  });
  client.on("error", (err) => console.warn("[redis] connection error:", err.message));
  return client;
}

export function getRedis(): Redis {
  if (!client) throw new Error("Redis client not initialized — call initRedis() first");
  return client;
}
