import { Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ResetPassword from "./pages/ResetPassword";
import VerifyOtp from "./pages/VerifyOtp";
import Dashboard from "./pages/Dashboard";
// import APIs from "./pages/APIs";
// import APIDetail from "./pages/APIDetail";
import RoutesPage from "./pages/Routes";
import CreateAPI from "./pages/CreateAPI";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/verify-otp" element={<VerifyOtp />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/apis" element={<RoutesPage />} />
        {/* <Route path="/apis/:id" element={<APIDetail />} /> */}
        <Route path="/apis/create" element={<CreateAPI />} />
        <Route path="/apis/:id/edit" element={<CreateAPI />} />
        {/* <Route path="/apis/:id/routes" element={<RoutesPage />} /> */}
      </Route>
    </Routes>
  );
}
