import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  IconButton,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  PlayArrow as TickIcon,
  Save as SnapshotIcon,
  RestorePage as RestoreIcon,
  DeleteForever as ResetIcon,
  CloudUpload as BurstIcon,
  BugReport as FailureIcon,
  LinkOutlined as LinkIcon,
  LinkOff as UnlinkIcon,
  ManageSearch as ResolveIcon,
} from "@mui/icons-material";
import PageWrapper from "../components/PageWrapper";
import * as mc from "../services/miniCloud";
import { listAPIs, getAPI } from "../services/apis";
import type { APIItem } from "../services/apis";
import type {
  AutoscalerDecision,
  ControlLoopStatus,
  Job,
  PolicyConfig,
  ServiceInstance,
} from "../services/miniCloud";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function StatusChip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <Chip
      label={label}
      size="small"
      color={ok ? "success" : "error"}
      sx={{ fontWeight: 600 }}
    />
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <Box
      component="pre"
      sx={{
        bgcolor: "action.hover",
        p: 1.5,
        borderRadius: 1,
        fontSize: 12,
        overflowX: "auto",
        maxHeight: 300,
        m: 0,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </Box>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="subtitle1" fontWeight={700} mb={1}>
      {children}
    </Typography>
  );
}

// ---------------------------------------------------------------------------
// Tab 1: Control Loop Overview
// ---------------------------------------------------------------------------

