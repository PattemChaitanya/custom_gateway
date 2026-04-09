import React, { useState } from "react";
import {
  Box,
  Container,
  Typography,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Stack,
  MenuItem,
  Grid,
  Paper,
  Button,
  TextField,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Speed as SpeedIcon,
  ErrorOutline as ErrorIcon,
  CheckCircleOutline as OkIcon,
} from "@mui/icons-material";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useQueryCache } from "../hooks/useQueryCache";
import { getRequestLogsSummary } from "../services/metrics";
import type { RequestLogsSummary } from "../services/metrics";
import { StatCardsSkeleton, TableSkeleton } from "../components/Skeletons";

const HOUR_OPTIONS = [
  { label: "Last 6 hours", value: 6 },
  { label: "Last 24 hours", value: 24 },
  { label: "Last 48 hours", value: 48 },
  { label: "Last 7 days", value: 168 },
];

function formatBucket(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:00`;
  } catch {
    return iso;
  }
}

const METHOD_COLORS: Record<string, string> = {
  GET: "#2196f3",
  POST: "#4caf50",
  PUT: "#ff9800",
  PATCH: "#9c27b0",
  DELETE: "#f44336",
};

export const Metrics: React.FC = () => {
  const [hours, setHours] = useState(24);

  const {
    data: summary,
    loading,
    error,
    refetch,
  } = useQueryCache<RequestLogsSummary>(
    `request-logs-summary-${hours}`,
    () => getRequestLogsSummary(hours),
  );

  // Prepare chart data
  const lineData =
    summary?.requests_over_time.map((b) => ({
      time: formatBucket(b.bucket),
      requests: b.count,
    })) ?? [];

  const barData = summary
    ? [
        { name: "2xx", count: summary.status_breakdown.s2xx, fill: "#4caf50" },
        { name: "4xx", count: summary.status_breakdown.s4xx, fill: "#ff9800" },
        { name: "5xx", count: summary.status_breakdown.s5xx, fill: "#f44336" },
        { name: "Other", count: summary.status_breakdown.other, fill: "#9e9e9e" },
      ]
    : [];

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="h4" component="h1" fontWeight={700}>
          Metrics
        </Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          <TextField
            select
            size="small"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            sx={{ minWidth: 160 }}
          >
            {HOUR_OPTIONS.map((o) => (
              <MenuItem key={o.value} value={o.value}>
                {o.label}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={refetch}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
      </Stack>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Request traffic, status distribution and latency from gateway logs.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Stat cards */}
      {loading ? (
        <StatCardsSkeleton count={4} />
      ) : summary ? (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Total Requests
                  </Typography>
                  <Typography variant="h4" fontWeight={700}>
                    {summary.total_requests.toLocaleString()}
                  </Typography>
                </Box>
                <TrendingUpIcon color="primary" />
              </Stack>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Avg Latency
                  </Typography>
                  <Typography variant="h4" fontWeight={700}>
                    {summary.avg_latency_ms} ms
                  </Typography>
                </Box>
                <SpeedIcon color="info" />
              </Stack>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Error Rate
                  </Typography>
                  <Typography
                    variant="h4"
                    fontWeight={700}
                    color={summary.error_rate > 5 ? "error.main" : "success.main"}
                  >
                    {summary.error_rate}%
                  </Typography>
                </Box>
                {summary.error_rate > 5 ? (
                  <ErrorIcon color="error" />
                ) : (
                  <OkIcon color="success" />
                )}
              </Stack>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Success (2xx)
                  </Typography>
                  <Typography variant="h4" fontWeight={700} color="success.main">
                    {summary.status_breakdown.s2xx.toLocaleString()}
                  </Typography>
                </Box>
                <OkIcon color="success" />
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      ) : null}

      {/* Charts row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Line chart — requests over time */}
        <Grid item xs={12} md={8}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Requests Over Time
            </Typography>
            {loading ? (
              <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Typography variant="body2" color="text.secondary">Loading…</Typography>
              </Box>
            ) : lineData.length === 0 ? (
              <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Typography variant="body2" color="text.secondary">No data for selected period.</Typography>
              </Box>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={lineData} margin={{ top: 5, right: 16, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.2)" />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="requests"
                    stroke="#2196f3"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Grid>

        {/* Bar chart — status breakdown */}
        <Grid item xs={12} md={4}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Status Breakdown
            </Typography>
            {loading ? (
              <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Typography variant="body2" color="text.secondary">Loading…</Typography>
              </Box>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={barData} margin={{ top: 5, right: 16, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.2)" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {barData.map((entry, index) => (
                      <rect key={index} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Grid>
      </Grid>

      {/* Top-5 slowest routes */}
      <Card>
        <Box sx={{ p: 2, pb: 1 }}>
          <Typography variant="h6">Top 5 Slowest Routes</Typography>
        </Box>
        {loading ? (
          <TableSkeleton columns={4} rows={5} />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Method</TableCell>
                  <TableCell>Path</TableCell>
                  <TableCell align="right">Avg Latency (ms)</TableCell>
                  <TableCell align="right">Requests</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {!summary || summary.slowest_routes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No route data available for selected period.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  summary.slowest_routes.map((route, i) => (
                    <TableRow key={i} hover>
                      <TableCell>
                        <Chip
                          label={route.method}
                          size="small"
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.7rem",
                            bgcolor: METHOD_COLORS[route.method] ?? "#9e9e9e",
                            color: "#fff",
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {route.path}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          color={
                            route.avg_latency_ms > 500
                              ? "error.main"
                              : route.avg_latency_ms > 200
                              ? "warning.main"
                              : "success.main"
                          }
                        >
                          {route.avg_latency_ms.toFixed(1)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" color="text.secondary">
                          {route.count.toLocaleString()}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
    </Container>
  );
};
