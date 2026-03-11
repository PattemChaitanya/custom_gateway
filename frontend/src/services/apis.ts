import api from "./api";

export interface APIItem {
  id: number;
  name: string;
  version: string;
  description?: string;
  // optional UI fields to carry the API config and metadata
  type?: "rest" | "graphql";
  format?: "resource" | "json" | "terraform";
  createdAt?: string;
  updatedAt?: string;
  // stored configuration body (JSON/YAML/terraform) - backend may accept string or object
  config?: any;
}

export async function listAPIs(): Promise<APIItem[]> {
  const resp = await api.get("/apis/");
  return resp.data as APIItem[];
}

export async function createAPI(payload: Partial<APIItem>) {
  const resp = await api.post("/apis/", payload);
  return resp.data as APIItem;
}

export async function deleteAPI(id: number) {
  const resp = await api.delete(`/apis/${id}`);
  return resp;
}

export async function getAPI(id: number) {
  const resp = await api.get(`/apis/${id}`);
  return resp.data as APIItem;
}

export async function updateAPI(id: number, payload: Partial<APIItem>) {
  const resp = await api.put(`/apis/${id}`, payload);
  return resp.data as APIItem;
}

// ── Auth Policies ──────────────────────────────────────────────────────────

export interface AuthPolicy {
  id: number;
  api_id: number;
  name: string;
  type: string;
  config?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface AuthPolicyCreate {
  name: string;
  type: "none" | "open" | "apiKey" | "jwt" | "bearer" | "oauth2";
  config?: Record<string, any>;
}

export const listAuthPolicies = (apiId: number): Promise<AuthPolicy[]> =>
  api.get(`/apis/${apiId}/auth-policies`).then((r) => r.data);

export const createAuthPolicy = (
  apiId: number,
  payload: AuthPolicyCreate,
): Promise<AuthPolicy> =>
  api.post(`/apis/${apiId}/auth-policies`, payload).then((r) => r.data);

export const updateAuthPolicy = (
  apiId: number,
  id: number,
  payload: Partial<AuthPolicyCreate>,
): Promise<AuthPolicy> =>
  api.put(`/apis/${apiId}/auth-policies/${id}`, payload).then((r) => r.data);

export const deleteAuthPolicy = (apiId: number, id: number) =>
  api.delete(`/apis/${apiId}/auth-policies/${id}`);

// ── Schemas ────────────────────────────────────────────────────────────────

export interface ApiSchema {
  id: number;
  api_id: number;
  name: string;
  definition?: Record<string, any>;
  raw?: string;
  created_at?: string;
}

export const listSchemas = (apiId: number): Promise<ApiSchema[]> =>
  api.get(`/apis/${apiId}/schemas`).then((r) => r.data);

export const createSchema = (
  apiId: number,
  payload: { name: string; definition?: object; raw?: string },
): Promise<ApiSchema> =>
  api.post(`/apis/${apiId}/schemas`, payload).then((r) => r.data);

export const updateSchema = (
  apiId: number,
  id: number,
  payload: Partial<{ name: string; definition: object; raw: string }>,
): Promise<ApiSchema> =>
  api.put(`/apis/${apiId}/schemas/${id}`, payload).then((r) => r.data);

export const deleteSchema = (apiId: number, id: number) =>
  api.delete(`/apis/${apiId}/schemas/${id}`);

// ── Backend Pools ──────────────────────────────────────────────────────────

export interface BackendPool {
  id: number;
  api_id: number;
  name: string;
  algorithm: string;
  backends: { url: string; weight: number; healthy: boolean }[];
  health_check_url?: string;
  health_check_interval: number;
}

export const listBackendPools = (apiId: number): Promise<BackendPool[]> =>
  api.get(`/apis/${apiId}/backend-pools`).then((r) => r.data);

export const createBackendPool = (
  apiId: number,
  payload: object,
): Promise<BackendPool> =>
  api.post(`/apis/${apiId}/backend-pools`, payload).then((r) => r.data);

export const updateBackendPool = (
  apiId: number,
  id: number,
  payload: object,
): Promise<BackendPool> =>
  api.put(`/apis/${apiId}/backend-pools/${id}`, payload).then((r) => r.data);

export const deleteBackendPool = (apiId: number, id: number) =>
  api.delete(`/apis/${apiId}/backend-pools/${id}`);

export const patchBackendHealth = (
  apiId: number,
  id: number,
  url: string,
  healthy: boolean,
): Promise<BackendPool> =>
  api
    .patch(
      `/apis/${apiId}/backend-pools/${id}/backends/${encodeURIComponent(url)}/health`,
      { healthy },
    )
    .then((r) => r.data);

// ── Deployments ────────────────────────────────────────────────────────────

export interface APIDeployment {
  id: number;
  api_id: number;
  environment_id: number;
  status: string;
  deployed_by?: number;
  target_url_override?: string;
  notes?: string;
  deployed_at?: string;
}

export const listDeployments = (apiId: number): Promise<APIDeployment[]> =>
  api.get(`/apis/${apiId}/deployments`).then((r) => r.data);

export const createDeployment = (
  apiId: number,
  payload: object,
): Promise<APIDeployment> =>
  api.post(`/apis/${apiId}/deployments`, payload).then((r) => r.data);

export const deleteDeployment = (apiId: number, id: number) =>
  api.delete(`/apis/${apiId}/deployments/${id}`);

// ── Rate Limits ────────────────────────────────────────────────────────────

export interface RateLimit {
  id: number;
  api_id: number;
  limit: number;
  window_seconds: number;
  key_type: string;
  algorithm: string;
}

export const listRateLimits = (apiId: number): Promise<RateLimit[]> =>
  api.get(`/apis/${apiId}/rate-limits`).then((r) => r.data);

export const createRateLimit = (
  apiId: number,
  payload: object,
): Promise<RateLimit> =>
  api.post(`/apis/${apiId}/rate-limits`, payload).then((r) => r.data);

export const updateRateLimit = (
  apiId: number,
  id: number,
  payload: object,
): Promise<RateLimit> =>
  api.put(`/apis/${apiId}/rate-limits/${id}`, payload).then((r) => r.data);

export const deleteRateLimit = (apiId: number, id: number) =>
  api.delete(`/apis/${apiId}/rate-limits/${id}`);
