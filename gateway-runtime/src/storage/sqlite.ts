/**
 * L2 — SQLite fallback store.
 * Persists routes and API keys across container restarts.
 * Used when control plane is temporarily unreachable on boot.
 */

import Database from "better-sqlite3";
import { config } from "../config.js";
import type { GatewayRoute, ApiKey } from "../types.js";

let db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!db) {
    db = new Database(config.sqlitePath);
    db.pragma("journal_mode = WAL");
    initSchema(db);
  }
  return db;
}

function initSchema(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS routes (
      id TEXT PRIMARY KEY,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS api_keys (
      key_hash TEXT PRIMARY KEY,
      data TEXT NOT NULL
    );
  `);
}

export const sqlite = {
  isAvailable(): boolean {
    try {
      getDb();
      return true;
    } catch {
      return false;
    }
  },

  saveRoutes(routes: GatewayRoute[]): void {
    const db = getDb();
    const del = db.prepare("DELETE FROM routes");
    const ins = db.prepare("INSERT OR REPLACE INTO routes (id, data) VALUES (?, ?)");
    const tx = db.transaction((rows: GatewayRoute[]) => {
      del.run();
      for (const r of rows) ins.run(r.id, JSON.stringify(r));
    });
    tx(routes);
  },

  loadRoutes(): GatewayRoute[] {
    try {
      const rows = getDb().prepare("SELECT data FROM routes").all() as { data: string }[];
      return rows.map((r) => JSON.parse(r.data) as GatewayRoute);
    } catch {
      return [];
    }
  },

  saveApiKeys(keys: ApiKey[]): void {
    const db = getDb();
    const del = db.prepare("DELETE FROM api_keys");
    const ins = db.prepare("INSERT OR REPLACE INTO api_keys (key_hash, data) VALUES (?, ?)");
    const tx = db.transaction((rows: ApiKey[]) => {
      del.run();
      for (const k of rows) ins.run(k.key_hash, JSON.stringify(k));
    });
    tx(keys);
  },

  loadApiKeys(): ApiKey[] {
    try {
      const rows = getDb().prepare("SELECT data FROM api_keys").all() as { data: string }[];
      return rows.map((r) => JSON.parse(r.data) as ApiKey);
    } catch {
      return [];
    }
  },
};
