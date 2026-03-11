import { useState } from "react";
import { resetPassword } from "../services/auth";
import { TextField, Button, Typography, Alert, Box } from "@mui/material";
import PageWrapper from "../components/PageWrapper";

export default function ResetPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      setLoading(true);
      const r = await resetPassword(email);
      if (r && r.error) setError(r.error);
      else setMessage(r.message || "Password reset link sent");
    } catch {
      setError("Failed to send reset link");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageWrapper maxWidth="sm">
      <Typography variant="h5">Reset password</Typography>
      {message && (
        <Alert severity="success" sx={{ mt: 1 }}>
          {message}
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}
      <Box
        component="form"
        onSubmit={submit}
        sx={{ display: "grid", gap: 1.5, mt: 1.5 }}
      >
        <TextField
          label="Email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          fullWidth
        />
        <Button type="submit" variant="contained" disabled={loading}>
          {loading ? "Sending…" : "Send reset link"}
        </Button>
      </Box>
    </PageWrapper>
  );
}
