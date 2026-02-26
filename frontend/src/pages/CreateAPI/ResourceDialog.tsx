import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from "@mui/material";

interface ResourceDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  newResourcePath: string;
  onPathChange: (value: string) => void;
  selectedResourcePath?: string;
}

const ResourceDialog: React.FC<ResourceDialogProps> = React.memo(
  ({
    open,
    onClose,
    onSubmit,
    newResourcePath,
    onPathChange,
    selectedResourcePath,
  }) => {
    return (
      <Dialog open={open} onClose={onClose}>
        <DialogTitle>Create resource</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Resource path part (e.g., users, {id}, orders)"
            fullWidth
            value={newResourcePath}
            onChange={(e) => onPathChange(e.target.value)}
            helperText={`Full path will be: ${selectedResourcePath === "/" ? "" : selectedResourcePath}/${newResourcePath}`}
          />
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

ResourceDialog.displayName = "ResourceDialog";

export default ResourceDialog;
