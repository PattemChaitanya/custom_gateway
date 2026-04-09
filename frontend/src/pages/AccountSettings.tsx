import { useEffect, useState } from "react";
import {
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
  TextField,
  Button,
  LinearProgress,
  Divider,
  Alert,
  Skeleton,
} from "@mui/material";
import PageWrapper from "../components/PageWrapper";
import useAuthStore from "../hooks/useAuth";
import usePermissions from "../hooks/usePermissions";
import {
  getAccount,
  getAccountUsage,
  updateAccount,
  type Account,
  type AccountUsage,
} from "../services/accounts";

const PLAN_COLORS: Record<string, "default" | "primary" | "secondary"> = {
  free: "default",
  pro: "primary",
  enterprise: "secondary",
};

export default function AccountSettings() {
  const profile = useAuthStore((s) => s.profile);
  const { isSuperuser } = usePermissions();

  const accountId = profile?.account_id;

  const [account, setAccount] = useState<Account | null>(null);
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!accountId) {
      setLoading(false);
      return;
    }
    Promise.all([getAccount(accountId), getAccountUsage(accountId)])
      .then(([acct, use]) => {
        setAccount(acct);
        setUsage(use);
        setEditName(acct.name);
      })
      .catch((e) => setError(e?.response?.data?.detail ?? "Failed to load account"))
      .finally(() => setLoading(false));
  }, [accountId]);

  const handleSave = async () => {
    if (!account) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateAccount(account.id, { name: editName });
      setAccount(updated);
      setSaved(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const usagePct =
    usage && usage.daily_quota
      ? Math.min(100, (usage.used_today / usage.daily_quota) * 100)
      : null;

  return (
    <PageWrapper maxWidth="md">
      <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
        Account Settings
      </Typography>

      {!accountId && !isSuperuser ? (
        <Alert severity="info">
          Your user account is not associated with a tenant account. Contact a
          superuser to be assigned to an account.
        </Alert>
      ) : loading ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Skeleton variant="rectangular" height={120} />
          <Skeleton variant="rectangular" height={80} />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : account ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* Account info card */}
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <Typography variant="h6" fontWeight={600}>
                  {account.name}
                </Typography>
                <Chip
                  label={account.plan}
                  size="small"
                  color={PLAN_COLORS[account.plan] ?? "default"}
                />
                <Chip
                  label={account.status}
                  size="small"
                  variant="outlined"
                  color={account.status === "active" ? "success" : "warning"}
                />
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                Slug: <strong>{account.slug}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                ID: {account.id}
              </Typography>
            </CardContent>
          </Card>

          {/* Usage card */}
          {usage && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Daily Gateway Usage
                </Typography>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {usage.used_today.toLocaleString()} requests today
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {usage.daily_quota
                      ? `${usage.daily_quota.toLocaleString()} / day`
                      : "Unlimited"}
                  </Typography>
                </Box>
                {usagePct !== null ? (
                  <LinearProgress
                    variant="determinate"
                    value={usagePct}
                    color={usagePct >= 90 ? "error" : usagePct >= 70 ? "warning" : "primary"}
                    sx={{ borderRadius: 1, height: 8 }}
                  />
                ) : (
                  <LinearProgress
                    variant="determinate"
                    value={0}
                    sx={{ borderRadius: 1, height: 8 }}
                  />
                )}
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                  Quota resets at {new Date(usage.quota_resets_at).toUTCString()}
                </Typography>
              </CardContent>
            </Card>
          )}

          <Divider />

          {/* Edit form */}
          <Box>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 2 }}>
              Edit Account
            </Typography>
            {saved && <Alert severity="success" sx={{ mb: 2 }}>Saved.</Alert>}
            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
              <TextField
                label="Account name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                size="small"
                sx={{ flexGrow: 1 }}
              />
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={saving || editName === account.name || !editName.trim()}
              >
                {saving ? "Saving…" : "Save"}
              </Button>
            </Box>
          </Box>
        </Box>
      ) : null}
    </PageWrapper>
  );
}
