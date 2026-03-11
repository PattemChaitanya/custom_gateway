import { logout } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { Typography, Button, Box, CircularProgress } from "@mui/material";
import PageWrapper from "../components/PageWrapper";

export default function Dashboard() {
  const profile = useAuthStore((s) => s.profile);
  const navigate = useNavigate();

  return (
    <PageWrapper maxWidth="md">
      <Typography variant="h5">Dashboard</Typography>
      {profile ? (
        <Box sx={{ mt: 2 }}>
          <Typography>Welcome, {profile.email}</Typography>
          <Box sx={{ display: "flex", gap: 1.5, mt: 2, flexWrap: "wrap" }}>
            <Button
              variant="contained"
              onClick={() => navigate("/apis")}
            >
              Manage APIs
            </Button>
            <Button
              variant="outlined"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Logout
            </Button>
          </Box>
        </Box>
      ) : (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 2 }}>
          <CircularProgress size={20} />
          <Typography color="text.secondary">Loading...</Typography>
        </Box>
      )}
    </PageWrapper>
  );
}
