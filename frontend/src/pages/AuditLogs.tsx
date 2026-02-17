import React, { useState, useEffect } from "react";
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
  TextField,
  MenuItem,
  Grid,
  Paper,
  Button,
  TablePagination,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { auditLogsService } from "../services/auditLogs";
import type {
  AuditLog,
  AuditLogFilters,
  AuditLogStats,
} from "../services/auditLogs";

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const [filters, setFilters] = useState<AuditLogFilters>({
    action: "",
    status: "",
    start_date: "",
    end_date: "",
    limit: 100,
  });

  useEffect(() => {
    loadLogs();
    loadStats();
  }, [filters]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await auditLogsService.list(filters);
      setLogs(data);
      setPage(0);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await auditLogsService.getStatistics();
      setStats(data);
    } catch (err: any) {
      console.error("Failed to load statistics:", err);
    }
  };

  const handleFilterChange = (key: keyof AuditLogFilters, value: any) => {
    setFilters({ ...filters, [key]: value });
  };

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "success":
        return <SuccessIcon color="success" fontSize="small" />;
      case "failure":
      case "error":
        return <ErrorIcon color="error" fontSize="small" />;
      default:
        return <WarningIcon color="warning" fontSize="small" />;
    }
  };

  const getStatusColor = (
    status: string,
  ): "success" | "error" | "warning" | "default" => {
    switch (status.toLowerCase()) {
      case "success":
        return "success";
      case "failure":
      case "error":
        return "error";
      default:
        return "warning";
    }
  };

  const displayedLogs = logs.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage,
  );

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h4" component="h1" fontWeight={700}>
            Audit Logs
          </Typography>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadLogs}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          View and monitor system audit logs. Logs are retained for 30 days.
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      {stats && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" color="primary" gutterBottom>
                Total Events
              </Typography>
              <Typography variant="h3" fontWeight={700}>
                {stats.total_logs.toLocaleString()}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" color="primary" gutterBottom>
                Event Types
              </Typography>
              <Typography variant="h3" fontWeight={700}>
                {Object.keys(stats.logs_by_type).length}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" color="primary" gutterBottom>
                Active Users
              </Typography>
              <Typography variant="h3" fontWeight={700}>
                {Object.keys(stats.logs_by_user).length}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Card sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Filters
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              fullWidth
              label="Action"
              value={filters.action}
              onChange={(e) => handleFilterChange("action", e.target.value)}
              size="small"
            >
              <MenuItem value="">All Actions</MenuItem>
              <MenuItem value="LOGIN_SUCCESS">Login Success</MenuItem>
              <MenuItem value="LOGIN_FAILURE">Login Failure</MenuItem>
              <MenuItem value="API_CREATE">API Create</MenuItem>
              <MenuItem value="API_UPDATE">API Update</MenuItem>
              <MenuItem value="API_DELETE">API Delete</MenuItem>
              <MenuItem value="KEY_GENERATE">Key Generate</MenuItem>
              <MenuItem value="KEY_REVOKE">Key Revoke</MenuItem>
              <MenuItem value="SECRET_CREATE">Secret Create</MenuItem>
              <MenuItem value="SECRET_UPDATE">Secret Update</MenuItem>
              <MenuItem value="SECRET_DELETE">Secret Delete</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              fullWidth
              label="Status"
              value={filters.status}
              onChange={(e) => handleFilterChange("status", e.target.value)}
              size="small"
            >
              <MenuItem value="">All Statuses</MenuItem>
              <MenuItem value="SUCCESS">Success</MenuItem>
              <MenuItem value="FAILURE">Failure</MenuItem>
              <MenuItem value="ERROR">Error</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Start Date"
              type="datetime-local"
              value={filters.start_date}
              onChange={(e) => handleFilterChange("start_date", e.target.value)}
              size="small"
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="End Date"
              type="datetime-local"
              value={filters.end_date}
              onChange={(e) => handleFilterChange("end_date", e.target.value)}
              size="small"
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
        </Grid>
      </Card>

      {/* Logs Table */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>User ID</TableCell>
                <TableCell>Resource</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {displayedLogs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No audit logs found matching the current filters.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                displayedLogs.map((log) => (
                  <TableRow key={log.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontSize: "0.75rem" }}>
                        {formatDate(log.timestamp)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.action}
                        size="small"
                        sx={{ fontFamily: "monospace", fontSize: "0.7rem" }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {log.user_id || "N/A"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {log.resource_type && log.resource_id
                          ? `${log.resource_type}:${log.resource_id}`
                          : "N/A"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        fontFamily="monospace"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {log.ip_address || "N/A"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        {getStatusIcon(log.status)}
                        <Chip
                          label={log.status}
                          color={getStatusColor(log.status)}
                          size="small"
                        />
                      </Stack>
                    </TableCell>
                    <TableCell>
                      {log.error_message ? (
                        <Typography
                          variant="body2"
                          color="error"
                          sx={{ fontSize: "0.75rem" }}
                        >
                          {log.error_message}
                        </Typography>
                      ) : log.metadata_json ? (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ fontSize: "0.75rem" }}
                        >
                          {Object.keys(log.metadata_json).length} metadata
                          fields
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          -
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={logs.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Card>

      {/* Event Type Breakdown */}
      {stats && Object.keys(stats.logs_by_type).length > 0 && (
        <Card sx={{ mt: 3, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Event Type Breakdown
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(stats.logs_by_type)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => (
                <Grid item xs={12} sm={6} md={4} key={type}>
                  <Paper sx={{ p: 2, bgcolor: "action.hover" }}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Typography variant="body2" fontWeight={500}>
                        {type}
                      </Typography>
                      <Chip label={count} size="small" color="primary" />
                    </Stack>
                  </Paper>
                </Grid>
              ))}
          </Grid>
        </Card>
      )}
    </Container>
  );
};
