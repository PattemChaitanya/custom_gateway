import api from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ContractData {
  version: string;
  guarantees: Record<string, string>;
  tradeoffs: Record<string, string>;
}

export interface PolicyConfig {
  version: string;
  routes: PolicyRoute[];
  auth: Record<string, AuthPolicy>;
  rate_limits: Record<string, RateLimitPolicy>;
}

export interface PolicyRoute {
  service: string;
  path_prefix?: string;
  strategy: string;
  auth_policy: string;
  rate_limit_policy: string;
}

export interface AuthPolicy {
  name: string;
  mode: string;
  scopes: string[];
}

export interface RateLimitPolicy {
  name: string;
  limit: number;
  window_seconds: number;
}

export interface ServiceInstance {
  service: string;
  instance_id: string;
  url: string;
  weight: number;
  healthy: boolean;
  health_status: string;
  registered_at: number;
  last_heartbeat: number;
  ttl_seconds: number;
  expired: boolean;
  metadata: Record<string, string>;
}

export interface RegisterInstanceRequest {
  instance_id: string;
  url: string;
  ttl_seconds?: number;
  weight?: number;
  metadata?: Record<string, string>;
}

export interface RouteResult {
  request_id: string;
  service: string;
  target: ServiceInstance;
  applied_route_policy: PolicyRoute | null;
}

export interface Job {
  id: string;
  job_type: string;
  payload: Record<string, unknown>;
  attempts: number;
  available_at: number;
  created_at: number;
  lease_owner: string | null;
  lease_expires_at: number | null;
}

export interface AutoscalerDecision {
  replicas: number;
  action: "scale_up" | "scale_down" | "none";
  reason: string;
}

export interface ControlLoopStatus {
  queue_depth: number;
  simulated_latency_p95_ms: number;
  autoscaler_replicas: number;
  last_state: Record<string, unknown>;
}

export interface ControlLoopTickResult {
  expired_instances: string[];
  queue_depth: number;
  simulated_latency_p95_ms: number;
  autoscaler: AutoscalerDecision;
}

// ---------------------------------------------------------------------------
// Contract
// ---------------------------------------------------------------------------

export const getContract = (): Promise<ContractData> =>
  api.get("/mini-cloud/contract").then((r) => r.data);

// ---------------------------------------------------------------------------
// Policies
// ---------------------------------------------------------------------------

export const getPolicies = (): Promise<PolicyConfig> =>
  api.get("/mini-cloud/policies").then((r) => r.data);

export const validatePolicies = (
  config: object,
): Promise<{ valid: boolean; errors: string[] }> =>
  api.post("/mini-cloud/policies/validate", config).then((r) => r.data);

export const updatePolicies = (config: object): Promise<PolicyConfig> =>
  api.put("/mini-cloud/policies", config).then((r) => r.data);

// ---------------------------------------------------------------------------
// Service Registry
// ---------------------------------------------------------------------------

export const registerInstance = (
  service: string,
  payload: RegisterInstanceRequest,
): Promise<ServiceInstance> =>
  api
    .post(`/mini-cloud/services/${service}/instances`, payload)
    .then((r) => r.data);

export const sendHeartbeat = (
  service: string,
  instanceId: string,
  healthy = true,
): Promise<ServiceInstance> =>
  api
    .post(`/mini-cloud/services/${service}/instances/${instanceId}/heartbeat`, {
      healthy,
    })
    .then((r) => r.data);

export const listInstances = (
  service: string,
  healthyOnly = false,
): Promise<ServiceInstance[]> =>
  api
    .get(`/mini-cloud/services/${service}/instances`, {
      params: { healthy_only: healthyOnly },
    })
    .then((r) => r.data);

export const routeRequest = (
  service: string,
  strategy: string,
): Promise<RouteResult> =>
  api
    .post(`/mini-cloud/services/${service}/route`, { strategy })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Scheduler
// ---------------------------------------------------------------------------

export const enqueueJob = (
  jobType: string,
  payload: Record<string, unknown>,
  maxRetries = 3,
): Promise<{ job_id: string }> =>
  api
    .post("/mini-cloud/scheduler/jobs", {
      job_type: jobType,
      payload,
      max_retries: maxRetries,
    })
    .then((r) => r.data);

export const leaseJob = (workerId: string): Promise<{ job: Job | null }> =>
  api
    .post("/mini-cloud/scheduler/jobs/lease", { worker_id: workerId })
    .then((r) => r.data);

