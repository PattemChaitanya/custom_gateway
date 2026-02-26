import api from "./api";

export interface Secret {
  id: number;
  name: string;
  key: string; // Alias for name
  description?: string;
  tags?: string[];
  created_at: string;
  updated_at?: string;
  encrypted_value?: string;
  value?: string; // Only for decrypted secrets
}

export interface CreateSecretRequest {
  name?: string;
  key?: string; // Alias for name
  value: string;
  description?: string;
  tags?: string[];
}

export const secretsService = {
  list: async (tags?: string): Promise<Secret[]> => {
    const response = await api.get(`/api/secrets`, {
      params: { tags },
    });
    return response.data;
  },

  create: async (data: CreateSecretRequest): Promise<Secret> => {
    const response = await api.post(`/api/secrets`, data);
    return response.data;
  },

  get: async (name: string, decrypt: boolean = false): Promise<Secret> => {
    const response = await api.get(`/api/secrets/${name}`, {
      params: { decrypt },
    });
    return response.data;
  },

  update: async (
    name: string,
    value: string,
    description?: string,
  ): Promise<Secret> => {
    const response = await api.put(`/api/secrets/${name}`, {
      value,
      description,
    });
    return response.data;
  },

  delete: async (name: string): Promise<void> => {
    await api.delete(`/api/secrets/${name}`);
  },

  rotate: async (name: string, newValue: string): Promise<Secret> => {
    const response = await api.post(`/api/secrets/${name}/rotate`, {
      value: newValue,
    });
    return response.data;
  },
};
