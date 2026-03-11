import { Link } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { logout } from "../services/auth";
import { useState } from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Divider from "@mui/material/Divider";
import NotificationsIcon from "@mui/icons-material/Notifications";
import MenuIcon from "@mui/icons-material/Menu";
import { ThemeToggle } from "./ThemeToggle";
import usePermissions from "../hooks/usePermissions";
import Chip from "@mui/material/Chip";

const NAV_LINKS = [
  { label: "APIs", to: "/apis" },
  { label: "API Keys", to: "/api-keys" },
  { label: "Secrets", to: "/secrets" },
  { label: "Connectors", to: "/connectors" },
  { label: "Authorizers", to: "/authorizers" },
  { label: "Audit Logs", to: "/audit-logs" },
] as const;

export default function Header() {
  const profile = useAuthStore((s) => s.profile);
  const { isSuperuser } = usePermissions();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleOpen = (e: React.MouseEvent<HTMLElement>) =>
    setAnchorEl(e.currentTarget);
  const handleClose = () => setAnchorEl(null);

  return (
    <>
      <AppBar position="fixed" color="primary" elevation={1}>
        <Toolbar
          sx={{
            maxWidth: { xs: "100%", xl: 1400 },
            margin: "0 auto",
            width: "100%",
            px: { xs: 1, sm: 2 },
          }}
        >
          <Box
            sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}
          >
            {/* Hamburger — visible only on xs */}
            <IconButton
              color="inherit"
              aria-label="open navigation menu"
              edge="start"
              onClick={() => setDrawerOpen(true)}
              sx={{ display: { xs: "inline-flex", sm: "none" } }}
            >
              <MenuIcon />
            </IconButton>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  bgcolor: "secondary.main",
                  borderRadius: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                }}
              >
                ▢▤
              </Box>
              <Typography variant="h6" component="div" noWrap>
                API Gateway
              </Typography>
            </Box>

            {/* Desktop nav links */}
            <Box sx={{ ml: 2, display: { xs: "none", sm: "flex" }, gap: 1 }}>
              {NAV_LINKS.map((link) => (
                <Button
                  key={link.to}
                  color="inherit"
                  component={Link}
                  to={link.to}
                >
                  {link.label}
                </Button>
              ))}
            </Box>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography
              variant="body2"
              sx={{ opacity: 0.85, display: { xs: "none", md: "block" } }}
            >
              http://localhost
            </Typography>
            <ThemeToggle />
            <IconButton color="inherit" aria-label="notifications">
              <NotificationsIcon />
            </IconButton>

            <IconButton
              color="inherit"
              onClick={handleOpen}
              size="small"
              aria-label="user menu"
              sx={{ ml: 1 }}
            >
              <Avatar sx={{ width: 32, height: 32 }}>
                {profile && (profile.email ?? "")
                  ? (profile.email as string)[0].toUpperCase()
                  : "U"}
              </Avatar>
            </IconButton>

            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleClose}
              anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
              transformOrigin={{ vertical: "top", horizontal: "right" }}
            >
              <Box
                sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider" }}
              >
                <Typography variant="body2" fontWeight="bold">
                  {profile?.email}
                </Typography>
                {isSuperuser && (
                  <Chip
                    label="Superuser"
                    size="small"
                    color="error"
                    sx={{ mt: 0.5 }}
                  />
                )}
                {profile?.roles && profile.roles.length > 0 && (
                  <Box
                    sx={{
                      mt: 1,
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 0.5,
                    }}
                  >
                    {profile.roles.map((role, idx) => (
                      <Chip
                        key={idx}
                        label={role}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                )}
              </Box>
              <MenuItem onClick={handleClose} component={Link} to="/dashboard">
                Dashboard
              </MenuItem>
              <MenuItem
                onClick={handleClose}
                component={Link}
                to="/environments"
              >
                Environments
              </MenuItem>
              <MenuItem onClick={handleClose}>My account</MenuItem>
              <MenuItem
                onClick={async () => {
                  try {
                    await logout();
                    window.location.href = "/";
                  } catch (_) {}
                }}
              >
                Logout
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Mobile navigation drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          display: { xs: "block", sm: "none" },
          "& .MuiDrawer-paper": { width: 260 },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" fontWeight={700}>
            API Gateway
          </Typography>
        </Box>
        <Divider />
        <List>
          {NAV_LINKS.map((link) => (
            <ListItem key={link.to} disablePadding>
              <ListItemButton
                component={Link}
                to={link.to}
                onClick={() => setDrawerOpen(false)}
              >
                <ListItemText primary={link.label} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Divider />
        <List>
          <ListItem disablePadding>
            <ListItemButton
              component={Link}
              to="/dashboard"
              onClick={() => setDrawerOpen(false)}
            >
              <ListItemText primary="Dashboard" />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton
              component={Link}
              to="/environments"
              onClick={() => setDrawerOpen(false)}
            >
              <ListItemText primary="Environments" />
            </ListItemButton>
          </ListItem>
        </List>
      </Drawer>
    </>
  );
}
