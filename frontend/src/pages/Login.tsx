import { useState } from "react";
import { login, me } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { Typography, Alert } from "@mui/material";
import "./Login.css";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [remember, setRemember] = useState(false);
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
        // persist remember preference
        try {
          if (remember) localStorage.setItem('remember', '1');
          else localStorage.removeItem('remember');
        } catch (_) {}
        navigate("/dashboard");
      }
    } catch (e) {
      setError("Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="avatar" aria-hidden>
          <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
            <path d="M12 12c2.7 0 4.9-2.2 4.9-4.9S14.7 2.2 12 2.2 7.1 4.4 7.1 7.1 9.3 12 12 12zm0 2.2c-3.3 0-9.8 1.7-9.8 5v1.6h19.6V19.2c0-3.3-6.5-5-9.8-5z" />
          </svg>
        </div>

        <Typography variant="h6" style={{ marginBottom: 6, color: "#6e6e6e" }}>
          LOGIN
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <form onSubmit={submit} className="login-form" aria-label="login form">
          <div className="input-row">
            <span className="icon">👤</span>
            <input
              aria-label="email"
              placeholder="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {fieldErrors.email && <div className="error">{fieldErrors.email}</div>}

          <div className="input-row">
            <span className="icon">🔒</span>
            <input
              aria-label="password"
              placeholder="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {fieldErrors.password && <div className="error">{fieldErrors.password}</div>}

          <div className="options">
            <label>
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              <span style={{ fontSize: 13, color: "#777" }}>Remember me</span>
            </label>
            <a href="#" onClick={(e) => { e.preventDefault(); navigate('/reset-password'); }}>
              Forgot Password?
            </a>
          </div>

          <button className="login-button" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
