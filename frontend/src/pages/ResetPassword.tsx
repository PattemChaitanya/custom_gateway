import { useState } from "react";
import { resetPassword } from "../services/auth";
import { Container, TextField, Button, Typography, Alert } from "@mui/material";

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
    } catch (e) {
      setError("Failed to send reset link");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Container maxWidth="sm" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Reset password</Typography>
      {message && <Alert severity="success">{message}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      <form onSubmit={submit} style={{ display: "grid", gap: 12, marginTop: 12 }}>
        <TextField label="Email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Button type="submit" variant="contained" disabled={loading}>
          {loading ? "Sending…" : "Send reset link"}
        </Button>
      </form>
    </Container>
  );
}
