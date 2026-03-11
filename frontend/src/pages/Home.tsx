import { Container, Typography, Button, Box } from "@mui/material";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";

export default function Home() {
  const profile = useAuthStore((s) => s.profile);
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        py: { xs: 4, md: 6 },
        background: (theme) =>
          theme.palette.mode === "dark"
            ? `linear-gradient(180deg, ${theme.palette.background.default}, ${theme.palette.background.paper})`
            : "linear-gradient(180deg, #fff, #f7fbff)",
      }}
    >
      <Container maxWidth="lg">
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: { xs: 3, md: 4 },
            alignItems: "center",
          }}
        >
          {/* Hero text */}
          <Box sx={{ flex: 1 }}>
            <Typography
              variant="h3"
              sx={{
                fontWeight: 700,
                color: "text.primary",
              }}
            >
              Simplify Your
              <br />
              <Box component="span" sx={{ color: "primary.main" }}>
                API Management
              </Box>
            </Typography>
            <Typography variant="body1" sx={{ color: "text.secondary", mt: 2 }}>
              Easily deploy, monitor, and secure your APIs with our powerful API
              management platform. Boost your development workflow and ensure
              seamless API integration.
            </Typography>
            <Box sx={{ mt: 3 }}>
              {profile ? (
                <Button
                  variant="contained"
                  color="primary"
                  size="large"
                  onClick={() => navigate("/dashboard")}
                >
                  Go to Dashboard
                </Button>
              ) : (
                <Button
                  variant="contained"
                  color="primary"
                  size="large"
                  onClick={() => navigate("/login")}
                >
                  Log in
                </Button>
              )}
            </Box>
          </Box>

          {/* Device mock */}
          <Box
            sx={{ flex: 1, display: "flex", justifyContent: "center" }}
            aria-hidden
          >
            <Box
              sx={{
                width: { xs: "100%", sm: 420, lg: 520 },
                maxWidth: "100%",
                height: { xs: 240, sm: 280, lg: 320 },
                background: (theme) =>
                  theme.palette.mode === "dark"
                    ? `linear-gradient(180deg, ${theme.palette.primary.dark}33, ${theme.palette.background.paper})`
                    : "linear-gradient(180deg, #e9f0ff, #ffffff)",
                borderRadius: 2,
                p: 2,
                boxShadow: (theme) =>
                  theme.palette.mode === "dark"
                    ? "0 10px 30px rgba(0,0,0,0.3)"
                    : "0 10px 30px rgba(75,107,255,0.12)",
              }}
            >
              <Box
                sx={{
                  bgcolor: "background.paper",
                  borderRadius: 1,
                  height: "calc(100% - 24px)",
                  p: 1.5,
                  overflow: "hidden",
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                }}
              >
                {[
                  { path: "/users/authenticate", method: "GET" },
                  { path: "/orders", method: "POST" },
                  { path: "/payments", method: "POST" },
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
                        fontSize: "0.875rem",
                      }}
                    >
                      {row.path}
                    </Box>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 700, color: "text.secondary" }}
                    >
                      {row.method}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        </Box>
      </Container>
    </Box>
  );
}
