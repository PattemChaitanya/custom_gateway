import { logout } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { Container, Typography, Button } from "@mui/material";

export default function Dashboard() {
  // Profile is already loaded by App.tsx + ProtectedRoute — no need to refetch
  const profile = useAuthStore((s) => s.profile);
  const navigate = useNavigate();

  return (
    <Container maxWidth="md" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Dashboard</Typography>
      {profile ? (
        <div>
          <Typography>Welcome, {profile.email}</Typography>
          <Button
            variant="contained"
            style={{ marginLeft: 12 }}
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
        </div>
      ) : (
        <Typography>Loading...</Typography>
      )}
    </Container>
  );
}
