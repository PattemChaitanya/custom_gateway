/**
 * Typed config loaded from environment variables.
 * All required vars throw on startup if missing.
 */

function required(name: string): string {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

export const config = {
  accountId: required("ACCOUNT_ID"),
  gatewayPort: parseInt(required("GATEWAY_PORT"), 10),
  redisUrl: required("REDIS_URL"),
  controlPlaneUrl: required("CONTROL_PLANE_URL").replace(/\/$/, ""),
  accountSecret: required("ACCOUNT_SECRET"),
  sqlitePath: process.env["SQLITE_PATH"] ?? "/data/gateway.db",

  // 48h in ms — instance self-terminates after this duration
  instanceTtlMs: 48 * 60 * 60 * 1000,
  instanceWarnMs: 47 * 60 * 60 * 1000,

  // Log batching
  logFlushIntervalMs: 5_000,
  logFlushBatchSize: 50,
} as const;
