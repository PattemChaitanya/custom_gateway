import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Chip,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import type {
  CreateRoleRequest,
  Role,
  Permission,
} from "../../services/authorizers";

interface RoleDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  editingRole: Role | null;
  formData: CreateRoleRequest;
  onFormDataChange: (data: CreateRoleRequest) => void;
  permissions: Permission[];
}

const RoleDialog: React.FC<RoleDialogProps> = React.memo(
  ({
    open,
    onClose,
    onSubmit,
    editingRole,
    formData,
    onFormDataChange,
    permissions,
  }) => {
    const handlePermissionsChange = (event: SelectChangeEvent<string[]>) => {
      const {
        target: { value },
      } = event;
      onFormDataChange({
        ...formData,
        permissions: typeof value === "string" ? value.split(",") : value,
      });
    };

    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>{editingRole ? "Edit Role" : "Create Role"}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Name"
              fullWidth
              value={formData.name}
              onChange={(e) =>
                onFormDataChange({ ...formData, name: e.target.value })
              }
              required
            />

            <TextField
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={formData.description}
              onChange={(e) =>
                onFormDataChange({ ...formData, description: e.target.value })
              }
            />

            <FormControl fullWidth>
              <InputLabel>Permissions</InputLabel>
              <Select
                multiple
                value={formData.permissions || []}
                onChange={handlePermissionsChange}
                input={<OutlinedInput label="Permissions" />}
                renderValue={(selected) => (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {permissions.map((permission) => (
                  <MenuItem key={permission.id} value={permission.name}>
                    {permission.name} ({permission.resource}:{permission.action}
                    )
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} variant="contained">
            {editingRole ? "Update" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

RoleDialog.displayName = "RoleDialog";

export default RoleDialog;
