import api from './api';

export interface APIItem {
  id: number;
  name: string;
  version: string;
  description?: string;
  // optional UI fields to carry the API config and metadata
  type?: 'rest' | 'graphql';
  format?: 'resource' | 'json' | 'terraform';
  createdAt?: string;
  updatedAt?: string;
  // stored configuration body (JSON/YAML/terraform) - backend may accept string or object
  config?: any;
}

export async function listAPIs(): Promise<APIItem[]> {
  const resp = await api.get('/apis/');
  return resp.data as APIItem[];
}

export async function createAPI(payload: Partial<APIItem>) {
  const resp = await api.post('/apis/', payload);
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
