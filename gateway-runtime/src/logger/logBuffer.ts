/**
 * Batched request log buffer.
 *
 * Accumulates RequestLog entries in memory and flushes them to the control
 * plane's POST /internal/logs endpoint every 5 seconds OR when 50 logs
 * accumulate — whichever comes first.
 */

import { v4 as uuidv4 } from "uuid";
import { config } from "../config.js";
import type { RequestLog } from "../types.js";

const buffer: RequestLog[] = [];
let flushTimer: NodeJS.Timeout | null = null;

async function flush(): Promise<void> {
  if (buffer.length === 0) return;

  const batch = buffer.splice(0, buffer.length);
  const url = `${config.controlPlaneUrl}/internal/logs`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Account-Secret": config.accountSecret,
        "X-Account-Id": config.accountId,
      },
      body: JSON.stringify({ logs: batch }),
    });
    if (!res.ok) {
      console.warn(`[logBuffer] flush returned ${res.status} — ${batch.length} logs dropped`);
    }
  } catch (err) {
    console.warn("[logBuffer] flush failed — logs dropped:", err);
    // Do NOT re-buffer; avoids unbounded memory growth on sustained outage
  }
}

export function startLogFlusher(): void {
  flushTimer = setInterval(() => {
    flush().catch(() => undefined);
  }, config.logFlushIntervalMs);
}

export function stopLogFlusher(): void {
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
  // Best-effort final flush on shutdown
  flush().catch(() => undefined);
}

export function pushLog(entry: Omit<RequestLog, "id" | "timestamp" | "account_id">): void {
  buffer.push({
    id: uuidv4(),
    account_id: config.accountId,
    timestamp: new Date().toISOString(),
    ...entry,
  });

  if (buffer.length >= config.logFlushBatchSize) {
    flush().catch(() => undefined);
  }
}
