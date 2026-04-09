import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Select,
  InputLabel,
  FormControl,
  Alert,
  LinearProgress,
  Tooltip,
  Skeleton,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import PageWrapper from "../components/PageWrapper";
import usePermissions from "../hooks/usePermissions";
import {
  listAccounts,
  getAccountUsage,
  updateAccount,
  createAccount,
  deleteAccount,
  type Account,
  type AccountUsage,
} from "../services/accounts";

const PLAN_COLORS: Record<string, "default" | "primary" | "secondary"> = {
  free: "default",
  pro: "primary",
  enterprise: "secondary",
};

function UsageCell({ accountId }: { accountId: number }) {
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  useEffect(() => {
    getAccountUsage(accountId)
      .then(setUsage)
      .catch(() => setUsage(null));
  }, [accountId]);

  if (!usage) return <TableCell>—</TableCell>;
  const pct = usage.daily_quota
    ? Math.min(100, (usage.used_today / usage.daily_quota) * 100)
    : 0;
  return (
    <TableCell>
      <Tooltip
        title={
          usage.daily_quota
            ? `${usage.used_today.toLocaleString()} / ${usage.daily_quota.toLocaleString()}`
            : "Unlimited"
        }
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 120 }}>
          <LinearProgress
            variant="determinate"
            value={pct}
            color={pct >= 90 ? "error" : pct >= 70 ? "warning" : "primary"}
            sx={{ flexGrow: 1, borderRadius: 1, height: 6 }}
          />
          <Typography variant="caption" color="text.secondary" noWrap>
            {usage.daily_quota ? `${Math.round(pct)}%` : "∞"}
          </Typography>
        </Box>
      </Tooltip>
    </TableCell>
  );
}

export default function Accounts() {
  const { isSuperuser } = usePermissions();
  if (!isSuperuser) return <Navigate to="/dashboard" replace />;

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [newSlug, setNewSlug] = useState("");
  const [newName, setNewName] = useState("");
  const [newPlan, setNewPlan] = useState("free");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  // Edit dialog
  const [editTarget, setEditTarget] = useState<Account | null>(null);
  const [editName, setEditName] = useState("");
  const [editPlan, setEditPlan] = useState("");
  const [editStatus, setEditStatus] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = () => {
    setLoading(true);
    listAccounts()
      .then(setAccounts)
      .catch((e) => setError(e?.response?.data?.detail ?? "Failed to load accounts"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    setCreating(true);
    setCreateError(null);
    try {
      await createAccount({ slug: newSlug, name: newName, plan: newPlan });
      setCreateOpen(false);
      setNewSlug("");
      setNewName("");
      setNewPlan("free");
      load();
    } catch (e: any) {
      setCreateError(e?.response?.data?.detail ?? "Failed to create");
    } finally {
      setCreating(false);
    }
  };

  const openEdit = (a: Account) => {
    setEditTarget(a);
    setEditName(a.name);
    setEditPlan(a.plan);
    setEditStatus(a.status);
    setEditError(null);
  };

  const handleSave = async () => {
    if (!editTarget) return;
    setSaving(true);
    setEditError(null);
    try {
      await updateAccount(editTarget.id, {
        name: editName,
        plan: editPlan,
        status: editStatus,
      });
      setEditTarget(null);
      load();
    } catch (e: any) {
      setEditError(e?.response?.data?.detail ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteAccount(deleteTarget.id);
      setDeleteTarget(null);
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to delete");
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <PageWrapper maxWidth="lg">
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>
          Accounts
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateOpen(true)}
        >
          New Account
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Slug</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Plan</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Daily Usage</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : accounts.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {a.slug}
                      </Typography>
                    </TableCell>
                    <TableCell>{a.name}</TableCell>
                    <TableCell>
                      <Chip
                        label={a.plan}
                        size="small"
                        color={PLAN_COLORS[a.plan] ?? "default"}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={a.status}
                        size="small"
                        variant="outlined"
                        color={a.status === "active" ? "success" : "warning"}
                      />
                    </TableCell>
                    <UsageCell accountId={a.id} />
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => openEdit(a)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => setDeleteTarget(a)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
            {!loading && accounts.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    No accounts found. Create one to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>New Account</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          {createError && <Alert severity="error">{createError}</Alert>}
          <TextField
            label="Slug"
            value={newSlug}
            onChange={(e) => setNewSlug(e.target.value.toLowerCase())}
            helperText="Lowercase letters, numbers, hyphens. Must start with a letter."
            size="small"
          />
          <TextField
            label="Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            size="small"
          />
          <FormControl size="small">
            <InputLabel>Plan</InputLabel>
            <Select
              value={newPlan}
              label="Plan"
              onChange={(e) => setNewPlan(e.target.value)}
            >
              <MenuItem value="free">Free</MenuItem>
              <MenuItem value="pro">Pro</MenuItem>
              <MenuItem value="enterprise">Enterprise</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={creating || !newSlug || !newName}
          >
            {creating ? "Creating…" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit dialog */}
      <Dialog
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Edit Account</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          {editError && <Alert severity="error">{editError}</Alert>}
          <TextField
            label="Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            size="small"
          />
          <FormControl size="small">
            <InputLabel>Plan</InputLabel>
            <Select
              value={editPlan}
              label="Plan"
              onChange={(e) => setEditPlan(e.target.value)}
            >
              <MenuItem value="free">Free</MenuItem>
              <MenuItem value="pro">Pro</MenuItem>
              <MenuItem value="enterprise">Enterprise</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small">
            <InputLabel>Status</InputLabel>
            <Select
              value={editStatus}
              label="Status"
              onChange={(e) => setEditStatus(e.target.value)}
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="suspended">Suspended</MenuItem>
              <MenuItem value="deleted">Deleted</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditTarget(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirm */}
      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Delete Account</DialogTitle>
        <DialogContent>
          <Typography>
            Delete <strong>{deleteTarget?.name}</strong> ({deleteTarget?.slug})?
            This will CASCADE-delete all APIs, keys, secrets, and environments
            belonging to this account.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? "Deleting…" : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </PageWrapper>
  );
}
