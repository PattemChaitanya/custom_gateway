import { useEffect } from "react";
import { me, logout } from "../services/auth";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { Container, Typography, Button } from "@mui/material";

export default function Dashboard() {
  const profile = useAuthStore((s) => s.profile);
  const setProfile = useAuthStore((s) => s.setProfile);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const data = await me();
        setProfile({ email: data.email });
      } catch (e) {
        navigate("/login");
      }
    })();
  }, []);

  return (
    <Container maxWidth="md" style={{ paddingTop: 24 }}>
      <Typography variant="h5">Dashboard</Typography>
      {profile ? (
        <div>
          <Typography>Welcome, {profile.email}</Typography>
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