export const ackJob = (
  jobId: string,
  workerId: string,
): Promise<{ acked: boolean }> =>
  api
    .post(`/mini-cloud/scheduler/jobs/${jobId}/ack`, { worker_id: workerId })
    .then((r) => r.data);

export const failJob = (
  jobId: string,
  workerId: string,
  reason: string,
): Promise<{ failed: boolean }> =>
  api
    .post(`/mini-cloud/scheduler/jobs/${jobId}/fail`, {
      worker_id: workerId,
      reason,
    })
    .then((r) => r.data);

export const getDlq = (): Promise<{ dlq: Record<string, unknown>[] }> =>
  api.get("/mini-cloud/scheduler/dlq").then((r) => r.data);

// ---------------------------------------------------------------------------
// Autoscaler
// ---------------------------------------------------------------------------

export const evaluateAutoscaler = (
  queueDepth: number,
  latencyP95Ms: number,
): Promise<AutoscalerDecision> =>
  api
    .post("/mini-cloud/autoscaler/evaluate", {
      queue_depth: queueDepth,
      latency_p95_ms: latencyP95Ms,
    })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Failure Injection
// ---------------------------------------------------------------------------

export const injectStaleHeartbeat = (
  service: string,
  instanceId: string,
  secondsAgo = 300,
): Promise<{ status: string; failure: string }> =>
  api
    .post(
      `/mini-cloud/failures/stale-heartbeat/${service}/${instanceId}`,
      null,
      { params: { seconds_ago: secondsAgo } },
    )
    .then((r) => r.data);

export const injectWorkerCrash = (
  jobId: string,
): Promise<{ status: string; failure: string }> =>
  api.post(`/mini-cloud/failures/worker-crash/${jobId}`).then((r) => r.data);

export const injectSlowDownstream = (
  latencyMs: number,
): Promise<{ simulated_latency_ms: number }> =>
  api
    .post("/mini-cloud/failures/slow-downstream", { latency_ms: latencyMs })
    .then((r) => r.data);

export const injectBurstTraffic = (
  rps: number,
  durationSeconds: number,
): Promise<{
  rps: number;
  duration_seconds: number;
  total_requests: number;
  queue_depth_after_enqueue: number;
}> =>
  api
    .post("/mini-cloud/failures/burst-traffic", {
      rps,
      duration_seconds: durationSeconds,
    })
    .then((r) => r.data);

// ---------------------------------------------------------------------------
// Control Loop
// ---------------------------------------------------------------------------

export const tickControlLoop = (): Promise<ControlLoopTickResult> =>
  api.post("/mini-cloud/control-loop/tick").then((r) => r.data);

export const getControlLoopStatus = (): Promise<ControlLoopStatus> =>
  api.get("/mini-cloud/control-loop/status").then((r) => r.data);

export const snapshotState = (
  path?: string,
): Promise<{ path: string; saved_at: number }> =>
  api
    .post("/mini-cloud/control-loop/snapshot", null, {
      params: path ? { path } : {},
    })
    .then((r) => r.data);

export const restoreState = (
  path?: string,
): Promise<{
  restored: boolean;
  path: string;
  services?: number;
  jobs?: number;
  reason?: string;
}> =>
  api
    .post("/mini-cloud/control-loop/restore", null, {
      params: path ? { path } : {},
    })
    .then((r) => r.data);

export const resetState = (): Promise<{ status: string }> =>
  api.post("/mini-cloud/reset").then((r) => r.data);

// ---------------------------------------------------------------------------
// Gateway ↔ Mini-Cloud Link (Phase 9)
// ---------------------------------------------------------------------------

export const resolveService = (
  service: string,
  strategy = "round_robin",
): Promise<{ service: string; instance: ServiceInstance; strategy: string }> =>
  api
    .get(`/mini-cloud/services/${service}/resolve`, { params: { strategy } })
    .then((r) => r.data);

export const linkApiToService = (
  service: string,
  apiId: number,
  routing_strategy = "round_robin",
): Promise<{
  api_id: number;
  service_name: string;
  routing_strategy: string;
}> =>
  api
    .post(`/mini-cloud/services/${service}/link-api/${apiId}`, {
      routing_strategy,
    })
    .then((r) => r.data);

export const unlinkApiFromService = (
  service: string,
  apiId: number,
): Promise<{ api_id: number; unlinked: boolean }> =>
  api
    .delete(`/mini-cloud/services/${service}/link-api/${apiId}`)
    .then((r) => r.data);
