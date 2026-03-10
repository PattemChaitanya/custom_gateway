import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Switch,
  FormControlLabel,
} from "@mui/material";
import type { User, UserUpdate } from "../../services/users";

interface UserEditDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  editingUser: User | null;
  formData: UserUpdate;
  onFormDataChange: (data: UserUpdate) => void;
}

const UserEditDialog: React.FC<UserEditDialogProps> = React.memo(
  ({ open, onClose, onSubmit, editingUser, formData, onFormDataChange }) => {
    if (!editingUser) return null;

    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>Edit User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Email"
              type="email"
              fullWidth
              value={formData.email || ""}
              onChange={(e) =>
                onFormDataChange({ ...formData, email: e.target.value })
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active ?? true}
                  onChange={(e) =>
                    onFormDataChange({
                      ...formData,
                      is_active: e.target.checked,
                    })
                  }
                />
              }
              label="Active"
            />

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_superuser ?? false}
                  onChange={(e) =>
                    onFormDataChange({
                      ...formData,
                      is_superuser: e.target.checked,
                    })
                  }
                />
              }
              label="Superuser"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} variant="contained">
            Update
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

UserEditDialog.displayName = "UserEditDialog";

export default UserEditDialog;
