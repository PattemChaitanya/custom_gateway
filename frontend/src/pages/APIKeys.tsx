import React, { useState, useEffect } from "react";
import {
  Box,
  Container,
  Typography,
  Button,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Tooltip,
  Stack,
  InputAdornment,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Block as BlockIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
} from "@mui/icons-material";
import { apiKeysService } from "../services/apiKeys";
import type { APIKey, CreateAPIKeyRequest } from "../services/apiKeys";

export const APIKeys: React.FC = () => {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKeyData, setNewKeyData] = useState<CreateAPIKeyRequest>({
    label: "",
    scopes: "",
    expires_in_days: 7,
  });
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiKeysService.list();
      setKeys(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiKeysService.create(newKeyData);
      setGeneratedKey(result.key);
      setSuccess("API key created successfully");
      await loadKeys();
      setNewKeyData({ label: "", scopes: "", expires_in_days: 365 });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create API key");
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (keyId: number) => {
    if (!confirm("Are you sure you want to revoke this API key?")) return;

    try {
      setLoading(true);
      setError(null);
      await apiKeysService.revoke(keyId);
      setSuccess("API key revoked successfully");
      await loadKeys();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to revoke API key");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (keyId: number) => {
    if (
      !confirm(
        "Are you sure you want to delete this API key? This action cannot be undone.",
      )
    )
      return;

    try {
      setLoading(true);
      setError(null);
      await apiKeysService.delete(keyId);
      setSuccess("API key deleted successfully");
      await loadKeys();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete API key");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCloseDialog = () => {
    setCreateDialogOpen(false);
    setGeneratedKey(null);
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
  };

  const isExpired = (expiresAt: string | undefined) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

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
            API Keys
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            disabled={loading}
          >
            Generate API Key
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Manage your API keys for authentication. Keep your keys secure and
          never share them publicly.
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert
          severity="success"
          sx={{ mb: 3 }}
          onClose={() => setSuccess(null)}
        >
          {success}
        </Alert>
      )}

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Label</TableCell>
                <TableCell>Key Preview</TableCell>
                <TableCell>Scopes</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Expires</TableCell>
                <TableCell>Last Used</TableCell>
                <TableCell>Usage Count</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {keys.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No API keys yet. Create your first API key to get started.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                keys.map((key) => (
                  <TableRow key={key.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {key.label}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Typography
                          variant="body2"
                          fontFamily="monospace"
                          sx={{ fontSize: "0.75rem" }}
                        >
                          {key.key_preview}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {key.scopes || "N/A"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={
                          key.revoked
                            ? "Revoked"
                            : isExpired(key.expires_at)
                              ? "Expired"
                              : "Active"
                        }
                        color={
                          key.revoked
                            ? "error"
                            : isExpired(key.expires_at)
                              ? "warning"
                              : "success"
                        }
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {formatDate(key.created_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {formatDate(key.expires_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {formatDate(key.last_used_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{key.usage_count}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Stack
                        direction="row"
                        spacing={1}
                        justifyContent="flex-end"
                      >
                        {!key.revoked && (
                          <Tooltip title="Revoke">
                            <IconButton
                              size="small"
                              onClick={() => handleRevoke(key.id)}
                              disabled={loading}
                            >
                              <BlockIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDelete(key.id)}
                            disabled={loading}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Create API Key Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {generatedKey ? "API Key Generated" : "Generate New API Key"}
        </DialogTitle>
        <DialogContent>
          {generatedKey ? (
            <Box>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Make sure to copy your API key now. You won't be able to see it
                again!
              </Alert>
              <TextField
                fullWidth
                label="Your API Key"
                value={generatedKey}
                InputProps={{
                  readOnly: true,
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => handleCopy(generatedKey, 0)}
                        edge="end"
                      >
                        {copiedId === 0 ? (
                          <CheckIcon color="success" />
                        ) : (
                          <CopyIcon />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{ fontFamily: "monospace" }}
              />
            </Box>
          ) : (
            <Stack spacing={2} sx={{ mt: 2 }}>
              <TextField
                label="Label"
                fullWidth
                required
                value={newKeyData.label}
                onChange={(e) =>
                  setNewKeyData({ ...newKeyData, label: e.target.value })
                }
                helperText="A descriptive name for this API key"
              />
              <TextField
                label="Scopes"
                fullWidth
                value={newKeyData.scopes}
                onChange={(e) =>
                  setNewKeyData({ ...newKeyData, scopes: e.target.value })
                }
                helperText="Comma-separated list of scopes (e.g., read, write, admin)"
              />
              <TextField
                label="Expires In (Days)"
                type="number"
                fullWidth
                value={newKeyData.expires_in_days}
                onChange={(e) =>
                  setNewKeyData({
                    ...newKeyData,
                    expires_in_days: parseInt(e.target.value),
                  })
                }
                helperText="Number of days until the key expires (0 for never)"
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>
            {generatedKey ? "Close" : "Cancel"}
          </Button>
          {!generatedKey && (
            <Button
              onClick={handleCreate}
              variant="contained"
              disabled={loading || !newKeyData.label}
            >
              Generate
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Container>
  );
};
