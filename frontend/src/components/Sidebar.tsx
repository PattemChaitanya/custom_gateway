import { Link, useLocation } from "react-router-dom";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Toolbar from "@mui/material/Toolbar";
import Divider from "@mui/material/Divider";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ApiIcon from "@mui/icons-material/Api";
import KeyIcon from "@mui/icons-material/Key";
import LockIcon from "@mui/icons-material/Lock";
import StorageIcon from "@mui/icons-material/Storage";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import ListAltIcon from "@mui/icons-material/ListAlt";
import CloudIcon from "@mui/icons-material/Cloud";
import PeopleIcon from "@mui/icons-material/People";
import usePermissions from "../hooks/usePermissions";

export const SIDEBAR_WIDTH = 220;

const NAV_ITEMS = [
  {
    label: "Dashboard",
    to: "/dashboard",
    icon: <DashboardIcon fontSize="small" />,
  },
  { label: "APIs", to: "/apis", icon: <ApiIcon fontSize="small" /> },
  { label: "API Keys", to: "/api-keys", icon: <KeyIcon fontSize="small" /> },
  { label: "Secrets", to: "/secrets", icon: <LockIcon fontSize="small" /> },
  {
    label: "Environments",
    to: "/environments",
    icon: <StorageIcon fontSize="small" />,
  },
  {
    label: "Connectors",
    to: "/connectors",
    icon: <AccountTreeIcon fontSize="small" />,
  },
  {
    label: "Authorizers",
    to: "/authorizers",
    icon: <VerifiedUserIcon fontSize="small" />,
  },
  {
    label: "Audit Logs",
    to: "/audit-logs",
    icon: <ListAltIcon fontSize="small" />,
  },
  {
    label: "Mini-Cloud",
    to: "/mini-cloud",
    icon: <CloudIcon fontSize="small" />,
  },
];

const ADMIN_ITEMS = [
  { label: "Users", to: "/users", icon: <PeopleIcon fontSize="small" /> },
];

export default function Sidebar() {
  const { isSuperuser } = usePermissions();
  const location = useLocation();

  const isActive = (to: string) =>
    location.pathname === to ||
    (to !== "/dashboard" && location.pathname.startsWith(to + "/"));

  const drawer = (
    <>
      <Toolbar /> {/* spacer for fixed AppBar */}
      <Divider />
      <List dense disablePadding>
        {NAV_ITEMS.map((item) => (
          <ListItem key={item.to} disablePadding>
            <ListItemButton
              component={Link}
              to={item.to}
              selected={isActive(item.to)}
              sx={{
                py: 0.75,
                "&.Mui-selected": { bgcolor: "action.selected" },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{ fontSize: 14 }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      {isSuperuser && (
        <>
          <Divider />
          <List dense disablePadding>
            {ADMIN_ITEMS.map((item) => (
              <ListItem key={item.to} disablePadding>
                <ListItemButton
                  component={Link}
                  to={item.to}
                  selected={isActive(item.to)}
                  sx={{
                    py: 0.75,
                    "&.Mui-selected": { bgcolor: "action.selected" },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{ fontSize: 14 }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </>
      )}
    </>
  );

  return (
    <Drawer
      variant="permanent"
      sx={{
        display: { xs: "none", md: "block" },
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: SIDEBAR_WIDTH,
          boxSizing: "border-box",
          borderRight: "1px solid",
          borderColor: "divider",
        },
      }}
    >
      {drawer}
    </Drawer>
  );
}
