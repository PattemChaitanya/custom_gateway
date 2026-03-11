import { BrowserRouter } from "react-router-dom";
import "./App.css";
import AppRoutes from "./AppRoutes";
import { ThemeProvider } from "./contexts/ThemeContext";

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <a
          href="#main-content"
          style={{
            position: "absolute",
            left: "-9999px",
            top: "auto",
            width: "1px",
            height: "1px",
            overflow: "hidden",
          }}
          onFocus={(e) => {
            e.currentTarget.style.position = "fixed";
            e.currentTarget.style.top = "0";
            e.currentTarget.style.left = "0";
            e.currentTarget.style.width = "auto";
            e.currentTarget.style.height = "auto";
            e.currentTarget.style.overflow = "visible";
            e.currentTarget.style.zIndex = "9999";
            e.currentTarget.style.padding = "8px 16px";
            e.currentTarget.style.background = "#646cff";
            e.currentTarget.style.color = "#fff";
          }}
          onBlur={(e) => {
            e.currentTarget.style.position = "absolute";
            e.currentTarget.style.left = "-9999px";
            e.currentTarget.style.width = "1px";
            e.currentTarget.style.height = "1px";
            e.currentTarget.style.overflow = "hidden";
          }}
        >
          Skip to content
        </a>
        <main id="main-content">
          <AppRoutes />
        </main>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
