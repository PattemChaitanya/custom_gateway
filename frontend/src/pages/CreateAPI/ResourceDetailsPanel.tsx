import React from "react";
import {
  Box,
  Typography,
  Button,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Paper,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from "@mui/icons-material";

export type Method = {
  type: string;
  authorization: string;
  apiKeyRequired: boolean;
  requestValidator?: string;
  integrationType: string;
  integrationUrl?: string;
  operationName?: string;
};

export type Resource = {
  id: string;
  path: string;
  pathPart: string;
  parentId: string | null;
  methods: Method[];
  children?: Resource[];
};

interface ResourceDetailsPanelProps {
  selectedResource: Resource | null;
  apiType: string;
  onOpenResourceDialog: () => void;
  onOpenMethodDialog: () => void;
  onEditMethod: (method: Method, index: number) => void;
  onDeleteMethod: (resource: Resource, index: number) => void;
}

const ResourceDetailsPanel: React.FC<ResourceDetailsPanelProps> = React.memo(
  ({
    selectedResource,
    apiType,
    onOpenResourceDialog,
    onOpenMethodDialog,
    onEditMethod,
    onDeleteMethod,
  }) => {
    if (!selectedResource) {
      return (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Typography color="text.secondary">
              Select a resource to view details
            </Typography>
          </Box>
        </Paper>
      );
    }

    return (
      <Paper sx={{ p: 2 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Box>
            <Typography variant="h6">Resource details</Typography>
            <Typography variant="body2" color="text.secondary">
              Path: {selectedResource.path}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Resource ID: {selectedResource.id}
            </Typography>
          </Box>
          <Box>
            <Button
              variant="outlined"
              size="small"
              sx={{ mr: 1 }}
              onClick={onOpenResourceDialog}
            >
              Delete
            </Button>
            <Button
              variant="contained"
              color="primary"
              size="small"
              onClick={onOpenMethodDialog}
            >
              Create method
            </Button>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1,
            }}
          >
            <Typography variant="subtitle1">
              Methods ({selectedResource.methods.length})
            </Typography>
          </Box>

          {selectedResource.methods.length === 0 ? (
            <Box
              sx={{
                textAlign: "center",
                py: 4,
                bgcolor: "background.default",
                borderRadius: 1,
              }}
            >
              <Typography color="text.secondary">No methods</Typography>
              <Typography variant="body2" color="text.secondary">
                No methods defined.
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={onOpenMethodDialog}
                sx={{ mt: 2 }}
              >
                Create method
              </Button>
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Method type</TableCell>
                    {apiType === "rest" ? (
                      <>
                        <TableCell>Integration type</TableCell>
                        <TableCell>Authorization</TableCell>
                        <TableCell>API key</TableCell>
                      </>
                    ) : (
                      <>
                        <TableCell>Operation name</TableCell>
                        <TableCell>Resolver URL</TableCell>
                      </>
                    )}
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {selectedResource.methods.map((method, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Chip
                          label={method.type}
                          color={apiType === "rest" ? "primary" : "secondary"}
                          size="small"
                        />
                      </TableCell>
                      {apiType === "rest" ? (
                        <>
                          <TableCell>{method.integrationType}</TableCell>
                          <TableCell>{method.authorization}</TableCell>
                          <TableCell>
                            {method.apiKeyRequired
                              ? "Required"
                              : "Not required"}
                          </TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell>{method.operationName || "—"}</TableCell>
                          <TableCell>
                            <Typography
                              variant="body2"
                              sx={{
                                maxWidth: 200,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                              }}
                            >
                              {method.integrationUrl || "—"}
                            </Typography>
                          </TableCell>
                        </>
                      )}
                      <TableCell>
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => onEditMethod(method, index)}
                          sx={{ mr: 0.5 }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() =>
                            onDeleteMethod(selectedResource, index)
                          }
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      </Paper>
    );
  },
);

ResourceDetailsPanel.displayName = "ResourceDetailsPanel";

export default ResourceDetailsPanel;
