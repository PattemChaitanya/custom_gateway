import { BrowserRouter } from "react-router-dom";
import "./App.css";
import useAuthStore from "./hooks/useAuth";
import AppRoutes from "./AppRoutes";
import { useEffect } from "react";
import { me } from "./services/auth";
import { ThemeProvider } from "./contexts/ThemeContext";

function App() {
  const setProfile = useAuthStore((s) => s.setProfile);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const userInfo = await me();
        if (mounted) {
          // Store user profile with roles and permissions from /auth/me
          setProfile({
            id: userInfo.id,
            email: userInfo.email,
            is_active: userInfo.is_active,
            is_superuser: userInfo.is_superuser,
            roles: userInfo.roles || [],
            permissions: userInfo.permissions || [],
          });
        }
      } catch (_) {
        // ignore - user remains unauthenticated
      }
    })();
    return () => {
      mounted = false;
    };
  }, [setProfile]);

  return (
    <ThemeProvider>
      <BrowserRouter>
        <div id="root">
          <main>
            <AppRoutes />
          </main>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
