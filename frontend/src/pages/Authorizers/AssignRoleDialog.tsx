import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import type { Role } from "../../services/authorizers";

interface AssignRoleDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  roles: Role[];
  selectedRoleId: number | string;
  onSelectedRoleIdChange: (id: number | string) => void;
}

const AssignRoleDialog: React.FC<AssignRoleDialogProps> = React.memo(
  ({
    open,
    onClose,
    onSubmit,
    roles,
    selectedRoleId,
    onSelectedRoleIdChange,
  }) => {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>Assign Role to User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Select Role</InputLabel>
              <Select
                value={selectedRoleId}
                onChange={(e) => onSelectedRoleIdChange(e.target.value)}
                label="Select Role"
              >
                {roles.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    {role.name} - {role.description}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} variant="contained">
            Assign
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

AssignRoleDialog.displayName = "AssignRoleDialog";

export default AssignRoleDialog;
