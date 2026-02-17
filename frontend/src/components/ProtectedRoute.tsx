import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../hooks/useAuth";
import { getCurrentUserInfo } from "../services/auth";
import Header from "./Header";
import { CircularProgress, Box } from "@mui/material";

export default function ProtectedRoute() {
  const token = useAuthStore((s) => s.accessToken);
  const setProfile = useAuthStore((s) => s.setProfile);
  const profile = useAuthStore((s) => s.profile);
  const [loading, setLoading] = useState(!profile);

  useEffect(() => {
    // Load user profile with roles and permissions
    if (token && !profile) {
      getCurrentUserInfo()
        .then((userInfo) => {
          setProfile({
            id: userInfo.id,
            email: userInfo.email,
            is_active: userInfo.is_active,
            is_superuser: userInfo.is_superuser,
            roles: userInfo.roles || [],
            permissions: userInfo.permissions || [],
          });
        })
        .catch((err) => {
          console.error("Failed to load user profile:", err);
        })
        .finally(() => {
          setLoading(false);
        });
    } else if (profile) {
      setLoading(false);
    }
  }, [token, profile, setProfile]);

  if (!token) return <Navigate to="/login" replace />;

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <Header />
      {/* spacer ensures main content is not hidden under the fixed header */}
      <div className="main-with-topbar">
        <Outlet />
      </div>
    </>
  );
}
