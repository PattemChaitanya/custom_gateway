import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  Typography,
} from "@mui/material";

interface TypeChangeDialogProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  currentType: string;
  pendingType: string;
}

const TypeChangeDialog: React.FC<TypeChangeDialogProps> = React.memo(
  ({ open, onConfirm, onCancel, currentType, pendingType }) => {
    return (
      <Dialog open={open} onClose={onCancel}>
        <DialogTitle>Change API Type?</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Changing from {currentType === "rest" ? "REST" : "GraphQL"} to{" "}
            {pendingType === "rest" ? "REST" : "GraphQL"} will delete all
            existing resources and methods.
          </Alert>
          <Typography>
            Are you sure you want to continue? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={onCancel}>Cancel</Button>
          <Button onClick={onConfirm} variant="contained" color="warning">
            Yes, Change Type
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

TypeChangeDialog.displayName = "TypeChangeDialog";

export default TypeChangeDialog;
