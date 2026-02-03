import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface AuditLog {
  id: number;
  timestamp: string;
  user_id?: number;
  action: string;
  resource_type?: string;
  resource_id?: string;
  ip_address?: string;
  user_agent?: string;
  metadata_json?: Record<string, any>;
  status: string;
  error_message?: string;
}

export interface AuditLogFilters {
  user_id?: number;
  action?: string;
  start_date?: string;
  end_date?: string;
  status?: string;
  limit?: number;
}

export interface AuditLogStats {
  total_logs: number;
  logs_by_type: Record<string, number>;
  logs_by_user: Record<number, number>;
}

export const auditLogsService = {
  list: async (filters?: AuditLogFilters): Promise<AuditLog[]> => {
    const response = await axios.get(`${API_URL}/api/audit-logs`, {
      params: filters,
      withCredentials: true,
    });
    return response.data;
  },

  getStatistics: async (): Promise<AuditLogStats> => {
    const response = await axios.get(`${API_URL}/api/audit-logs/statistics`, {
      withCredentials: true,
    });
    return response.data;
  },

  getUserActivity: async (
    userId: number,
    days: number = 30,
  ): Promise<AuditLog[]> => {
    const response = await axios.get(
      `${API_URL}/api/audit-logs/user/${userId}`,
      {
        params: { days },
        withCredentials: true,
      },
    );
    return response.data;
  },

  getFailedAttempts: async (hours: number = 24): Promise<AuditLog[]> => {
    const response = await axios.get(`${API_URL}/api/audit-logs/failed`, {
      params: { hours },
      withCredentials: true,
    });
    return response.data;
  },
};
