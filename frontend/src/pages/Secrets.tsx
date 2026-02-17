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
  FormControl,
  InputLabel,
  OutlinedInput,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
} from "@mui/icons-material";
import { secretsService } from "../services/secrets";
import type { Secret, CreateSecretRequest } from "../services/secrets";

export const Secrets: React.FC = () => {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [rotateDialogOpen, setRotateDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null);
  const [decryptedValue, setDecryptedValue] = useState<string>("");
  const [showValue, setShowValue] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const [newSecretData, setNewSecretData] = useState<CreateSecretRequest>({
    key: "",
    value: "",
    description: "",
    tags: [],
  });

  const [updateValue, setUpdateValue] = useState("");
  const [rotateValue, setRotateValue] = useState("");
  const [tagInput, setTagInput] = useState("");

  useEffect(() => {
    loadSecrets();
  }, []);

  const loadSecrets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await secretsService.list();
      setSecrets(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load secrets");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      setError(null);
      await secretsService.create(newSecretData);
      setSuccess("Secret created successfully");
      await loadSecrets();
      setCreateDialogOpen(false);
      setNewSecretData({ key: "", value: "", description: "", tags: [] });
      setTagInput("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create secret");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedSecret) return;

    try {
      setLoading(true);
      setError(null);
      await secretsService.update(
        selectedSecret.key,
        updateValue,
        selectedSecret.description,
      );
      setSuccess("Secret updated successfully");
      await loadSecrets();
      setUpdateDialogOpen(false);
      setUpdateValue("");
      setSelectedSecret(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update secret");
    } finally {
      setLoading(false);
    }
  };

  const handleRotate = async () => {
    if (!selectedSecret) return;

    try {
      setLoading(true);
      setError(null);
      await secretsService.rotate(selectedSecret.key, rotateValue);
      setSuccess("Secret rotated successfully");
      await loadSecrets();
      setRotateDialogOpen(false);
      setRotateValue("");
      setSelectedSecret(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to rotate secret");
    } finally {
      setLoading(false);
    }
  };

  const handleView = async (secret: Secret) => {
    try {
      setLoading(true);
      setError(null);
      const data = await secretsService.get(secret.key, true);
      setDecryptedValue(data.value || "");
      setSelectedSecret(secret);
      setViewDialogOpen(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to decrypt secret");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (key: string) => {
    if (
      !confirm(
        "Are you sure you want to delete this secret? This action cannot be undone.",
      )
    )
      return;

    try {
      setLoading(true);
      setError(null);
      await secretsService.delete(key);
      setSuccess("Secret deleted successfully");
      await loadSecrets();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete secret");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !newSecretData.tags?.includes(tagInput.trim())) {
      setNewSecretData({
        ...newSecretData,
        tags: [...(newSecretData.tags || []), tagInput.trim()],
      });
      setTagInput("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setNewSecretData({
      ...newSecretData,
      tags: (newSecretData.tags || []).filter((t) => t !== tag),
    });
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
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
            Secrets Management
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            disabled={loading}
          >
            Create Secret
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Store and manage encrypted secrets. All values are encrypted at rest
          using Fernet encryption.
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
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Updated</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {secrets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No secrets yet. Create your first secret to get started.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                secrets.map((secret) => (
                  <TableRow key={secret.id} hover>
                    <TableCell>
                      <Typography
                        variant="body2"
                        fontWeight={500}
                        fontFamily="monospace"
                      >
                        {secret.key}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {secret.description || "N/A"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap">
                        {secret.tags && secret.tags.length > 0 ? (
                          secret.tags.map((tag) => (
                            <Chip
                              key={tag}
                              label={tag}
                              size="small"
                              sx={{ mb: 0.5 }}
                            />
                          ))
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            N/A
                          </Typography>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {formatDate(secret.created_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {formatDate(secret.updated_at)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Stack
                        direction="row"
                        spacing={1}
                        justifyContent="flex-end"
                      >
                        <Tooltip title="View Decrypted">
                          <IconButton
                            size="small"
                            onClick={() => handleView(secret)}
                            disabled={loading}
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Update">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedSecret(secret);
                              setUpdateDialogOpen(true);
                            }}
                            disabled={loading}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Rotate">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedSecret(secret);
                              setRotateDialogOpen(true);
                            }}
                            disabled={loading}
                          >
                            <RefreshIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDelete(secret.key)}
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

      {/* Create Secret Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Secret</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <TextField
              label="Secret Name"
              fullWidth
              required
              value={newSecretData.key}
              onChange={(e) =>
                setNewSecretData({ ...newSecretData, key: e.target.value })
              }
              helperText="Unique identifier for this secret"
            />
            <FormControl variant="outlined" fullWidth required>
              <InputLabel>Secret Value</InputLabel>
              <OutlinedInput
                type={showValue ? "text" : "password"}
                value={newSecretData.value}
                onChange={(e) =>
                  setNewSecretData({ ...newSecretData, value: e.target.value })
                }
                endAdornment={
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowValue(!showValue)}
                      edge="end"
                    >
                      {showValue ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                }
                label="Secret Value"
              />
            </FormControl>
            <TextField
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={newSecretData.description}
              onChange={(e) =>
                setNewSecretData({
                  ...newSecretData,
                  description: e.target.value,
                })
              }
            />
            <Box>
              <Stack direction="row" spacing={1} mb={1}>
                <TextField
                  label="Add Tag"
                  size="small"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleAddTag()}
                />
                <Button
                  variant="outlined"
                  onClick={handleAddTag}
                  disabled={!tagInput.trim()}
                >
                  Add
                </Button>
              </Stack>
              <Stack direction="row" spacing={0.5} flexWrap="wrap">
                {newSecretData.tags?.map((tag) => (
                  <Chip
                    key={tag}
                    label={tag}
                    onDelete={() => handleRemoveTag(tag)}
                    size="small"
                    sx={{ mb: 0.5 }}
                  />
                ))}
              </Stack>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={loading || !newSecretData.key || !newSecretData.value}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* View Secret Dialog */}
      <Dialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>View Secret: {selectedSecret?.key}</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            This secret is decrypted and displayed in plain text. Make sure no
            one is watching your screen.
          </Alert>
          <TextField
            fullWidth
            multiline
            rows={4}
            value={decryptedValue}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() =>
                      handleCopy(decryptedValue, selectedSecret?.id || 0)
                    }
                    edge="end"
                  >
                    {copiedId === selectedSecret?.id ? (
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
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Update Secret Dialog */}
      <Dialog
        open={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Update Secret: {selectedSecret?.key}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <FormControl variant="outlined" fullWidth required>
              <InputLabel>New Value</InputLabel>
              <OutlinedInput
                type={showValue ? "text" : "password"}
                value={updateValue}
                onChange={(e) => setUpdateValue(e.target.value)}
                endAdornment={
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowValue(!showValue)}
                      edge="end"
                    >
                      {showValue ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                }
                label="New Value"
              />
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUpdateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpdate}
            variant="contained"
            disabled={loading || !updateValue}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rotate Secret Dialog */}
      <Dialog
        open={rotateDialogOpen}
        onClose={() => setRotateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Rotate Secret: {selectedSecret?.key}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Rotating will replace the current secret value with a new one. Make
            sure all services are updated to use the new value.
          </Alert>
          <FormControl variant="outlined" fullWidth required>
            <InputLabel>New Value</InputLabel>
            <OutlinedInput
              type={showValue ? "text" : "password"}
              value={rotateValue}
              onChange={(e) => setRotateValue(e.target.value)}
              endAdornment={
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowValue(!showValue)}
                    edge="end"
                  >
                    {showValue ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </InputAdornment>
              }
              label="New Value"
            />
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRotateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleRotate}
            variant="contained"
            disabled={loading || !rotateValue}
          >
            Rotate
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};
