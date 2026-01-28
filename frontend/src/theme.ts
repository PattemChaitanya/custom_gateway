import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#646cff',
    },
    background: {
      default: '#242424',
      paper: '#1f1f1f',
    },
  },
  typography: {
    fontFamily: ['system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'].join(','),
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale',
        },
      },
    },
  },
});

export default theme;
