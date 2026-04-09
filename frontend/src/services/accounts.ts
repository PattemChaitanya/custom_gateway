import apiClient from "./api";

export interface Account {
  id: number;
  slug: string;
  name: string;
  plan: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface AccountUsage {
  account_id: number;
  slug: string;
  plan: string;
  daily_quota: number | null;
  used_today: number;
  remaining: number | null;
  quota_resets_at: string;
}

export interface AccountUpdatePayload {
  name?: string;
  plan?: string;
  status?: string;
}

export async function getAccount(id: number): Promise<Account> {
  const res = await apiClient.get<Account>(`/api/accounts/${id}`);
  return res.data;
}

export async function listAccounts(): Promise<Account[]> {
  const res = await apiClient.get<Account[]>("/api/accounts");
  return res.data;
}

export async function getAccountUsage(id: number): Promise<AccountUsage> {
  const res = await apiClient.get<AccountUsage>(`/api/accounts/${id}/usage`);
  return res.data;
}

export async function updateAccount(
  id: number,
  payload: AccountUpdatePayload,
): Promise<Account> {
  const res = await apiClient.put<Account>(`/api/accounts/${id}`, payload);
  return res.data;
}

export async function createAccount(payload: {
  slug: string;
  name: string;
  plan?: string;
}): Promise<Account> {
  const res = await apiClient.post<Account>("/api/accounts", payload);
  return res.data;
}

export async function deleteAccount(id: number): Promise<void> {
  await apiClient.delete(`/api/accounts/${id}`);
}

// ── Instance ──────────────────────────────────────────────────────────────────

export interface GatewayInstance {
  id: number;
  account_id: number;
  container_id: string | null;
  port: number;
  status: "provisioning" | "running" | "stopped" | "expired" | "error";
  gateway_url: string;
  created_at: string | null;
  expires_at: string;
  expires_in_seconds: number;
}

export async function getAccountInstance(accountId: number): Promise<GatewayInstance> {
  const res = await apiClient.get<GatewayInstance>(`/api/instances/${accountId}`);
  return res.data;
}
