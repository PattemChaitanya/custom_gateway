/**
 * Shared TypeScript types for the gateway runtime.
 */

export interface GatewayRoute {
  id: string;
  account_id: string;
  path: string;
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "ANY";
  target_url: string;
  auth_required: boolean;
  validation_schema: ValidationSchema | null;
  active: boolean;
}

export interface ValidationSchema {
  path_params?: Record<string, ParamSchema>;
  query_params?: Record<string, ParamSchema>;
  body?: object; // JSON Schema object
  headers?: Record<string, HeaderSchema>;
}

export interface ParamSchema {
  type: "string" | "number" | "integer" | "boolean";
  pattern?: string;
  required?: boolean;
  enum?: string[];
}

export interface HeaderSchema {
  required: boolean;
  pattern?: string;
}

export interface ApiKey {
  id: string;
  account_id: string;
  key_hash: string;
  name: string;
  rate_limit_rpm: number;
}

export interface AccountConfig {
  account_id: string;
  routes: GatewayRoute[];
  api_keys: ApiKey[];
}

export interface RequestLog {
  id: string;
  account_id: string;
  route_id: string | null;
  method: string;
  path: string;
  status_code: number;
  latency_ms: number;
  api_key_id: string | null;
  timestamp: string; // ISO string
}
