import { useState } from "react";
import { login } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { TextField, Button, Container, Typography, Alert } from "@mui/material";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const setProfile = useAuthStore((s) => s.setProfile);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await login(email, password);
      if (r.error) {
        setError(r.error);
      } else {
        try {
          // use auth.me which uses api.get and will attach Authorization header via store
          // call via service to populate profile
          const meResp = await fetch(((import.meta.env.VITE_API_URL as string) || "http://localhost:8000") + "/auth/me", {
            headers: { Authorization: `Bearer ${r.access_token}` },
          });
          const js = await meResp.json();
          setProfile({ email: js.email });
        } catch (_) {
          // ignore profile fetch error
        }
        navigate("/dashboard");
      }
    } catch (e) {
      setError("Login failed");
    }
  }

  return (
    <Container maxWidth="sm" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Sign in</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <form onSubmit={submit} style={{ display: "grid", gap: 12, marginTop: 12 }}>
        <TextField label="Email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextField
          label="Password"
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" variant="contained">Sign in</Button>
      </form>
    </Container>
  );
}