function ControlLoopTab() {
  const [status, setStatus] = useState<ControlLoopStatus | null>(null);
  const [tickResult, setTickResult] = useState<mc.ControlLoopTickResult | null>(
    null,
  );
  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await mc.getControlLoopStatus());
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadStatus();
    const id = setInterval(loadStatus, 5000);
    return () => clearInterval(id);
  }, [loadStatus]);

  const action = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    setMsg(null);
    try {
      const result = await fn();
      setMsg({ type: "success", text: `${label} OK` });
      if (label === "Tick") setTickResult(result as mc.ControlLoopTickResult);
      await loadStatus();
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? label + " failed",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {msg && <Alert severity={msg.type}>{msg.text}</Alert>}

      {/* Status cards */}
      <Grid container spacing={2}>
        {[
          { label: "Queue Depth", value: status?.queue_depth ?? "—" },
          {
            label: "Autoscaler Replicas",
            value: status?.autoscaler_replicas ?? "—",
          },
          {
            label: "Simulated Latency p95 (ms)",
            value: status?.simulated_latency_p95_ms ?? "—",
          },
        ].map(({ label, value }) => (
          <Grid item xs={12} sm={4} key={label}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  {label}
                </Typography>
                <Typography variant="h4" fontWeight={700}>
                  {String(value)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Action buttons */}
      <Stack direction="row" spacing={1} flexWrap="wrap">
        <Button
          variant="contained"
          startIcon={<TickIcon />}
          onClick={() => action("Tick", mc.tickControlLoop)}
          disabled={busy}
        >
          Tick
        </Button>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadStatus}
          disabled={busy}
        >
          Refresh Status
        </Button>
        <Button
          variant="outlined"
          startIcon={<SnapshotIcon />}
          onClick={() => action("Snapshot", () => mc.snapshotState())}
          disabled={busy}
        >
          Snapshot
        </Button>
        <Button
          variant="outlined"
          startIcon={<RestoreIcon />}
          onClick={() => action("Restore", () => mc.restoreState())}
          disabled={busy}
        >
          Restore
        </Button>
        <Tooltip title="Wipes all in-memory state — use with care">
          <Button
            variant="outlined"
            color="error"
            startIcon={<ResetIcon />}
            onClick={() => action("Reset", mc.resetState)}
            disabled={busy}
          >
            Reset
          </Button>
        </Tooltip>
      </Stack>

      {tickResult && (
        <>
          <SectionTitle>Last Tick Result</SectionTitle>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    Autoscaler Decision
                  </Typography>
                  <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    mt={0.5}
                  >
                    <StatusChip
                      ok={tickResult.autoscaler.action !== "none"}
                      label={tickResult.autoscaler.action}
                    />
                    <Typography variant="body2">
                      {tickResult.autoscaler.reason}
                    </Typography>
                    <Chip
                      size="small"
                      label={`→ ${tickResult.autoscaler.replicas} replicas`}
                    />
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    Expired Instances
                  </Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {tickResult.expired_instances.length}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Service Registry
// ---------------------------------------------------------------------------

function ServicesTab() {
  const [service, setService] = useState("orders");
  const [instanceId, setInstanceId] = useState("");
  const [url, setUrl] = useState("");
  const [ttl, setTtl] = useState("60");
  const [weight, setWeight] = useState("1");

  const [instances, setInstances] = useState<ServiceInstance[]>([]);
  const [routeResult, setRouteResult] = useState<mc.RouteResult | null>(null);
  const [strategy, setStrategy] = useState("round_robin");

  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const loadInstances = useCallback(async () => {
    if (!service.trim()) return;
    try {
      setInstances(await mc.listInstances(service.trim()));
    } catch {
      setInstances([]);
    }
  }, [service]);

  const withFeedback = async (
    fn: () => Promise<unknown>,
    successMsg?: string,
  ) => {
    setBusy(true);
    setMsg(null);
    try {
      const result = await fn();
      setMsg({ type: "success", text: successMsg ?? "OK" });
      await loadInstances();
      return result;
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? "Failed",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleRegister = () =>
    withFeedback(
      () =>
        mc.registerInstance(service.trim(), {
          instance_id: instanceId.trim(),
          url: url.trim(),
          ttl_seconds: parseInt(ttl, 10),
          weight: parseInt(weight, 10),
        }),
      "Instance registered",
    );

  const handleRoute = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await mc.routeRequest(service.trim(), strategy);
      setRouteResult(r);
      setMsg({ type: "success", text: `Routed to ${r.target.url}` });
    } catch (e: any) {
      setRouteResult(null);
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? "No healthy instance",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      {msg && <Alert severity={msg.type}>{msg.text}</Alert>}

      {/* Register */}
      <Box>
        <SectionTitle>Register Instance</SectionTitle>
        <Grid container spacing={1.5}>
          {[
            { label: "Service", value: service, set: setService },
            { label: "Instance ID", value: instanceId, set: setInstanceId },
            { label: "URL", value: url, set: setUrl },
            { label: "TTL (s)", value: ttl, set: setTtl },
            { label: "Weight", value: weight, set: setWeight },
          ].map(({ label, value, set }) => (
            <Grid item xs={12} sm={label === "URL" ? 4 : 2} key={label}>
              <TextField
                label={label}
                value={value}
                onChange={(e) => set(e.target.value)}
                size="small"
                fullWidth
              />
            </Grid>
          ))}
          <Grid item xs={12} sm={2}>
            <Button
              variant="contained"
              onClick={handleRegister}
              disabled={busy || !service || !instanceId || !url}
              fullWidth
              sx={{ height: 40 }}
            >
              Register
            </Button>
          </Grid>
        </Grid>
      </Box>

      <Divider />

      {/* List + Route */}
      <Box>
        <Stack direction="row" spacing={1} alignItems="center" mb={1}>
          <SectionTitle>Instances for "{service}"</SectionTitle>
          <IconButton size="small" onClick={loadInstances}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Stack>
        <Stack direction="row" spacing={1} mb={1}>
          <TextField
            label="Strategy"
            select
            SelectProps={{ native: true }}
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            size="small"
          >
            {["round_robin", "weighted", "weighted_round_robin"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </TextField>
          <Button variant="outlined" onClick={handleRoute} disabled={busy}>
            Route Request
          </Button>
        </Stack>
        {routeResult && (
          <Alert severity="info" sx={{ mb: 1 }}>
            → <strong>{routeResult.target.url}</strong> (
            {routeResult.target.instance_id})
          </Alert>
        )}
        {instances.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            No instances. Register one or change the service name and refresh.
          </Typography>
        ) : (
          <Stack spacing={1}>
            {instances.map((inst) => (
              <Card key={inst.instance_id} variant="outlined">
                <CardContent sx={{ py: 1, "&:last-child": { pb: 1 } }}>
                  <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    flexWrap="wrap"
                  >
                    <Typography variant="body2" fontWeight={600}>
                      {inst.instance_id}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {inst.url}
                    </Typography>
                    <StatusChip
                      ok={inst.healthy}
                      label={inst.healthy ? "healthy" : "unhealthy"}
                    />
                    <Chip size="small" label={inst.health_status} />
                    <Chip
                      size="small"
                      label={`w=${inst.weight}`}
                      variant="outlined"
                    />
                    <StatusChip
                      ok={!inst.expired}
                      label={inst.expired ? "expired" : "live"}
                    />
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}
      </Box>
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Scheduler
// ---------------------------------------------------------------------------

function SchedulerTab() {
  const [jobType, setJobType] = useState("reconcile");
  const [payloadJson, setPayloadJson] = useState("{}");
  const [maxRetries, setMaxRetries] = useState("3");
  const [workerId, setWorkerId] = useState("worker-1");
  const [leasedJob, setLeasedJob] = useState<Job | null>(null);
  const [dlq, setDlq] = useState<Record<string, unknown>[]>([]);
  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const loadDlq = useCallback(async () => {
    try {
      const r = await mc.getDlq();
      setDlq(r.dlq);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadDlq();
  }, [loadDlq]);

  const withFeedback = async (
    fn: () => Promise<unknown>,
    successMsg: string,
  ) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg({ type: "success", text: successMsg });
      await loadDlq();
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? "Failed",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleEnqueue = () =>
    withFeedback(async () => {
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(payloadJson);
      } catch {
        throw new Error("Invalid JSON payload");
      }
      return mc.enqueueJob(jobType, payload, parseInt(maxRetries, 10));
    }, "Job enqueued");

  const handleLease = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await mc.leaseJob(workerId);
      if (r.job) {
        setLeasedJob(r.job);
        setMsg({ type: "success", text: `Leased job ${r.job.id}` });
      } else {
        setMsg({ type: "info" as any, text: "No jobs available in queue" });
      }
    } catch (e: any) {
      setMsg({ type: "error", text: e?.response?.data?.detail ?? "Failed" });
    } finally {
      setBusy(false);
    }
  };

  const handleAck = () =>
    withFeedback(async () => {
      if (!leasedJob) throw new Error("No leased job");
      await mc.ackJob(leasedJob.id, workerId);
      setLeasedJob(null);
    }, "Job acknowledged");

  const handleFail = () =>
    withFeedback(async () => {
      if (!leasedJob) throw new Error("No leased job");
      await mc.failJob(leasedJob.id, workerId, "manual fail");
      setLeasedJob(null);
    }, "Job failed (backoff/DLQ)");

  return (
    <Stack spacing={3}>
      {msg && <Alert severity={msg.type as any}>{msg.text}</Alert>}

      <Box>
        <SectionTitle>Enqueue Job</SectionTitle>
        <Grid container spacing={1.5}>
          <Grid item xs={12} sm={3}>
            <TextField
              label="Job Type"
              value={jobType}
              onChange={(e) => setJobType(e.target.value)}
              size="small"
              fullWidth
            />
          </Grid>
          <Grid item xs={12} sm={1.5}>
            <TextField
              label="Max Retries"
              value={maxRetries}
              onChange={(e) => setMaxRetries(e.target.value)}
              size="small"
              fullWidth
            />
          </Grid>
          <Grid item xs={12} sm={5}>
            <TextField
              label="Payload (JSON)"
              value={payloadJson}
              onChange={(e) => setPayloadJson(e.target.value)}
              size="small"
              fullWidth
            />
          </Grid>
          <Grid item xs={12} sm={2.5}>
            <Button
              variant="contained"
              onClick={handleEnqueue}
              disabled={busy}
              fullWidth
              sx={{ height: 40 }}
            >
              Enqueue
            </Button>
          </Grid>
        </Grid>
      </Box>

      <Divider />

      <Box>
        <SectionTitle>Lease / Ack / Fail</SectionTitle>
        <Stack direction="row" spacing={1} flexWrap="wrap" mb={1}>
          <TextField
            label="Worker ID"
            value={workerId}
            onChange={(e) => setWorkerId(e.target.value)}
            size="small"
          />
          <Button variant="outlined" onClick={handleLease} disabled={busy}>
            Lease Next
          </Button>
          <Button
            variant="contained"
            onClick={handleAck}
            disabled={busy || !leasedJob}
          >
            Ack
          </Button>
          <Button
            variant="outlined"
            color="warning"
            onClick={handleFail}
            disabled={busy || !leasedJob}
          >
            Fail
          </Button>
        </Stack>
        {leasedJob && (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="caption" color="text.secondary">
                Currently Leased
              </Typography>
              <JsonBlock value={leasedJob} />
            </CardContent>
          </Card>
        )}
      </Box>

      <Divider />

      <Box>
        <Stack direction="row" spacing={1} alignItems="center" mb={1}>
          <SectionTitle>Dead Letter Queue ({dlq.length})</SectionTitle>
          <IconButton size="small" onClick={loadDlq}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Stack>
        {dlq.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            DLQ is empty.
          </Typography>
        ) : (
          <JsonBlock value={dlq} />
        )}
      </Box>
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Tab 4: Autoscaler
// ---------------------------------------------------------------------------

function AutoscalerTab() {
  const [queueDepth, setQueueDepth] = useState("10");
  const [latency, setLatency] = useState("200");
  const [decision, setDecision] = useState<AutoscalerDecision | null>(null);
  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const handleEvaluate = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const d = await mc.evaluateAutoscaler(
        parseInt(queueDepth, 10),
        parseFloat(latency),
      );
      setDecision(d);
      setMsg({
        type: "success",
        text: `Action: ${d.action} → ${d.replicas} replicas (${d.reason})`,
      });
    } catch (e: any) {
      setMsg({ type: "error", text: e?.response?.data?.detail ?? "Failed" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      {msg && <Alert severity={msg.type}>{msg.text}</Alert>}

      <Box>
        <SectionTitle>Evaluate Autoscaler Signal</SectionTitle>
        <Typography variant="body2" color="text.secondary" mb={1.5}>
          Thresholds: scale_up when queue ≥ 25 or latency ≥ 400 ms · scale_down
          when queue ≤ 5 and latency ≤ 120 ms · cooldown 30 s · replicas 1–10
        </Typography>
        <Stack
          direction="row"
          spacing={1.5}
          flexWrap="wrap"
          alignItems="center"
        >
          <TextField
            label="Queue Depth"
            type="number"
            value={queueDepth}
            onChange={(e) => setQueueDepth(e.target.value)}
            size="small"
            sx={{ width: 150 }}
          />
          <TextField
            label="Latency p95 (ms)"
            type="number"
            value={latency}
            onChange={(e) => setLatency(e.target.value)}
            size="small"
            sx={{ width: 170 }}
          />
          <Button variant="contained" onClick={handleEvaluate} disabled={busy}>
            Evaluate
          </Button>
        </Stack>
      </Box>

      {decision && (
        <Grid container spacing={2}>
          {[
            { label: "Action", value: decision.action },
            { label: "Replicas", value: String(decision.replicas) },
            { label: "Reason", value: decision.reason },
          ].map(({ label, value }) => (
            <Grid item xs={12} sm={4} key={label}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {value}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Tab 5: Policies
// ---------------------------------------------------------------------------

function PoliciesTab() {
  const [, setPolicies] = useState<PolicyConfig | null>(null);
  const [editJson, setEditJson] = useState("");
  const [validation, setValidation] = useState<{
    valid: boolean;
    errors: string[];
  } | null>(null);
  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const loadPolicies = useCallback(async () => {
    try {
      const p = await mc.getPolicies();
      setPolicies(p);
      setEditJson(JSON.stringify(p, null, 2));
    } catch (e: any) {
      setMsg({ type: "error", text: "Failed to load policies" });
    }
  }, []);

  useEffect(() => {
    loadPolicies();
  }, [loadPolicies]);

  const handleValidate = async () => {
    setBusy(true);
    setMsg(null);
    setValidation(null);
    try {
      let parsed: object;
      try {
        parsed = JSON.parse(editJson);
      } catch {
        throw new Error("Invalid JSON");
      }
      const v = await mc.validatePolicies(parsed);
      setValidation(v);
      setMsg({
        type: v.valid ? "success" : "error",
        text: v.valid ? "Valid" : `${v.errors.length} error(s)`,
      });
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? "Validation failed",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    setBusy(true);
    setMsg(null);
    try {
      let parsed: object;
      try {
        parsed = JSON.parse(editJson);
      } catch {
        throw new Error("Invalid JSON");
      }
      await mc.updatePolicies(parsed);
      setMsg({ type: "success", text: "Policies hot-reloaded successfully" });
      await loadPolicies();
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? "Save failed",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {msg && <Alert severity={msg.type}>{msg.text}</Alert>}
      {validation && validation.errors.length > 0 && (
        <Alert severity="warning">
          {validation.errors.map((err, i) => (
            <div key={i}>{err}</div>
          ))}
        </Alert>
      )}

      <Stack direction="row" spacing={1}>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadPolicies}
          disabled={busy}
        >
          Reload from Server
        </Button>
        <Button variant="outlined" onClick={handleValidate} disabled={busy}>
          Validate
        </Button>
        <Button variant="contained" onClick={handleSave} disabled={busy}>
          Save & Hot-Reload
        </Button>
      </Stack>

      <TextField
        label="Policy Config (JSON)"
        multiline
        rows={20}
        value={editJson}
        onChange={(e) => setEditJson(e.target.value)}
        fullWidth
        inputProps={{ style: { fontFamily: "monospace", fontSize: 12 } }}
      />
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Tab 6: Failure Injection
// ---------------------------------------------------------------------------

function FailureInjectionTab() {
  const [staleService, setStaleService] = useState("orders");
  const [staleInstance, setStaleInstance] = useState("inst-1");
  const [staleSeconds, setStaleSeconds] = useState("300");

  const [crashJobId, setCrashJobId] = useState("");

  const [slowLatency, setSlowLatency] = useState("500");

  const [burstRps, setBurstRps] = useState("10");
  const [burstDuration, setBurstDuration] = useState("3");

  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<unknown>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setMsg(null);
    setLastResult(null);
    try {
      const result = await fn();
      setLastResult(result);
      setMsg({ type: "success", text: "Failure injected" });
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? "Injection failed",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      {msg && <Alert severity={msg.type}>{msg.text}</Alert>}
      {lastResult !== null && (
        <JsonBlock value={lastResult as Record<string, unknown>} />
      )}

      {/* Stale Heartbeat */}
      <Card variant="outlined">
        <CardContent>
          <SectionTitle>Stale Heartbeat</SectionTitle>
          <Typography variant="body2" color="text.secondary" mb={1.5}>
            Back-dates the instance's last_heartbeat → TTL expiry kicks it out
            of routing.
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap">
            <TextField
              label="Service"
              value={staleService}
              onChange={(e) => setStaleService(e.target.value)}
              size="small"
            />
            <TextField
              label="Instance ID"
              value={staleInstance}
              onChange={(e) => setStaleInstance(e.target.value)}
              size="small"
            />
            <TextField
              label="Seconds Ago"
              type="number"
              value={staleSeconds}
              onChange={(e) => setStaleSeconds(e.target.value)}
              size="small"
              sx={{ width: 140 }}
            />
            <Button
              variant="contained"
              color="warning"
              startIcon={<FailureIcon />}
              onClick={() =>
                run(() =>
                  mc.injectStaleHeartbeat(
                    staleService,
                    staleInstance,
                    parseInt(staleSeconds, 10),
                  ),
                )
              }
              disabled={busy}
            >
              Inject
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Worker Crash */}
      <Card variant="outlined">
        <CardContent>
          <SectionTitle>Worker Crash</SectionTitle>
          <Typography variant="body2" color="text.secondary" mb={1.5}>
            Expires the job's lease immediately so any worker can re-acquire it.
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap">
            <TextField
              label="Job ID"
              value={crashJobId}
              onChange={(e) => setCrashJobId(e.target.value)}
              size="small"
              sx={{ width: 320 }}
            />
            <Button
              variant="contained"
              color="warning"
              startIcon={<FailureIcon />}
              onClick={() => run(() => mc.injectWorkerCrash(crashJobId))}
              disabled={busy || !crashJobId}
            >
              Crash
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Slow Downstream */}
      <Card variant="outlined">
        <CardContent>
          <SectionTitle>Slow Downstream</SectionTitle>
          <Typography variant="body2" color="text.secondary" mb={1.5}>
            Sets simulated_latency_p95_ms — the next control-loop tick will use
            this to evaluate scale-up.
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap">
            <TextField
              label="Latency (ms)"
              type="number"
              value={slowLatency}
              onChange={(e) => setSlowLatency(e.target.value)}
              size="small"
              sx={{ width: 160 }}
            />
            <Button
              variant="contained"
              color="warning"
              startIcon={<FailureIcon />}
              onClick={() =>
                run(() => mc.injectSlowDownstream(parseFloat(slowLatency)))
              }
              disabled={busy}
            >
              Inject
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Burst Traffic */}
      <Card variant="outlined">
        <CardContent>
          <SectionTitle>Burst Traffic</SectionTitle>
          <Typography variant="body2" color="text.secondary" mb={1.5}>
            Enqueues rps × duration_seconds synthetic jobs, simulating a traffic
            spike.
          </Typography>
          <Stack direction="row" spacing={1.5} flexWrap="wrap">
            <TextField
              label="RPS"
              type="number"
              value={burstRps}
              onChange={(e) => setBurstRps(e.target.value)}
              size="small"
              sx={{ width: 120 }}
            />
            <TextField
              label="Duration (s)"
              type="number"
              value={burstDuration}
              onChange={(e) => setBurstDuration(e.target.value)}
              size="small"
              sx={{ width: 140 }}
            />
            <Button
              variant="contained"
              color="warning"
              startIcon={<BurstIcon />}
              onClick={() =>
                run(() =>
                  mc.injectBurstTraffic(
                    parseInt(burstRps, 10),
                    parseInt(burstDuration, 10),
                  ),
                )
              }
              disabled={busy}
            >
              Burst
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Tab 6: Gateway Link (Phase 9)
// ---------------------------------------------------------------------------

function GatewayLinkTab() {
  const [apis, setApis] = useState<APIItem[]>([]);
  const [selectedApiId, setSelectedApiId] = useState("");
  const [serviceName, setServiceName] = useState("");
  const [strategy, setStrategy] = useState("round_robin");
  const [currentLinked, setCurrentLinked] = useState<string | null>(null);
  const [resolveResult, setResolveResult] = useState<{
    service: string;
    strategy: string;
    instance: ServiceInstance;
  } | null>(null);
  const [msg, setMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listAPIs()
      .then(setApis)
      .catch(() => setApis([]));
  }, []);

  useEffect(() => {
    const id = parseInt(selectedApiId, 10);
    const found = apis.find((a) => a.id === id);
    setCurrentLinked(found?.config?.service_name ?? null);
    setResolveResult(null);
  }, [selectedApiId, apis]);

  const refreshApi = async (id: number) => {
    try {
      const updated = await getAPI(id);
      setCurrentLinked(updated?.config?.service_name ?? null);
      setApis((prev) =>
        prev.map((a) => (a.id === id ? { ...a, config: updated.config } : a)),
      );
    } catch {
      // silent
    }
  };

  const run = async (fn: () => Promise<unknown>, successMsg: string) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg({ type: "success", text: successMsg });
      const id = parseInt(selectedApiId, 10);
      if (id) await refreshApi(id);
    } catch (e: any) {
      setMsg({
        type: "error",
        text: e?.response?.data?.detail ?? e?.message ?? "Failed",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleLink = () => {
    const id = parseInt(selectedApiId, 10);
    run(
      () => mc.linkApiToService(serviceName.trim(), id, strategy),
      `API ${id} linked → ${serviceName.trim()}`,
    );
  };

  const handleUnlink = () => {
    const id = parseInt(selectedApiId, 10);
    run(
      () => mc.unlinkApiFromService(currentLinked!, id),
      `API ${id} unlinked from ${currentLinked}`,
    );
  };

  const handleResolve = async () => {
    const svc = serviceName.trim() || currentLinked;
    if (!svc) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await mc.resolveService(svc, strategy);
      setResolveResult(r as any);
    } catch (e: any) {
      setMsg({
        type: "error",
        text:
          e?.response?.data?.detail ??
          `No healthy instance for service "${svc}"`,
      });
      setResolveResult(null);
    } finally {
      setBusy(false);
    }
  };

  const apiId = parseInt(selectedApiId, 10);
  const resolveSvc = serviceName.trim() || currentLinked;

  return (
    <Stack spacing={3}>
      {msg && <Alert severity={msg.type}>{msg.text}</Alert>}

      <Alert severity="info" variant="outlined">
        Link any registered API to a mini-cloud service. After linking, every
        request to <code>/gw/{"<api_id>"}/**</code> selects a healthy instance
        from the ServiceRegistry instead of a static URL — with live routing
        strategy, TTL expiry, and weighted load-balancing.
      </Alert>

      {/* Step 1 – pick an API */}
      <Box>
        <SectionTitle>1 — Select an API</SectionTitle>
        <TextField
          select
          SelectProps={{ native: true }}
          value={selectedApiId}
          onChange={(e) => setSelectedApiId(e.target.value)}
          size="small"
          label="API"
          sx={{ width: 340 }}
        >
          <option value="">— choose —</option>
          {apis.map((a) => (
            <option key={a.id} value={a.id}>
              [{a.id}] {a.name}
              {a.config?.service_name ? ` (→ ${a.config.service_name})` : ""}
            </option>
          ))}
        </TextField>
        {currentLinked && (
          <Alert severity="success" sx={{ mt: 1.5 }}>
            Currently linked to service: <strong>{currentLinked}</strong>
          </Alert>
        )}
      </Box>

      <Divider />

      {/* Step 2 – configure & link */}
      <Box>
        <SectionTitle>2 — Link / Unlink</SectionTitle>
        <Stack
          direction="row"
          spacing={1.5}
          flexWrap="wrap"
          alignItems="center"
        >
          <TextField
            label="Service Name"
            value={serviceName}
            onChange={(e) => setServiceName(e.target.value)}
            placeholder={currentLinked ?? "e.g. orders"}
            size="small"
            sx={{ width: 200 }}
          />
          <TextField
            label="Routing Strategy"
            select
            SelectProps={{ native: true }}
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            size="small"
          >
            {["round_robin", "weighted", "weighted_round_robin"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </TextField>
          <Button
            variant="contained"
            startIcon={<LinkIcon />}
            onClick={handleLink}
            disabled={busy || !apiId || !serviceName.trim()}
          >
            Link
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<UnlinkIcon />}
            onClick={handleUnlink}
            disabled={busy || !apiId || !currentLinked}
          >
            Unlink
          </Button>
        </Stack>
      </Box>

      <Divider />

      {/* Step 3 – resolve preview */}
      <Box>
        <SectionTitle>3 — Resolve Preview</SectionTitle>
        <Typography variant="body2" color="text.secondary" mb={1.5}>
          Preview which instance the gateway would select right now for{" "}
          <strong>{resolveSvc ?? "—"}</strong> with strategy{" "}
          <strong>{strategy}</strong> — no real traffic is sent.
        </Typography>
        <Button
          variant="outlined"
          startIcon={<ResolveIcon />}
          onClick={handleResolve}
          disabled={busy || !resolveSvc}
        >
          Resolve
        </Button>

        {resolveResult && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                mb={0.5}
              >
                Selected instance for &quot;{resolveResult.service}&quot; via{" "}
                {resolveResult.strategy}
              </Typography>
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                flexWrap="wrap"
              >
                <Chip
                  label={resolveResult.instance.instance_id}
                  color="primary"
                  size="small"
                />
                <Typography variant="body2" fontFamily="monospace">
                  {resolveResult.instance.url}
                </Typography>
                <Chip
                  size="small"
                  label={`w=${resolveResult.instance.weight}`}
                  variant="outlined"
                />
                <StatusChip
                  ok={resolveResult.instance.healthy}
                  label={
                    resolveResult.instance.healthy ? "healthy" : "unhealthy"
                  }
                />
                <Chip
                  size="small"
                  label={resolveResult.instance.health_status}
                />
              </Stack>
            </CardContent>
          </Card>
        )}
      </Box>
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const TABS = [
  { label: "Control Loop" },
  { label: "Services" },
  { label: "Scheduler" },
  { label: "Autoscaler" },
  { label: "Policies" },
  { label: "Failure Injection" },
  { label: "Gateway Link" },
];

export default function MiniCloud() {
  const [tab, setTab] = useState(0);

  return (
    <PageWrapper maxWidth="lg">
      <Typography variant="h5" fontWeight={700} mb={0.5}>
        Mini-Cloud Control Plane
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Live control plane dashboard — service registry, scheduler, autoscaler,
        policies, and chaos tooling.
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ borderBottom: 1, borderColor: "divider", mb: 2.5 }}
      >
        {TABS.map((t) => (
          <Tab key={t.label} label={t.label} />
        ))}
      </Tabs>

      {tab === 0 && <ControlLoopTab />}
      {tab === 1 && <ServicesTab />}
      {tab === 2 && <SchedulerTab />}
      {tab === 3 && <AutoscalerTab />}
      {tab === 4 && <PoliciesTab />}
      {tab === 5 && <FailureInjectionTab />}
      {tab === 6 && <GatewayLinkTab />}
    </PageWrapper>
  );
}
