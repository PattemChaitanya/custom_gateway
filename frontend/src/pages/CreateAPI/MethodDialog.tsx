import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Select,
  MenuItem,
  Stack,
  FormControlLabel,
  Checkbox,
  Alert,
} from "@mui/material";

export type Method = {
  type: string;
  authorization: string;
  apiKeyRequired: boolean;
  requestValidator?: string;
  integrationType: string;
  integrationUrl?: string;
  operationName?: string;
};

interface MethodDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: () => void;
  apiType: string;
  method: Method;
  onMethodChange: (method: Method) => void;
  editingMethodIndex: number | null;
  validationError: string | null;
}

const MethodDialog: React.FC<MethodDialogProps> = React.memo(
  ({
    open,
    onClose,
    onSubmit,
    apiType,
    method,
    onMethodChange,
    editingMethodIndex,
    validationError,
  }) => {
    const handleClose = () => {
      onClose();
    };

    return (
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingMethodIndex !== null ? "Edit method" : "Create method"}
        </DialogTitle>
        <DialogContent>
          {validationError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {validationError}
            </Alert>
          )}
          <Stack spacing={2} sx={{ mt: 1 }}>
            {apiType === "rest" ? (
              <Select
                value={method.type}
                onChange={(e) =>
                  onMethodChange({ ...method, type: e.target.value })
                }
                fullWidth
              >
                <MenuItem value="GET">GET</MenuItem>
                <MenuItem value="POST">POST</MenuItem>
                <MenuItem value="PUT">PUT</MenuItem>
                <MenuItem value="PATCH">PATCH</MenuItem>
                <MenuItem value="DELETE">DELETE</MenuItem>
                <MenuItem value="ANY">ANY</MenuItem>
              </Select>
            ) : (
              <Select
                value={method.type}
                onChange={(e) =>
                  onMethodChange({ ...method, type: e.target.value })
                }
                fullWidth
              >
                <MenuItem value="QUERY">Query</MenuItem>
                <MenuItem value="MUTATION">Mutation</MenuItem>
                <MenuItem value="SUBSCRIPTION">Subscription</MenuItem>
              </Select>
            )}

            {apiType === "graphql" ? (
              <>
                <TextField
                  label="Operation Name (required)"
                  value={method.operationName}
                  onChange={(e) =>
                    onMethodChange({
                      ...method,
                      operationName: e.target.value,
                    })
                  }
                  fullWidth
                  required
                  helperText="e.g., getUser, createPost, subscribeToMessages"
                />

                <TextField
                  label="Resolver URL"
                  value={method.integrationUrl}
                  onChange={(e) =>
                    onMethodChange({
                      ...method,
                      integrationUrl: e.target.value,
                    })
                  }
                  fullWidth
                  helperText="Backend resolver endpoint"
                />

                <TextField
                  label="Schema Definition (optional)"
                  multiline
                  rows={4}
                  value={method.requestValidator}
                  onChange={(e) =>
                    onMethodChange({
                      ...method,
                      requestValidator: e.target.value,
                    })
                  }
                  fullWidth
                  placeholder="type Query {\n  getUser(id: ID!): User\n}"
                  sx={{ fontFamily: "monospace" }}
                />
              </>
            ) : (
              <>
                <Select
                  value={method.authorization}
                  onChange={(e) =>
                    onMethodChange({
                      ...method,
                      authorization: e.target.value,
                    })
                  }
                  fullWidth
                  displayEmpty
                >
                  <MenuItem value="NONE">None</MenuItem>
                  <MenuItem value="API_KEY">API Key</MenuItem>
                  <MenuItem value="JWT">JWT</MenuItem>
                  <MenuItem value="IAM">AWS IAM</MenuItem>
                  <MenuItem value="COGNITO">Cognito</MenuItem>
                </Select>

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={method.apiKeyRequired}
                      onChange={(e) =>
                        onMethodChange({
                          ...method,
                          apiKeyRequired: e.target.checked,
                        })
                      }
                    />
                  }
                  label="API key required"
                />

                <Select
                  value={method.integrationType}
                  onChange={(e) =>
                    onMethodChange({
                      ...method,
                      integrationType: e.target.value,
                    })
                  }
                  fullWidth
                >
                  <MenuItem value="HTTP">HTTP</MenuItem>
                  <MenuItem value="LAMBDA">AWS Lambda</MenuItem>
                  <MenuItem value="MOCK">Mock</MenuItem>
                </Select>

                {method.integrationType === "HTTP" && (
                  <TextField
                    label="Integration URL"
                    value={method.integrationUrl}
                    onChange={(e) =>
                      onMethodChange({
                        ...method,
                        integrationUrl: e.target.value,
                      })
                    }
                    fullWidth
                  />
                )}

                <TextField
                  label="Operation name (optional)"
                  value={method.operationName}
                  onChange={(e) =>
                    onMethodChange({
                      ...method,
                      operationName: e.target.value,
                    })
                  }
                  fullWidth
                />
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={onSubmit} variant="contained">
            {editingMethodIndex !== null ? "Update" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    );
  },
);

MethodDialog.displayName = "MethodDialog";

export default MethodDialog;
