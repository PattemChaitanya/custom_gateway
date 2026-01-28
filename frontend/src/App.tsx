import { BrowserRouter } from "react-router-dom";
import "./App.css";
import useAuthStore from "./hooks/useAuth";
import AppRoutes from "./AppRoutes";
import { useEffect } from "react";
import { me } from "./services/auth";

function App() {
  const setProfile = useAuthStore((s) => s.setProfile);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const js = await me();
        if (mounted) setProfile(js);
      } catch (_) {
        // ignore - user remains unauthenticated
      }
    })();
    return () => {
      mounted = false;
    };
  }, [setProfile]);

  return (
    <BrowserRouter>
      <div id="root">
        <main>
          <AppRoutes />
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
