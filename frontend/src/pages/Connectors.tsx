import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  Card,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PlayArrow as TestIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";
import connectorsService from "../services/connectors";
import type {
  Connector,
  CreateConnectorRequest,
  ConnectorTestResult,
} from "../services/connectors";

const CONNECTOR_TYPES = [
  { value: "postgresql", label: "PostgreSQL" },
  { value: "mongodb", label: "MongoDB" },
  { value: "redis", label: "Redis" },
  { value: "kafka", label: "Kafka" },
  { value: "s3", label: "AWS S3" },
  { value: "azure", label: "Azure Storage" },
];

const Connectors: React.FC = () => {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingConnector, setEditingConnector] = useState<Connector | null>(
    null,
  );
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [connectorToDelete, setConnectorToDelete] = useState<number | null>(
    null,
  );
  const [testResults, setTestResults] = useState<
    Record<number, ConnectorTestResult>
  >({});

  // Form state
  const [formData, setFormData] = useState<CreateConnectorRequest>({
    name: "",
    type: "postgresql",
    config: {},
  });
  const [configJson, setConfigJson] = useState("{}");

  useEffect(() => {
    loadConnectors();
  }, []);

  const loadConnectors = async () => {
    try {
      setLoading(true);
      const data = await connectorsService.list();
      setConnectors(data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load connectors");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (connector?: Connector) => {
    if (connector) {
      setEditingConnector(connector);
      setFormData({
        name: connector.name,
        type: connector.type,
        config: connector.config,
        api_id: connector.api_id,
      });
      setConfigJson(JSON.stringify(connector.config, null, 2));
    } else {
      setEditingConnector(null);
      setFormData({
        name: "",
        type: "postgresql",
        config: {},
      });
      setConfigJson("{}");
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingConnector(null);
  };

  const handleSubmit = async () => {
    try {
      // Parse config JSON
      let config;
      try {
        config = JSON.parse(configJson);
      } catch (e) {
        setError("Invalid JSON in configuration");
        return;
      }

      const data = { ...formData, config };

      if (editingConnector) {
        await connectorsService.update(editingConnector.id, data);
        setSuccess("Connector updated successfully");
      } else {
        await connectorsService.create(data);
        setSuccess("Connector created successfully");
      }

      handleCloseDialog();
      loadConnectors();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to save connector");
    }
  };

  const handleDelete = async () => {
    if (!connectorToDelete) return;

    try {
      await connectorsService.delete(connectorToDelete);
      setSuccess("Connector deleted successfully");
      setDeleteDialogOpen(false);
      setConnectorToDelete(null);
      loadConnectors();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete connector");
    }
  };

  const handleTest = async (connectorId: number) => {
    try {
      const result = await connectorsService.test(connectorId);
      setTestResults((prev) => ({ ...prev, [connectorId]: result }));
      setTimeout(() => {
        setTestResults((prev) => {
          const newResults = { ...prev };
          delete newResults[connectorId];
          return newResults;
        });
      }, 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to test connector");
    }
  };

  const getStatusColor = (result?: ConnectorTestResult) => {
    if (!result) return "default";
    if (result.status === "healthy") return "success";
    if (result.status === "unhealthy") return "warning";
    return "error";
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4">Connectors</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Add Connector
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          onClose={() => setSuccess(null)}
        >
          {success}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>API ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {connectors.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="textSecondary">
                        No connectors found
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  connectors.map((connector) => {
                    const testResult = testResults[connector.id];
                    return (
                      <TableRow key={connector.id}>
                        <TableCell>{connector.name}</TableCell>
                        <TableCell>
                          <Chip label={connector.type} size="small" />
                        </TableCell>
                        <TableCell>{connector.api_id || "-"}</TableCell>
                        <TableCell>
                          {testResult && (
                            <Chip
                              label={testResult.status}
                              size="small"
                              color={getStatusColor(testResult) as any}
                              icon={
                                testResult.connected ? (
                                  <SuccessIcon />
                                ) : (
                                  <ErrorIcon />
                                )
                              }
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {new Date(connector.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleTest(connector.id)}
                            title="Test Connection"
                          >
                            <TestIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleOpenDialog(connector)}
                          >
                            <EditIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              setConnectorToDelete(connector.id);
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingConnector ? "Edit Connector" : "Create Connector"}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Name"
              fullWidth
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              required
            />

            <FormControl fullWidth required>
              <InputLabel>Type</InputLabel>
              <Select
                value={formData.type}
                onChange={(e) =>
                  setFormData({ ...formData, type: e.target.value })
                }
                label="Type"
              >
                {CONNECTOR_TYPES.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="API ID (optional)"
              fullWidth
              type="number"
              value={formData.api_id || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  api_id: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
            />

            <TextField
              label="Configuration (JSON)"
              fullWidth
              multiline
              rows={8}
              value={configJson}
              onChange={(e) => setConfigJson(e.target.value)}
              required
              placeholder='{"host": "localhost", "port": 5432, "database": "mydb"}'
              helperText="Enter connector configuration as JSON"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingConnector ? "Update" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this connector?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Connectors;
