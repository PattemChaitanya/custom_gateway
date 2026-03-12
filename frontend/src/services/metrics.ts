import api from "./api";

export interface MetricsSummary {
  total_requests: number;
  average_latency_ms: number;
  error_count: number;
  error_rate: number; // percentage 0–100
  status_distribution: Record<number, number>;
  start_date: string;
  end_date: string;
}

export async function getMetricsSummary(): Promise<MetricsSummary> {
  const resp = await api.get("/metrics/summary");
  return resp.data as MetricsSummary;
}
