import {
  Container,
  Typography,
  Button,
  Box,
  Grid,
  Paper,
  Stack,
} from "@mui/material";
import {
  Security as SecurityIcon,
  Speed as SpeedIcon,
  BarChart as BarChartIcon,
  AccountTree as AccountTreeIcon,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";

const features = [
  {
    icon: <SecurityIcon fontSize="large" />,
    title: "Secure by Default",
    desc: "Role-based access control, API key management, and JWT authentication protect every endpoint out of the box.",
  },
  {
    icon: <SpeedIcon fontSize="large" />,
    title: "Rate Limiting & Load Balancing",
    desc: "Built-in rate limiting and intelligent load balancing keep your services fast and reliable under any traffic.",
  },
  {
    icon: <BarChartIcon fontSize="large" />,
    title: "Real-Time Metrics",
    desc: "Monitor request volume, latency, and error rates through a live dashboard with detailed audit logs.",
  },
  {
    icon: <AccountTreeIcon fontSize="large" />,
    title: "Multi-Service Routing",
    desc: "Register multiple backend services and let the gateway route, retry, and failover automatically.",
  },
];

export default function Home() {
  const profile = useAuthStore((s) => s.profile);
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        width: "100vw",
        minHeight: "100vh",
        overflowX: "hidden",
        background: (theme) =>
          theme.palette.mode === "dark"
            ? `linear-gradient(180deg, ${theme.palette.background.default}, ${theme.palette.background.paper})`
            : "linear-gradient(180deg, #fff, #f7fbff)",
      }}
    >
      {/* ─── Hero Section ─── */}
      <Box
        sx={{
          minHeight: { xs: "auto", md: "100vh" },
          display: "flex",
          alignItems: "center",
          py: { xs: 8, md: 0 },
        }}
      >
        <Container maxWidth="lg">
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              gap: { xs: 4, md: 6 },
              alignItems: "center",
            }}
          >
            {/* Hero text */}
            <Box sx={{ flex: 1 }}>
              <Typography
                variant="h2"
                sx={{
                  fontWeight: 800,
                  color: "text.primary",
                  lineHeight: 1.15,
                }}
              >
                Your Unified
                <br />
                <Box component="span" sx={{ color: "primary.main" }}>
                  API Gateway
                </Box>
              </Typography>

              <Typography
                variant="h6"
                sx={{ color: "text.secondary", mt: 2, fontWeight: 400 }}
              >
                A full-featured gateway management platform — route traffic,
                enforce security policies, monitor performance, and manage
                services all from one place.
              </Typography>

              <Stack direction="row" spacing={2} sx={{ mt: 4 }}>
                {profile ? (
                  <Button
                    variant="contained"
                    size="large"
                    onClick={() => navigate("/dashboard")}
                  >
                    Go to Dashboard
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="contained"
                      size="large"
                      onClick={() => navigate("/login")}
                    >
                      Log In
                    </Button>
                    <Button
                      variant="outlined"
                      size="large"
                      onClick={() => navigate("/register")}
                    >
                      Register
                    </Button>
                  </>
                )}
              </Stack>
            </Box>

            {/* Device mock */}
            <Box
              sx={{ flex: 1, display: "flex", justifyContent: "center" }}
              aria-hidden
            >
              <Box
                sx={{
                  width: { xs: "100%", sm: 440, lg: 540 },
                  maxWidth: "100%",
                  height: { xs: 260, sm: 300, lg: 340 },
                  background: (theme) =>
                    theme.palette.mode === "dark"
                      ? `linear-gradient(135deg, ${theme.palette.primary.dark}33, ${theme.palette.background.paper})`
                      : "linear-gradient(135deg, #e9f0ff, #ffffff)",
                  borderRadius: 3,
                  p: 2,
                  boxShadow: (theme) =>
                    theme.palette.mode === "dark"
                      ? "0 12px 40px rgba(0,0,0,0.35)"
                      : "0 12px 40px rgba(75,107,255,0.14)",
                }}
              >
                <Box
                  sx={{
                    bgcolor: "background.paper",
                    borderRadius: 2,
                    height: "100%",
                    p: 2,
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    gap: 1.25,
                  }}
                >
                  {[
                    { path: "/users/authenticate", method: "GET", status: 200 },
                    { path: "/orders", method: "POST", status: 201 },
                    { path: "/payments", method: "POST", status: 200 },
                    { path: "/health", method: "GET", status: 200 },
                  ].map((row) => (
                    <Box
                      key={row.path}
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <Box
                        sx={{
                          bgcolor: (theme) =>
                            theme.palette.mode === "dark"
                              ? "rgba(100,108,255,0.15)"
                              : "#eef2ff",
                          px: 1.5,
                          py: 0.75,
                          borderRadius: 1,
                          color: "primary.main",
                          fontSize: "0.85rem",
                          fontFamily: "monospace",
                        }}
                      >
                        {row.path}
                      </Box>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography
                          variant="body2"
                          sx={{ fontWeight: 700, color: "text.secondary" }}
                        >
                          {row.method}
                        </Typography>
                        <Box
                          sx={{
                            bgcolor: "success.main",
                            color: "#fff",
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            px: 1,
                            py: 0.25,
                            borderRadius: 0.5,
                          }}
                        >
                          {row.status}
                        </Box>
                      </Stack>
                    </Box>
                  ))}
                </Box>
              </Box>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* ─── Features Section ─── */}
      <Box sx={{ py: { xs: 6, md: 10 } }}>
        <Container maxWidth="lg">
          <Typography
            variant="h4"
            sx={{ fontWeight: 700, textAlign: "center", mb: 1 }}
          >
            Everything You Need to{" "}
            <Box component="span" sx={{ color: "primary.main" }}>
              Manage APIs
            </Box>
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: "text.secondary",
              textAlign: "center",
              mb: 6,
              maxWidth: 600,
              mx: "auto",
            }}
          >
            From authentication to analytics, the gateway handles the
            cross-cutting concerns so your teams can focus on building features.
          </Typography>

          <Grid container spacing={3}>
            {features.map((f) => (
              <Grid item xs={12} sm={6} md={3} key={f.title}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    height: "100%",
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    transition: "box-shadow 0.2s",
                    "&:hover": {
                      boxShadow: (theme) =>
                        theme.palette.mode === "dark"
                          ? "0 4px 20px rgba(0,0,0,0.4)"
                          : "0 4px 20px rgba(75,107,255,0.12)",
                    },
                  }}
                >
                  <Box sx={{ color: "primary.main", mb: 1.5 }}>{f.icon}</Box>
                  <Typography
                    variant="subtitle1"
                    sx={{ fontWeight: 700, mb: 0.5 }}
                  >
                    {f.title}
                  </Typography>
                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    {f.desc}
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* ─── CTA Section ─── */}
      <Box
        sx={{
          py: { xs: 6, md: 8 },
          textAlign: "center",
          background: (theme) =>
            theme.palette.mode === "dark"
              ? theme.palette.background.paper
              : "#f0f4ff",
        }}
      >
        <Container maxWidth="sm">
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
            Ready to get started?
          </Typography>
          <Typography variant="body1" sx={{ color: "text.secondary", mb: 3 }}>
            Create an account or log in to start managing your APIs in minutes.
          </Typography>
          <Stack direction="row" spacing={2} justifyContent="center">
            {profile ? (
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate("/dashboard")}
              >
                Open Dashboard
              </Button>
            ) : (
              <>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate("/register")}
                >
                  Create Account
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => navigate("/login")}
                >
                  Log In
                </Button>
              </>
            )}
          </Stack>
        </Container>
      </Box>
    </Box>
  );
}
