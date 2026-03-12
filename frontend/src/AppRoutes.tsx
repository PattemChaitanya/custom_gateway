import { Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";
import { CircularProgress, Box } from "@mui/material";
import ProtectedRoute from "./components/ProtectedRoute";

// Lazy-loaded page components for code-splitting
const Home = lazy(() => import("./pages/Home"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const VerifyOtp = lazy(() => import("./pages/VerifyOtp"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const APIDetail = lazy(() => import("./pages/APIDetail"));
const RoutesPage = lazy(() => import("./pages/Routes"));
const CreateAPI = lazy(() => import("./pages/CreateAPI"));
const APIKeys = lazy(() =>
  import("./pages/APIKeys").then((m) => ({ default: m.APIKeys })),
);
const Secrets = lazy(() =>
  import("./pages/Secrets").then((m) => ({ default: m.Secrets })),
);
const AuditLogs = lazy(() =>
  import("./pages/AuditLogs").then((m) => ({ default: m.AuditLogs })),
);
const Connectors = lazy(() => import("./pages/Connectors"));
const Authorizers = lazy(() => import("./pages/Authorizers"));
const Environments = lazy(() => import("./pages/Environments"));
const MiniCloud = lazy(() => import("./pages/MiniCloud"));
const Users = lazy(() => import("./pages/Users"));

const PageLoader = () => (
  <Box
    sx={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "60vh",
    }}
  >
    <CircularProgress />
  </Box>
);

export default function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-otp" element={<VerifyOtp />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/apis" element={<RoutesPage />} />
          <Route path="/apis/create" element={<CreateAPI />} />
          <Route path="/apis/:id/edit" element={<CreateAPI />} />
          <Route path="/apis/:id" element={<APIDetail />} />
          <Route path="/api-keys" element={<APIKeys />} />
          <Route path="/secrets" element={<Secrets />} />
          <Route path="/audit-logs" element={<AuditLogs />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/authorizers" element={<Authorizers />} />
          <Route path="/environments" element={<Environments />} />
          <Route path="/mini-cloud" element={<MiniCloud />} />
          <Route path="/users" element={<Users />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
