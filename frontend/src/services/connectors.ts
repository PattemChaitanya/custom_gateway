import api from "./api";

export interface Connector {
  id: number;
  name: string;
  type: string;
  config: Record<string, any>;
  api_id?: number;
  created_at: string;
  updated_at?: string;
}

export interface CreateConnectorRequest {
  name: string;
  type: string;
  config: Record<string, any>;
  api_id?: number;
}

export interface UpdateConnectorRequest {
  name?: string;
  type?: string;
  config?: Record<string, any>;
  api_id?: number;
}

export interface ConnectorTestResult {
  connector_id: number;
  status: string;
  connected: boolean;
  error?: string;
}

const connectorsService = {
  async list(api_id?: number): Promise<Connector[]> {
    const params = api_id ? { api_id } : {};
    const response = await api.get(`/api/connectors`, { params });
    return response.data;
  },

  async get(id: number): Promise<Connector> {
    const response = await api.get(`/api/connectors/${id}`);
    return response.data;
  },

  async create(data: CreateConnectorRequest): Promise<Connector> {
    const response = await api.post(`/api/connectors`, data);
    return response.data;
  },

  async update(id: number, data: UpdateConnectorRequest): Promise<Connector> {
    const response = await api.put(`/api/connectors/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/api/connectors/${id}`);
  },

  async test(id: number): Promise<ConnectorTestResult> {
    const response = await api.post(`/api/connectors/${id}/test`, {});
    return response.data;
  },
};

export default connectorsService;
