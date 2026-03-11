import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, me, register } from "../services/auth";
import useAuthStore from "../hooks/useAuth";
import {
  TextField,
  Button,
  Typography,
  Alert,
  Checkbox,
  FormControlLabel,
  Box,
} from "@mui/material";
import PageWrapper from "../components/PageWrapper";

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
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
    terms?: string;
  }>({});
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    const errs: { email?: string; password?: string; terms?: string } = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
      errs.email = "Enter a valid email";
    if (password.length < 6)
      errs.password = "Password must be at least 6 characters";
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
        try {
          const loginResp = await login(email, password);
          if (loginResp && loginResp.access_token) {
            const js = await me();
            setProfile({ email: js.email });
            localStorage.setItem("remember", "1");
            localStorage.setItem("-princem", btoa(email));
            navigate("/dashboard");
            return;
          }
        } catch (_) {
          // fallback to login page
        }
        navigate("/login");
      }
    } catch {
      setError("Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageWrapper maxWidth="sm">
      <Typography variant="h5">Create account</Typography>
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
        <Box
          sx={{
            display: "flex",
            gap: 1.5,
            flexDirection: { xs: "column", sm: "row" },
          }}
        >
          <TextField
            label="First Name"
            placeholder="First Name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            fullWidth
          />
          <TextField
            label="Last Name"
            placeholder="Last Name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            fullWidth
          />
        </Box>
        <TextField
          label="Email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={!!fieldErrors.email}
          helperText={fieldErrors.email}
          fullWidth
        />
        <TextField
          label="Password"
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={!!fieldErrors.password}
          helperText={fieldErrors.password}
          fullWidth
        />
        <TextField
          label="Confirm Password"
          placeholder="confirm password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          fullWidth
        />
        <Box>
          <FormControlLabel
            control={
              <Checkbox
                checked={acceptedTerms}
                onChange={(e) => setAcceptedTerms(e.target.checked)}
              />
            }
            label="I accept Terms of Use"
          />
          {fieldErrors.terms ? (
            <Typography variant="caption" color="error">
              {fieldErrors.terms}
            </Typography>
          ) : null}
        </Box>
        <Button
          type="submit"
          variant="contained"
          disabled={loading}
          sx={{ py: 1.5, fontWeight: 700 }}
        >
          {loading ? "Registering…" : "REGISTER NOW"}
        </Button>
      </Box>
    </PageWrapper>
  );
}
