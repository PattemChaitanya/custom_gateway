import api from "./api";

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
    const response = await api.get(`/api/audit-logs`, {
      params: filters,
    });
    return response.data;
  },

  getStatistics: async (): Promise<AuditLogStats> => {
    const response = await api.get(`/api/audit-logs/statistics`);
    return response.data;
  },

  getUserActivity: async (
    userId: number,
    days: number = 30,
  ): Promise<AuditLog[]> => {
    const response = await api.get(`/api/audit-logs/user/${userId}`, {
      params: { days },
    });
    return response.data;
  },

  getFailedAttempts: async (hours: number = 24): Promise<AuditLog[]> => {
    const response = await api.get(`/api/audit-logs/failed`, {
      params: { hours },
    });
    return response.data;
  },
};
