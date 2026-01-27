import { BrowserRouter, Link } from "react-router-dom";
import "./App.css";
import useAuthStore from "./hooks/useAuth";
import AppRoutes from "./AppRoutes";

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
          <AppRoutes />
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
