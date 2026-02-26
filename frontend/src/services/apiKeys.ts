import api from "./api";

export interface APIKey {
  id: number;
  key?: string; // Only returned on creation
  label: string;
  scopes: string;
  environment_id?: number;
  revoked: boolean;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
  usage_count: number;
  key_preview: string;
}

export interface CreateAPIKeyRequest {
  label: string;
  scopes?: string;
  environment_id?: number;
  expires_in_days?: number;
  metadata?: Record<string, any>;
}

export const apiKeysService = {
  list: async (environmentId?: number): Promise<APIKey[]> => {
    const response = await api.get(`/api/keys`, {
      params: { environment_id: environmentId },
    });
    return response.data;
  },

  create: async (
    data: CreateAPIKeyRequest,
  ): Promise<APIKey & { key: string }> => {
    const response = await api.post(`/api/keys`, data);
    return response.data;
  },

  revoke: async (keyId: number): Promise<void> => {
    await api.post(`/api/keys/${keyId}/revoke`, {});
  },

  delete: async (keyId: number): Promise<void> => {
    await api.delete(`/api/keys/${keyId}`);
  },

  getUsageStats: async (keyId: number): Promise<any> => {
    const response = await api.get(`/api/keys/${keyId}/stats`);
    return response.data;
  },
};
