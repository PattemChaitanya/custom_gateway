import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
    const response = await axios.get(`${API_URL}/api/secrets`, {
      params: { tags },
      withCredentials: true,
    });
    return response.data;
  },

  create: async (data: CreateSecretRequest): Promise<Secret> => {
    const response = await axios.post(`${API_URL}/api/secrets`, data, {
      withCredentials: true,
    });
    return response.data;
  },

  get: async (name: string, decrypt: boolean = false): Promise<Secret> => {
    const response = await axios.get(`${API_URL}/api/secrets/${name}`, {
      params: { decrypt },
      withCredentials: true,
    });
    return response.data;
  },

  update: async (
    name: string,
    value: string,
    description?: string,
  ): Promise<Secret> => {
    const response = await axios.put(
      `${API_URL}/api/secrets/${name}`,
      { value, description },
      { withCredentials: true },
    );
    return response.data;
  },

  delete: async (name: string): Promise<void> => {
    await axios.delete(`${API_URL}/api/secrets/${name}`, {
      withCredentials: true,
    });
  },

  rotate: async (name: string, newValue: string): Promise<Secret> => {
    const response = await axios.post(
      `${API_URL}/api/secrets/${name}/rotate`,
      { value: newValue },
      { withCredentials: true },
    );
    return response.data;
  },
};
