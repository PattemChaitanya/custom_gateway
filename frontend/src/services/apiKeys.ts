import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
    const response = await axios.get(`${API_URL}/api/keys`, {
      params: { environment_id: environmentId },
      withCredentials: true,
    });
    return response.data;
  },

  create: async (
    data: CreateAPIKeyRequest,
  ): Promise<APIKey & { key: string }> => {
    const response = await axios.post(`${API_URL}/api/keys`, data, {
      withCredentials: true,
    });
    return response.data;
  },

  revoke: async (keyId: number): Promise<void> => {
    await axios.post(
      `${API_URL}/api/keys/${keyId}/revoke`,
      {},
      {
        withCredentials: true,
      },
    );
  },

  delete: async (keyId: number): Promise<void> => {
    await axios.delete(`${API_URL}/api/keys/${keyId}`, {
      withCredentials: true,
    });
  },

  getUsageStats: async (keyId: number): Promise<any> => {
    const response = await axios.get(`${API_URL}/api/keys/${keyId}/stats`, {
      withCredentials: true,
    });
    return response.data;
  },
};
