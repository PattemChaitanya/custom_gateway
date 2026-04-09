import { useCallback, useEffect, useRef, useState } from "react";
import { getMetricsSummary, getRequestLogsSummary } from "../services/metrics";
import type { MetricsSummary, RequestLogsSummary } from "../services/metrics";
import {
  getAccountUsage,
  getAccountInstance,
  type AccountUsage,
  type GatewayInstance,
} from "../services/accounts";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import {
  Typography,
  Button,
  Box,
  Grid,
  Card,
  CardContent,
  Chip,
  Divider,
  IconButton,
  LinearProgress,
  Tooltip,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import PageWrapper from "../components/PageWrapper";

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {label}
        </Typography>
        <Typography variant="h5" fontWeight={700}>
          {value}
        </Typography>
        {sub && (
          <Typography variant="caption" color="text.secondary">
            {sub}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

function StatusBar({
  distribution,
  total,
}: {
  distribution: Record<number, number>;
  total: number;
}) {
  const groups: { label: string; codes: number[]; color: string }[] = [
    { label: "2xx", codes: [200, 201, 202, 204], color: "#4caf50" },
    { label: "3xx", codes: [301, 302, 304], color: "#2196f3" },
    { label: "4xx", codes: [400, 401, 403, 404, 422, 429], color: "#ff9800" },
    { label: "5xx", codes: [500, 502, 503], color: "#f44336" },
  ];

  const grouped = groups.map((g) => {
    const count = g.codes.reduce((acc, c) => acc + (distribution[c] ?? 0), 0);
    return { ...g, count };
  });

  // Catch codes not in any group
  const knownCodes = new Set(groups.flatMap((g) => g.codes));
  const otherCount = Object.entries(distribution).reduce(
    (acc, [code, cnt]) => (!knownCodes.has(Number(code)) ? acc + cnt : acc),
    0,
  );
  if (otherCount > 0)
    grouped.push({
      label: "other",
      codes: [],
      color: "#9e9e9e",
      count: otherCount,
    });

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          height: 16,
          borderRadius: 1,
          overflow: "hidden",
          mb: 1,
        }}
      >
        {grouped.map((g) => (
          <Box
            key={g.label}
            sx={{
              width: `${((g.count / Math.max(total, 1)) * 100).toFixed(1)}%`,
              backgroundColor: g.color,
            }}
            title={`${g.label}: ${g.count}`}
          />
        ))}
      </Box>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        {grouped.map((g) => (
          <Box
            key={g.label}
            sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
          >
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                backgroundColor: g.color,
              }}
            />
            <Typography variant="caption">
              {g.label} ({g.count})
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

const PLAN_COLORS: Record<string, "default" | "primary" | "secondary"> = {
  free: "default",
  pro: "primary",
  enterprise: "secondary",
};

// ── Instance status colours ───────────────────────────────────────────────────
const INSTANCE_STATUS_COLOR: Record<
  GatewayInstance["status"],
  "default" | "success" | "warning" | "error" | "info"
> = {
  running: "success",
  provisioning: "info",
  stopped: "default",
  expired: "error",
  error: "error",
};

function formatCountdown(seconds: number): string {
  if (seconds <= 0) return "Expired";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m remaining`;
  if (m > 0) return `${m}m ${s}s remaining`;
  return `${s}s remaining`;
}

function InstancePanel({ accountId }: { accountId: number }) {
  const [instance, setInstance] = useState<GatewayInstance | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchInstance = useCallback(() => {
    getAccountInstance(accountId)
      .then((data) => {
        setInstance(data);
        setCountdown(Math.max(0, data.expires_in_seconds));
      })
      .catch(() => setInstance(null));
  }, [accountId]);

  // Poll instance status every 10s
  useEffect(() => {
    fetchInstance();
    const poll = setInterval(fetchInstance, 10_000);
    return () => clearInterval(poll);
  }, [fetchInstance]);

  // Live countdown tick every second
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (!instance || instance.status !== "running") return;
    timerRef.current = setInterval(() => {
      setCountdown((c) => Math.max(0, c - 1));
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [instance?.status]);

  const handleCopy = () => {
    if (!instance) return;
    navigator.clipboard.writeText(instance.gateway_url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!instance) return null;

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
          <Typography variant="subtitle2">Gateway Instance</Typography>
          <Chip
            label={instance.status}
            size="small"
            color={INSTANCE_STATUS_COLOR[instance.status]}
          />
        </Box>

        {/* Gateway URL */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
          <Typography
            variant="body2"
            sx={{ fontFamily: "monospace", wordBreak: "break-all" }}
          >
            {instance.gateway_url}
          </Typography>
          <Tooltip title={copied ? "Copied!" : "Copy URL"}>
            <IconButton size="small" onClick={handleCopy}>
              <ContentCopyIcon fontSize="inherit" />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Countdown */}
        <Typography
          variant="caption"
          color={countdown < 3600 ? "error" : "text.secondary"}
        >
          {formatCountdown(countdown)}
        </Typography>

        {/* Expiry progress bar */}
        {instance.status === "running" && (
          <LinearProgress
            variant="determinate"
            value={Math.max(
              0,
              100 - (countdown / (48 * 3600)) * 100,
            )}
            color={countdown < 3600 ? "error" : countdown < 7200 ? "warning" : "primary"}
            sx={{ mt: 1, borderRadius: 1, height: 4 }}
          />
        )}
      </CardContent>
    </Card>
  );
}

// ── Live metrics strip (polls every 10s) ─────────────────────────────────────

function LiveMetricsStrip({ accountId }: { accountId?: number }) {
  const [live, setLive] = useState<RequestLogsSummary | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchLive = useCallback(() => {
    getRequestLogsSummary(1) // last 1 hour
      .then((data) => {
        setLive(data);
        setLastUpdated(new Date());
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchLive();
    const poll = setInterval(fetchLive, 10_000);
    return () => clearInterval(poll);
  }, [fetchLive, accountId]);

  // req/min = total requests in last 60 min / 60
  const reqPerMin = live ? (live.total_requests / 60).toFixed(1) : "—";
  const errorRate = live ? `${live.error_rate}%` : "—";
  const avgLatency = live ? `${live.avg_latency_ms} ms` : "—";

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <Typography variant="subtitle2">Live Traffic</Typography>
          <Chip label="1h window" size="small" variant="outlined" />
          {lastUpdated && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </Typography>
          )}
        </Box>
        <Grid container spacing={2}>
          <Grid item xs={4}>
            <Typography variant="caption" color="text.secondary">
              Req / min
            </Typography>
            <Typography variant="h6" fontWeight={700}>
              {reqPerMin}
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="caption" color="text.secondary">
              Error rate
            </Typography>
            <Typography
              variant="h6"
              fontWeight={700}
              color={
                live && live.error_rate > 5 ? "error.main" : "success.main"
              }
            >
              {errorRate}
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="caption" color="text.secondary">
              Avg latency
            </Typography>
            <Typography
              variant="h6"
              fontWeight={700}
              color={
                live && live.avg_latency_ms > 500
                  ? "error.main"
                  : live && live.avg_latency_ms > 200
                  ? "warning.main"
                  : "success.main"
              }
            >
              {avgLatency}
            </Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const profile = useAuthStore((s) => s.profile);
  const navigate = useNavigate();
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [usage, setUsage] = useState<AccountUsage | null>(null);

  useEffect(() => {
    getMetricsSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoadingMetrics(false));
  }, []);

  useEffect(() => {
    if (profile?.account_id) {
      getAccountUsage(profile.account_id)
        .then(setUsage)
        .catch(() => setUsage(null));
    }
  }, [profile?.account_id]);

  return (
    <PageWrapper maxWidth="lg">
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>
          Dashboard
        </Typography>
        {profile && (
          <Typography variant="body2" color="text.secondary">
            Signed in as {profile.email}
          </Typography>
        )}
      </Box>

      {/* Navigation */}
      <Box sx={{ display: "flex", gap: 1.5, mb: 4, flexWrap: "wrap" }}>
        <Button variant="contained" onClick={() => navigate("/apis")}>
          Manage APIs
        </Button>
        <Button variant="outlined" onClick={() => navigate("/mini-cloud")}>
          Control Plane
        </Button>
        <Button variant="outlined" onClick={() => navigate("/audit-logs")}>
          Audit Logs
        </Button>
        <Button variant="outlined" onClick={() => navigate("/secrets")}>
          Secrets
        </Button>
      </Box>

      {/* Gateway instance status + countdown */}
      {profile?.account_id && (
        <InstancePanel accountId={profile.account_id} />
      )}

      {/* Live metrics — req/min, error rate, avg latency — auto-polls 10s */}
      <LiveMetricsStrip accountId={profile?.account_id} />

      {/* Account quota card */}
      {usage && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
              <Typography variant="subtitle2">Account Quota</Typography>
              <Chip
                label={usage.plan}
                size="small"
                color={PLAN_COLORS[usage.plan] ?? "default"}
              />
              <Typography variant="caption" color="text.secondary">
                {usage.slug}
              </Typography>
            </Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
              <Typography variant="body2">
                {usage.used_today.toLocaleString()} requests today
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {usage.daily_quota
                  ? `${usage.daily_quota.toLocaleString()} / day`
                  : "Unlimited"}
              </Typography>
            </Box>
            {usage.daily_quota ? (
              <Tooltip
                title={`${usage.remaining?.toLocaleString() ?? 0} remaining`}
              >
                <LinearProgress
                  variant="determinate"
                  value={Math.min(
                    100,
                    (usage.used_today / usage.daily_quota) * 100,
                  )}
                  color={
                    usage.used_today / usage.daily_quota >= 0.9
                      ? "error"
                      : usage.used_today / usage.daily_quota >= 0.7
                        ? "warning"
                        : "primary"
                  }
                  sx={{ borderRadius: 1, height: 6 }}
                />
              </Tooltip>
            ) : (
              <LinearProgress
                variant="determinate"
                value={0}
                sx={{ borderRadius: 1, height: 6 }}
              />
            )}
          </CardContent>
        </Card>
      )}

      <Divider sx={{ mb: 3 }} />

      {/* Metrics — last 7 days */}
      <Typography variant="h6" gutterBottom>
        Gateway Traffic (last 7 days)
      </Typography>

      {loadingMetrics ? (
        <LinearProgress sx={{ borderRadius: 1, mb: 2 }} />
      ) : !summary ? (
        <Typography variant="body2" color="text.secondary">
          Metrics unavailable — start proxying requests through{" "}
          <code>GET /gw/&#123;api_id&#125;/&#123;path&#125;</code> to populate
          data.
        </Typography>
      ) : (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                label="Total Requests"
                value={summary.total_requests.toLocaleString()}
                sub="7-day window"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                label="Avg Latency"
                value={`${summary.average_latency_ms} ms`}
                sub="across all endpoints"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                label="Errors"
                value={summary.error_count.toLocaleString()}
                sub={`${summary.error_rate}% error rate`}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                label="Success Rate"
                value={`${(100 - summary.error_rate).toFixed(1)}%`}
                sub="non-4xx/5xx responses"
              />
            </Grid>
          </Grid>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Response Status Distribution
              </Typography>
              <StatusBar
                distribution={summary.status_distribution}
                total={summary.total_requests}
              />
            </CardContent>
          </Card>
        </>
      )}
    </PageWrapper>
  );
}
