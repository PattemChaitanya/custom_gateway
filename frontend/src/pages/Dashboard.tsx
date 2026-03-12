import { useEffect, useState } from "react";
import { getMetricsSummary } from "../services/metrics";
import type { MetricsSummary } from "../services/metrics";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import {
  Typography,
  Button,
  Box,
  Grid,
  Card,
  CardContent,
  Divider,
  LinearProgress,
} from "@mui/material";
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

export default function Dashboard() {
  const profile = useAuthStore((s) => s.profile);
  const navigate = useNavigate();
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  useEffect(() => {
    getMetricsSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoadingMetrics(false));
  }, []);

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
