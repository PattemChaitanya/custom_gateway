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
} from "@mui/material";
import type { CreatePermissionRequest } from "../../services/authorizers";

const ACTIONS = ["create", "read", "update", "delete", "execute", "list"];
const RESOURCES = [
  "api",
  "user",
  "key",
  "secret",
  "connector",
  "role",
  "permission",
];

interface PermissionDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  formData: CreatePermissionRequest;
  onFormDataChange: (data: CreatePermissionRequest) => void;
}

const PermissionDialog: React.FC<PermissionDialogProps> = React.memo(
  ({ open, onClose, onSubmit, formData, onFormDataChange }) => {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>Create Permission</DialogTitle>
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
              placeholder="e.g., api:create"
            />

            <FormControl fullWidth required>
              <InputLabel>Resource</InputLabel>
              <Select
                value={formData.resource}
                onChange={(e) =>
                  onFormDataChange({ ...formData, resource: e.target.value })
                }
                label="Resource"
              >
                {RESOURCES.map((resource) => (
                  <MenuItem key={resource} value={resource}>
                    {resource}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth required>
              <InputLabel>Action</InputLabel>
              <Select
                value={formData.action}
                onChange={(e) =>
                  onFormDataChange({ ...formData, action: e.target.value })
                }
                label="Action"
              >
                {ACTIONS.map((action) => (
                  <MenuItem key={action} value={action}>
                    {action}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

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
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={onSubmit} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

PermissionDialog.displayName = "PermissionDialog";

export default PermissionDialog;
