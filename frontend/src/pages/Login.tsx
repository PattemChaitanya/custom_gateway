import { useState } from "react";
import { login, me } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import {
  Typography,
  Alert,
  Box,
  TextField,
  Button,
  Checkbox,
  FormControlLabel,
  InputAdornment,
  IconButton,
  Paper,
  Avatar,
  Link as MuiLink,
} from "@mui/material";
import { Visibility, VisibilityOff, Person } from "@mui/icons-material";

export default function Login() {
  const [email, setEmail] = useState(
    atob(localStorage.getItem("-princem") || ""),
  );
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remember, setRemember] = useState(
    localStorage.getItem("remember") === "1",
  );
  const navigate = useNavigate();
  const setProfile = useAuthStore((s) => s.setProfile);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    const errs: { email?: string; password?: string } = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
      errs.email = "Enter a valid email";
    if (password.length < 6)
      errs.password = "Password must be at least 6 characters";
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
        const js = await me();
        if ((js as any).error) {
          setError((js as any).error);
          return;
        }
        setProfile({
          id: js.id,
          email: js.email,
          is_active: js.is_active,
          is_superuser: js.is_superuser,
          roles: js.roles || [],
          permissions: js.permissions || [],
        });
        if (remember) {
          localStorage.setItem("remember", "1");
          localStorage.setItem("-princem", btoa(email));
        } else {
          localStorage.removeItem("remember");
          localStorage.removeItem("-princem");
        }
        navigate("/dashboard");
      }
    } catch {
      setError("Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: (theme) =>
          theme.palette.mode === "dark"
            ? `linear-gradient(135deg, ${theme.palette.background.default} 0%, ${theme.palette.primary.dark}22 100%)`
            : `linear-gradient(135deg, #ffd4d1 0%, #fff3e6 40%, #f1e9ff 100%)`,
        p: 2,
      }}
    >
      <Paper
        elevation={3}
        sx={{
          width: { xs: "100%", sm: 400 },
          maxWidth: 400,
          p: { xs: 3, sm: 4 },
          pt: { xs: 7, sm: 8 },
          borderRadius: 3,
          position: "relative",
          textAlign: "center",
        }}
      >
        <Avatar
          sx={{
            width: 80,
            height: 80,
            bgcolor: "primary.main",
            position: "absolute",
            top: -40,
            left: "50%",
            transform: "translateX(-50%)",
            boxShadow: 3,
          }}
        >
          <Person sx={{ fontSize: 40 }} />
        </Avatar>

        <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
          LOGIN
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box
          component="form"
          onSubmit={submit}
          aria-label="login form"
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <TextField
            label="Email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={!!fieldErrors.email}
            helperText={fieldErrors.email}
            fullWidth
            size="small"
          />

          <TextField
            label="Password"
            placeholder="password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={!!fieldErrors.password}
            helperText={fieldErrors.password}
            fullWidth
            size="small"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    onClick={() => setShowPassword(!showPassword)}
                    edge="end"
                    size="small"
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <FormControlLabel
              control={
                <Checkbox
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  size="small"
                />
              }
              label={
                <Typography variant="body2" color="text.secondary">
                  Remember me
                </Typography>
              }
            />
            <MuiLink
              component="button"
              type="button"
              variant="body2"
              onClick={() => navigate("/reset-password")}
              sx={{ textDecoration: "none" }}
            >
              Forgot Password?
            </MuiLink>
          </Box>

          <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={loading}
            sx={{ py: 1.2, fontWeight: 600, borderRadius: 6 }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Are you new?{" "}
          <MuiLink
            component="button"
            type="button"
            onClick={() => navigate("/register")}
            sx={{ fontWeight: 500 }}
          >
            Register here
          </MuiLink>
        </Typography>
      </Paper>
    </Box>
  );
}
