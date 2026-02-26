import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
} from "@mui/material";

interface ConfirmDeleteDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  message: string;
}

const ConfirmDeleteDialog: React.FC<ConfirmDeleteDialogProps> = React.memo(
  ({ open, onClose, onConfirm, message }) => {
    return (
      <Dialog open={open} onClose={onClose}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>{message}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={onConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

ConfirmDeleteDialog.displayName = "ConfirmDeleteDialog";

export default ConfirmDeleteDialog;
