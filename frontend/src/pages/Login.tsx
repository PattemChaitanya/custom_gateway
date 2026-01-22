import { useState } from "react";
import { login, me } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { TextField, Button, Container, Typography, Alert } from "@mui/material";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const setProfile = useAuthStore((s) => s.setProfile);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    // client-side validation
    const errs: { email?: string; password?: string } = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errs.email = "Enter a valid email";
    if (password.length < 6) errs.password = "Password must be at least 6 characters";
    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      return;
    }
    try {
      setLoading(true);
      const r = await login(email, password);
      if (r.error) {
        setError(r.error);
      } else {
        try {
          // use auth.me service which attaches Authorization header via axios interceptor
          const js = await me();
          setProfile({ email: js.email });
        } catch (_) {
          // ignore profile fetch error
        }
        navigate("/dashboard");
      }
    } catch (e) {
      setError("Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Container maxWidth="sm" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Sign in</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <form onSubmit={submit} style={{ display: "grid", gap: 12, marginTop: 12 }}>
        <TextField
          label="Email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={!!fieldErrors.email}
          helperText={fieldErrors.email}
        />
        <TextField
          label="Password"
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={!!fieldErrors.password}
          helperText={fieldErrors.password}
        />
        <Button type="submit" variant="contained" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </Container>
  );
}
