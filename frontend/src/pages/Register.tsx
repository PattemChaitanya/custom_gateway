import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, me, register } from "../services/auth";
import useAuthStore from "../hooks/useAuth";
import { TextField, Button, Container, Typography, Alert, Checkbox, FormControlLabel } from "@mui/material";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const setProfile = useAuthStore((s) => s.setProfile);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string; terms?: string }>({});
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    const errs: { email?: string; password?: string; terms?: string } = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errs.email = "Enter a valid email";
    if (password.length < 6) errs.password = "Password must be at least 6 characters";
    if (password !== confirmPassword) errs.password = "Passwords do not match";
    if (!acceptedTerms) errs.terms = "Please accept Terms of Use";
    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      return;
    }
    try {
      setLoading(true);
      const r = await register(email, password, { firstName, lastName });
      if (r && r.error) {
        setError(r.error);
      } else {
        // auto-login after successful registration
        try {
          const loginResp = await login(email, password);
          if (loginResp && loginResp.access_token) {
            // populate profile
            const js = await me();
            setProfile({ email: js.email });
            // persist remember preference before login so token setter can persist tokens
            localStorage.setItem('remember', '1');
            localStorage.setItem('-princem', btoa(email));
            localStorage.setItem('-prince', btoa(password));
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
        <div style={{ display: "flex", gap: 12 }}>
          <TextField label="First Name" placeholder="First Name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          <TextField label="Last Name" placeholder="Last Name" value={lastName} onChange={(e) => setLastName(e.target.value)} />
        </div>
        <TextField
          label="Email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)} error={!!fieldErrors.email} helperText={fieldErrors.email} />
        <TextField label="Password" placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} error={!!fieldErrors.password} helperText={fieldErrors.password} />
        <TextField label="Confirm Password" placeholder="confirm password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
        <div>
          <FormControlLabel control={<Checkbox checked={acceptedTerms} onChange={(e) => setAcceptedTerms(e.target.checked)} />} label={"I accept Terms of Use"} />
          {fieldErrors.terms ? <div style={{ color: '#d32f2f', fontSize: 12 }}>{fieldErrors.terms}</div> : null}
        </div>
        <Button type="submit" variant="contained" disabled={loading} style={{ background: 'linear-gradient(90deg,#19c6ff,#00f6c3)', color: '#fff', padding: '12px 24px', fontWeight: 700 }}>
          {loading ? "Registering…" : "REGISTER NOW"}
        </Button>
      </form>
    </Container>
  );
}
