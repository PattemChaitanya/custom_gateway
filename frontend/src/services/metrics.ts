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

// ── Request-log based metrics (T8) ────────────────────────────────────────────

export interface HourlyBucket {
  bucket: string;
  count: number;
}

export interface StatusBreakdown {
  s2xx: number;
  s4xx: number;
  s5xx: number;
  other: number;
}

export interface SlowestRoute {
  path: string;
  method: string;
  avg_latency_ms: number;
  count: number;
}

export interface RequestLogsSummary {
  requests_over_time: HourlyBucket[];
  status_breakdown: StatusBreakdown;
  slowest_routes: SlowestRoute[];
  total_requests: number;
  avg_latency_ms: number;
  error_rate: number;
}

export async function getRequestLogsSummary(
  hours = 24,
): Promise<RequestLogsSummary> {
  const resp = await api.get("/api/request-logs/summary", {
    params: { hours },
  });
  return resp.data as RequestLogsSummary;
}
