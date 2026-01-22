import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import "./App.css";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ProtectedRoute from "./components/ProtectedRoute";
import useAuthStore from "./hooks/useAuth";

function App() {
  const profile = useAuthStore((s) => s.profile);

  return (
    <BrowserRouter>
      <div id="root">
        <header>
          <nav>
            <Link to="/">Home</Link> | <Link to="/dashboard">Dashboard</Link> | <Link to="/login">Login</Link> | <Link to="/register">Register</Link>
            {profile ? <span style={{ marginLeft: 12 }}>({profile.email})</span> : null}
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<h1>Welcome to Gateway Portal</h1>} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
