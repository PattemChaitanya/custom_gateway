import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
    const token = localStorage.getItem("token");
    const params = api_id ? { api_id } : {};

    const response = await axios.get(`${API_URL}/api/connectors`, {
      params,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  },

  async get(id: number): Promise<Connector> {
    const token = localStorage.getItem("token");

    const response = await axios.get(`${API_URL}/api/connectors/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  },

  async create(data: CreateConnectorRequest): Promise<Connector> {
    const token = localStorage.getItem("token");

    const response = await axios.post(`${API_URL}/api/connectors`, data, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    return response.data;
  },

  async update(id: number, data: UpdateConnectorRequest): Promise<Connector> {
    const token = localStorage.getItem("token");

    const response = await axios.put(`${API_URL}/api/connectors/${id}`, data, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    return response.data;
  },

  async delete(id: number): Promise<void> {
    const token = localStorage.getItem("token");

    await axios.delete(`${API_URL}/api/connectors/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  async test(id: number): Promise<ConnectorTestResult> {
    const token = localStorage.getItem("token");

    const response = await axios.post(
      `${API_URL}/api/connectors/${id}/test`,
      {},
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    return response.data;
  },
};

export default connectorsService;
