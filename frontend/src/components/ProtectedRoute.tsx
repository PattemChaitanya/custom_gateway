import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../hooks/useAuth";
import Header from "./Header";

export default function ProtectedRoute() {
  const token = useAuthStore((s) => s.accessToken);
  if (!token) return <Navigate to="/login" replace />;

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
