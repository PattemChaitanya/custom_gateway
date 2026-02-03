import { createTheme, type ThemeOptions } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

export const getTheme = (mode: PaletteMode) => {
  const isDark = mode === "dark";

  const themeOptions: ThemeOptions = {
    palette: {
      mode,
      primary: {
        main: isDark ? "#646cff" : "#5a67d8",
        light: isDark ? "#7c84ff" : "#7886d7",
        dark: isDark ? "#4c54cc" : "#4c51bf",
      },
      secondary: {
        main: isDark ? "#f59e0b" : "#ed8936",
      },
      background: {
        default: isDark ? "#0f0f23" : "#f7fafc",
        paper: isDark ? "#1a1a2e" : "#ffffff",
      },
      text: {
        primary: isDark ? "#e2e8f0" : "#1a202c",
        secondary: isDark ? "#a0aec0" : "#718096",
      },
      error: {
        main: isDark ? "#f56565" : "#e53e3e",
      },
      warning: {
        main: isDark ? "#ed8936" : "#dd6b20",
      },
      success: {
        main: isDark ? "#48bb78" : "#38a169",
      },
      info: {
        main: isDark ? "#4299e1" : "#3182ce",
      },
      divider: isDark ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.12)",
    },
    typography: {
      fontFamily: [
        "-apple-system",
        "BlinkMacSystemFont",
        '"Segoe UI"',
        "Roboto",
        '"Helvetica Neue"',
        "Arial",
        "sans-serif",
      ].join(","),
      h1: {
        fontSize: "2.5rem",
        fontWeight: 700,
        lineHeight: 1.2,
      },
      h2: {
        fontSize: "2rem",
        fontWeight: 600,
        lineHeight: 1.3,
      },
      h3: {
        fontSize: "1.75rem",
        fontWeight: 600,
        lineHeight: 1.4,
      },
      h4: {
        fontSize: "1.5rem",
        fontWeight: 600,
        lineHeight: 1.4,
      },
      h5: {
        fontSize: "1.25rem",
        fontWeight: 600,
        lineHeight: 1.5,
      },
      h6: {
        fontSize: "1rem",
        fontWeight: 600,
        lineHeight: 1.6,
      },
      body1: {
        fontSize: "1rem",
        lineHeight: 1.5,
      },
      body2: {
        fontSize: "0.875rem",
        lineHeight: 1.5,
      },
      button: {
        textTransform: "none",
        fontWeight: 500,
      },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            WebkitFontSmoothing: "antialiased",
            MozOsxFontSmoothing: "grayscale",
            scrollbarWidth: "thin",
            scrollbarColor: isDark ? "#4a5568 #2d3748" : "#cbd5e0 #f7fafc",
            "&::-webkit-scrollbar": {
              width: "8px",
              height: "8px",
            },
            "&::-webkit-scrollbar-track": {
              background: isDark ? "#2d3748" : "#f7fafc",
            },
            "&::-webkit-scrollbar-thumb": {
              background: isDark ? "#4a5568" : "#cbd5e0",
              borderRadius: "4px",
              "&:hover": {
                background: isDark ? "#718096" : "#a0aec0",
              },
            },
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            padding: "8px 16px",
            fontSize: "0.875rem",
          },
          contained: {
            boxShadow: "none",
            "&:hover": {
              boxShadow: "none",
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            boxShadow: isDark
              ? "0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px 0 rgba(0, 0, 0, 0.24)"
              : "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
            borderRadius: 12,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderBottom: isDark
              ? "1px solid rgba(255, 255, 255, 0.08)"
              : "1px solid rgba(0, 0, 0, 0.08)",
          },
          head: {
            fontWeight: 600,
            backgroundColor: isDark ? "#16213e" : "#f7fafc",
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 6,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-root": {
              borderRadius: 8,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
    },
  };

  return createTheme(themeOptions);
};

// Default theme (dark mode)
const theme = getTheme("dark");

export default theme;
