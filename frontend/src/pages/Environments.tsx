import React, { useState } from "react";
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
} from "@mui/material";
import { Add as AddIcon, Delete as DeleteIcon } from "@mui/icons-material";
import { apiKeysService } from "../services/apiKeys";
import type { Environment } from "../services/apiKeys";
import { useQueryCache } from "../hooks/useQueryCache";
import { TableSkeleton } from "../components/Skeletons";

const DEFAULT_SLUGS = ["production", "staging", "testing", "development"];

export const Environments: React.FC = () => {
  const {
    data: environments = [],
    loading,
    error: fetchError,
    refetch: refetchEnvironments,
  } = useQueryCache<Environment[]>("environments", () =>
    apiKeysService.listEnvironments(),
  );
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [formData, setFormData] = useState({ name: "", description: "" });

  const displayError = fetchError || error;
  const isDisabled = loading || mutating;

  const handleCreate = async () => {
    try {
      setMutating(true);
      setError(null);
      await apiKeysService.createEnvironment({
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
      });
      setSuccess("Environment created successfully");
      setFormData({ name: "", description: "" });
      setCreateOpen(false);
      await refetchEnvironments();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create environment");
    } finally {
      setMutating(false);
    }
  };

  const handleDelete = async (env: Environment) => {
    if (
      !confirm(
        `Delete "${env.name}" environment? API keys using it will keep their environment_id but it won't resolve to a name.`,
      )
    )
      return;

    try {
      setMutating(true);
      setError(null);
      await apiKeysService.deleteEnvironment(env.id);
      setSuccess(`"${env.name}" environment deleted`);
      await refetchEnvironments();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete environment");
    } finally {
      setMutating(false);
    }
  };

  const isDefault = (env: Environment) => DEFAULT_SLUGS.includes(env.slug);

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ mb: 4 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h4" component="h1" fontWeight={700}>
            Environments
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
            disabled={isDisabled}
          >
            New Environment
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Manage environments for organizing API keys across deployment stages.
        </Typography>
      </Box>

      {displayError && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {displayError}
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
        {loading ? (
          <TableSkeleton columns={5} rows={3} />
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Slug</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {environments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No environments yet. Default environments will be
                        created on server startup.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  environments.map((env) => (
                    <TableRow key={env.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {env.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          fontFamily="monospace"
                          color="text.secondary"
                        >
                          {env.slug}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {env.description || "—"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={isDefault(env) ? "Default" : "Custom"}
                          size="small"
                          color={isDefault(env) ? "primary" : "default"}
                          variant={isDefault(env) ? "filled" : "outlined"}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip
                          title={
                            isDefault(env)
                              ? "Default environments cannot be deleted"
                              : "Delete"
                          }
                        >
                          <span>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDelete(env)}
                              disabled={isDisabled || isDefault(env)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {/* Create Environment Dialog */}
      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create Environment</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <TextField
              label="Name"
              fullWidth
              required
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value.slice(0, 100) })
              }
              helperText={`Environment name (${formData.name.length}/100)`}
            />
            <TextField
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              helperText="Optional description"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={loading || !formData.name.trim()}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Environments;
