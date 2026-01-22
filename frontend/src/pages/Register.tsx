import { useState } from "react";
import api from "../services/api";
import { useNavigate } from "react-router-dom";
import { login, me } from "../services/auth";
import useAuthStore from "../hooks/useAuth";
import { TextField, Button, Container, Typography, Alert } from "@mui/material";

export default function Register() {
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

    const errs: { email?: string; password?: string } = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errs.email = "Enter a valid email";
    if (password.length < 6) errs.password = "Password must be at least 6 characters";
    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      return;
    }
    try {
      setLoading(true);
      const r = await api.post(`/auth/register`, { email, password });
      if (r.data && r.data.error) {
        setError(r.data.error);
      } else {
        // auto-login after successful registration
        try {
          const loginResp = await login(email, password);
          if (loginResp && loginResp.access_token) {
            // populate profile
            try {
              const js = await me();
              setProfile({ email: js.email });
            } catch (_) {}
            navigate("/dashboard");
            return;
          }
        } catch (_) {
          // fallback to login page
        }
        navigate("/login");
      }
    } catch (e) {
      setError("Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Container maxWidth="sm" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Create account</Typography>
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
          {loading ? "Creating…" : "Create account"}
        </Button>
      </form>
    </Container>
  );
}
