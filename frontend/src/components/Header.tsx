import { Link } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import { logout } from "../services/auth";
import { useState } from "react";
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import NotificationsIcon from '@mui/icons-material/Notifications';

export default function Header() {
    const profile = useAuthStore((s) => s.profile);
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

    const handleOpen = (e: React.MouseEvent<HTMLElement>) => setAnchorEl(e.currentTarget);
    const handleClose = () => setAnchorEl(null);

    return (
        <AppBar position="fixed" color="primary" elevation={1}>
            <Toolbar sx={{ maxWidth: 1200, margin: '0 auto', width: '100%', px: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box sx={{ width: 36, height: 36, bgcolor: 'secondary.main', borderRadius: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>▢▤</Box>
                        <Typography variant="h6" component="div">API Management</Typography>
                    </Box>

                    <Box sx={{ ml: 2, display: { xs: 'none', sm: 'flex' }, gap: 1 }}>
                        <Button color="inherit" component={Link} to="/apis">APIs</Button>
                        <Button color="inherit" component={Link} to="/authorizers">Authorizers</Button>
                        <Button color="inherit" component={Link} to="/connectors">Connectors</Button>
                        <Button color="inherit" component={Link} to="/monitoring">Monitoring</Button>
                    </Box>
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" sx={{ opacity: 0.85 }}>http://localhost</Typography>
                    <IconButton color="inherit" aria-label="notifications">
                        <NotificationsIcon />
                    </IconButton>

                    <IconButton color="inherit" onClick={handleOpen} size="small" sx={{ ml: 1 }}>
                        <Avatar sx={{ width: 32, height: 32 }}>{profile && (profile.email ?? '') ? (profile.email as string)[0].toUpperCase() : 'U'}</Avatar>
                    </IconButton>

                    <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }} transformOrigin={{ vertical: 'top', horizontal: 'right' }}>
                        <MenuItem onClick={handleClose}>Profile</MenuItem>
                        <MenuItem onClick={handleClose}>My account</MenuItem>
                        <MenuItem onClick={async () => { try { await logout(); window.location.href = '/'; } catch (_) { } }}>
                            Logout
                        </MenuItem>
                    </Menu>
                </Box>
            </Toolbar>
        </AppBar>
    );
}
