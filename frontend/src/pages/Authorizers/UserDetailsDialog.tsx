import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
} from "@mui/material";
import type { UserWithRoles } from "../../services/users";

interface UserDetailsDialogProps {
  open: boolean;
  onClose: () => void;
  user: UserWithRoles | null;
}

const UserDetailsDialog: React.FC<UserDetailsDialogProps> = React.memo(
  ({ open, onClose, user }) => {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>User Details</DialogTitle>
        <DialogContent>
          {user && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="h6" gutterBottom>
                {user.email}
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Typography>
                  {user.is_active ? "Active" : "Inactive"}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Superuser
                </Typography>
                <Typography>{user.is_superuser ? "Yes" : "No"}</Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Roles
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  {user.roles.length > 0 ? (
                    user.roles.map((role, idx) => (
                      <Chip key={idx} label={role} color="primary" />
                    ))
                  ) : (
                    <Typography color="text.secondary">No roles</Typography>
                  )}
                </Box>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Permissions
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  {user.permissions.length > 0 ? (
                    user.permissions.map((perm, idx) => (
                      <Chip
                        key={idx}
                        label={perm}
                        size="small"
                        variant="outlined"
                      />
                    ))
                  ) : (
                    <Typography color="text.secondary">
                      No permissions
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  },
);

UserDetailsDialog.displayName = "UserDetailsDialog";

export default UserDetailsDialog;
