import { useState } from "react";
import api from "../services/api";
import { useNavigate } from "react-router-dom";
import { TextField, Button, Container, Typography, Alert } from "@mui/material";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await api.post(`/auth/register`, { email, password });
      if (r.data && r.data.error) setError(r.data.error);
      else navigate("/login");
    } catch (e) {
      setError("Registration failed");
    }
  }

  return (
    <Container maxWidth="sm" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Create account</Typography>
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
        <Button type="submit" variant="contained">Create account</Button>
      </form>
    </Container>
  );
}
