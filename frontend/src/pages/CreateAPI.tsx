import { useState, useEffect, useCallback } from "react";
import {
  Container,
  Typography,
  TextField,
  Button,
  RadioGroup,
  FormControlLabel,
  Radio,
  Box,
  Alert,
  Stack,
  Paper,
  IconButton,
  Select,
  MenuItem,
  Chip,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Collapse,
  Grid,
} from "@mui/material";
import {
  Add as AddIcon,
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
} from "@mui/icons-material";
import { createAPI, getAPI, updateAPI } from "../services/apis";
import { useNavigate, useParams } from "react-router-dom";
import ResourceDialog from "./CreateAPI/ResourceDialog";
import MethodDialog from "./CreateAPI/MethodDialog";
import TypeChangeDialog from "./CreateAPI/TypeChangeDialog";
import ResourceDetailsPanel from "./CreateAPI/ResourceDetailsPanel";

type Method = {
  type: string;
  authorization: string;
  apiKeyRequired: boolean;
  requestValidator?: string;
  integrationType: string;
  integrationUrl?: string;
  operationName?: string;
};

type Resource = {
  id: string;
  path: string;
  pathPart: string;
  parentId: string | null;
  methods: Method[];
  children?: Resource[];
};

export default function CreateAPI() {
  const params = useParams();
  const editId = params.id ? Number(params.id) : null;

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [type, setType] = useState("rest");

  const [resources, setResources] = useState<Resource[]>([
    {
      id: "root",
      path: "/",
      pathPart: "/",
      parentId: null,
      methods: [],
      children: [],
    },
  ]);

  const [selectedResource, setSelectedResource] = useState<Resource | null>(
    null,
  );
  const [expandedResources, setExpandedResources] = useState<Set<string>>(
    new Set(["root"]),
  );

  const [resourceDialogOpen, setResourceDialogOpen] = useState(false);
  const [methodDialogOpen, setMethodDialogOpen] = useState(false);
  const [typeChangeDialogOpen, setTypeChangeDialogOpen] = useState(false);
  const [editingMethodIndex, setEditingMethodIndex] = useState<number | null>(
    null,
  );
  const [pendingType, setPendingType] = useState<string>("");
  const [newResourcePath, setNewResourcePath] = useState("");
  const [newMethod, setNewMethod] = useState<Method>({
    type: "GET",
    authorization: "NONE",
    apiKeyRequired: false,
    integrationType: "HTTP",
    integrationUrl: "",
    operationName: "",
  });

  const [success, setSuccess] = useState<{ id?: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const navigate = useNavigate();

  const generateId = () =>
    `res-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const buildResourceTree = (flatResources: Resource[]): Resource[] => {
    const map = new Map<string, Resource>();
    const roots: Resource[] = [];

    flatResources.forEach((r) => {
      map.set(r.id, { ...r, children: [] });
    });

    flatResources.forEach((r) => {
      const resource = map.get(r.id)!;
      if (r.parentId && map.has(r.parentId)) {
        map.get(r.parentId)!.children!.push(resource);
      } else {
        roots.push(resource);
      }
    });

    return roots;
  };

  const flattenResources = (resources: Resource[]): Resource[] => {
    const result: Resource[] = [];
    const traverse = (res: Resource[]) => {
      res.forEach((r) => {
        const { children, ...rest } = r;
        result.push(rest as Resource);
        if (children && children.length > 0) {
          traverse(children);
        }
      });
    };
    traverse(resources);
    return result;
  };

  const findResourceById = (
    resources: Resource[],
    id: string,
  ): Resource | null => {
    for (const resource of resources) {
      if (resource.id === id) return resource;
      if (resource.children && resource.children.length > 0) {
        const found = findResourceById(resource.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const addResource = () => {
    if (!newResourcePath.trim() || !selectedResource) return;

    const pathPart = newResourcePath.startsWith("/")
      ? newResourcePath
      : `/${newResourcePath}`;
    const fullPath =
      selectedResource.path === "/"
        ? pathPart
        : `${selectedResource.path}${pathPart}`;

    const newResource: Resource = {
      id: generateId(),
      path: fullPath,
      pathPart,
      parentId: selectedResource.id,
      methods: [],
      children: [],
    };

    const updateChildren = (res: Resource[]): Resource[] => {
      return res.map((r) => {
        if (r.id === selectedResource.id) {
          return {
            ...r,
            children: [...(r.children || []), newResource],
          };
        }
        if (r.children && r.children.length > 0) {
          return {
            ...r,
            children: updateChildren(r.children),
          };
        }
        return r;
      });
    };

    setResources(updateChildren(resources));
    setExpandedResources((prev) => new Set([...prev, selectedResource.id]));
    setNewResourcePath("");
    setResourceDialogOpen(false);
  };

  const addMethod = () => {
    if (!selectedResource) return;

    // Validate duplicate methods
    const methodExists = selectedResource.methods.some((m, idx) => {
      // When editing, skip the method being edited
      if (editingMethodIndex !== null && idx === editingMethodIndex)
        return false;
      return m.type === newMethod.type;
    });

    if (methodExists) {
      setValidationError(
        `Method ${newMethod.type} already exists for this resource`,
      );
      return;
    }

    const updateMethods = (res: Resource[]): Resource[] => {
      return res.map((r) => {
        if (r.id === selectedResource.id) {
          // If editing, replace the method at the index
          if (editingMethodIndex !== null) {
            const updatedMethods = [...r.methods];
            updatedMethods[editingMethodIndex] = { ...newMethod };
            return {
              ...r,
              methods: updatedMethods,
            };
          }
          // Otherwise, add new method
          return {
            ...r,
            methods: [...r.methods, { ...newMethod }],
          };
        }
        if (r.children && r.children.length > 0) {
          return {
            ...r,
            children: updateMethods(r.children),
          };
        }
        return r;
      });
    };

    const updatedResources = updateMethods(resources);
    setResources(updatedResources);

    // Update selectedResource to reflect the new method
    if (selectedResource) {
      const updated = findResourceById(updatedResources, selectedResource.id);
      if (updated) setSelectedResource(updated);
    }

    setValidationError(null);
    setEditingMethodIndex(null);
    setMethodDialogOpen(false);
    setNewMethod({
      type: type === "rest" ? "GET" : "QUERY",
      authorization: "NONE",
      apiKeyRequired: false,
      integrationType: "HTTP",
      integrationUrl: "",
      operationName: "",
    });
  };

  const deleteMethod = (resource: Resource, methodIndex: number) => {
    const updateMethods = (res: Resource[]): Resource[] => {
      return res.map((r) => {
        if (r.id === resource.id) {
          return {
            ...r,
            methods: r.methods.filter((_, i) => i !== methodIndex),
          };
        }
        if (r.children && r.children.length > 0) {
          return {
            ...r,
            children: updateMethods(r.children),
          };
        }
        return r;
      });
    };

    const updatedResources = updateMethods(resources);
    setResources(updatedResources);

    // Update selectedResource to reflect the deleted method
    if (resource && resource.id === selectedResource?.id) {
      const updated = findResourceById(updatedResources, resource.id);
      if (updated) setSelectedResource(updated);
    }
  };

  const handleTypeChange = (newType: string) => {
    // Check if there are any resources with methods
    const hasMethodsInResources = flattenResources(resources).some(
      (r) => r.methods.length > 0,
    );

    if (hasMethodsInResources && newType !== type) {
      // Show warning dialog
      setPendingType(newType);
      setTypeChangeDialogOpen(true);
    } else {
      setType(newType);
    }
  };

  const confirmTypeChange = () => {
    // Clear all resources and reset to root
    setResources([
      {
        id: "root",
        path: "/",
        pathPart: "/",
        parentId: null,
        methods: [],
        children: [],
      },
    ]);
    setSelectedResource(null);
    setType(pendingType);
    setTypeChangeDialogOpen(false);
    setPendingType("");
  };

  const cancelTypeChange = () => {
    setTypeChangeDialogOpen(false);
    setPendingType("");
  };

  const openMethodDialog = useCallback(() => {
    setValidationError(null);
    setEditingMethodIndex(null);
    setNewMethod({
      type: type === "rest" ? "GET" : "QUERY",
      authorization: "NONE",
      apiKeyRequired: false,
      integrationType: type === "rest" ? "HTTP" : "LAMBDA",
      integrationUrl: "",
      operationName: "",
    });
    setMethodDialogOpen(true);
  }, [type]);

  const openEditMethodDialog = useCallback((method: Method, index: number) => {
    setValidationError(null);
    setEditingMethodIndex(index);
    setNewMethod({ ...method });
    setMethodDialogOpen(true);
  }, []);

  const handleCloseMethodDialog = useCallback(() => {
    setMethodDialogOpen(false);
    setValidationError(null);
    setEditingMethodIndex(null);
  }, []);

  const handleOpenResourceDialog = useCallback(() => {
    setResourceDialogOpen(true);
  }, []);

  const handleCloseResourceDialog = useCallback(() => {
    setResourceDialogOpen(false);
  }, []);

  async function handleCreate(e?: React.FormEvent) {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const now = new Date().toISOString();

      const flatResources = flattenResources(resources);
      const routes = flatResources.flatMap((resource) =>
        resource.methods.map((method) => ({
          path: resource.path,
          method: method.type,
          auth: method.authorization,
          apiKeyRequired: method.apiKeyRequired,
          integration: {
            type: method.integrationType,
            url: method.integrationUrl || "",
          },
          operationName: method.operationName,
          requestValidator: method.requestValidator,
        })),
      );

      const config = {
        apiVersion: "v1",
        name,
        type: type.toUpperCase(),
        resources: flatResources.map((r) => ({
          id: r.id,
          path: r.path,
          pathPart: r.pathPart,
          parentId: r.parentId,
        })),
        routes,
        _meta: {
          ui: {
            type,
            format: "resource",
            createdAt: editId ? undefined : now,
            updatedAt: now,
          },
        },
      };

      const payload: any = { name, version, description, type, config };

      if (editId) {
        const res = await updateAPI(editId, payload);
        setSuccess({ id: (res as any).id || editId });
      } else {
        const res = await createAPI(payload);
        setSuccess({ id: (res as any).id });
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!editId) return;

    let mounted = true;
    setLoadingEdit(true);

    (async () => {
      try {
        const apiData = await getAPI(editId);
        if (!mounted) return;

        setName(apiData.name || "");
        setDescription(apiData.description || "");
        setVersion(apiData.version || "1.0.0");

        if (
          (apiData as any).config?.resources &&
          Array.isArray((apiData as any).config.resources)
        ) {
          const cfg = (apiData as any).config;
          if (cfg._meta?.ui?.type) setType(cfg._meta.ui.type);

          const savedResources: Resource[] = cfg.resources.map((r: any) => ({
            ...r,
            methods: [],
            children: [],
          }));

          cfg.routes?.forEach((route: any) => {
            const resource = savedResources.find((r) => r.path === route.path);
            if (resource) {
              resource.methods.push({
                type: route.method || "GET",
                authorization: route.auth || "NONE",
                apiKeyRequired: route.apiKeyRequired || false,
                integrationType: route.integration?.type || "HTTP",
                integrationUrl: route.integration?.url || "",
                operationName: route.operationName || "",
                requestValidator: route.requestValidator,
              });
            }
          });

          setResources(buildResourceTree(savedResources));
        }
      } catch (e: any) {
        console.error("failed to load api", e);
        if (mounted) {
          setError(`Failed to load API: ${e?.message || String(e)}`);
        }
      } finally {
        if (mounted) {
          setLoadingEdit(false);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, [editId]);

  const renderResource = (
    resource: Resource,
    level: number = 0,
  ): React.ReactElement => {
    const isExpanded = expandedResources.has(resource.id);
    const hasChildren = resource.children && resource.children.length > 0;

    return (
      <Box key={resource.id}>
        <ListItem disablePadding sx={{ pl: level * 2 }}>
          <ListItemButton
            selected={selectedResource?.id === resource.id}
            onClick={() => setSelectedResource(resource)}
            sx={{ borderRadius: 1 }}
          >
            {hasChildren && (
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedResources((prev) => {
                    const next = new Set(prev);
                    if (isExpanded) {
                      next.delete(resource.id);
                    } else {
                      next.add(resource.id);
                    }
                    return next;
                  });
                }}
              >
                {isExpanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
              </IconButton>
            )}
            <ListItemText
              primary={
                <Box>
                  <Chip
                    label={resource.pathPart}
                    size="small"
                    variant="outlined"
                    sx={{ mr: 1, fontWeight: 600 }}
                  />
                  <Chip
                    label={type === "rest" ? "REST" : "GraphQL"}
                    size="small"
                    color={type === "rest" ? "primary" : "secondary"}
                    sx={{ fontSize: "0.7rem" }}
                  />
                </Box>
              }
              secondary={
                resource.methods.length > 0 && (
                  <Box
                    sx={{
                      display: "flex",
                      gap: 0.5,
                      mt: 0.5,
                      flexWrap: "wrap",
                    }}
                  >
                    {resource.methods.map((m, i) => (
                      <Chip
                        key={i}
                        label={m.type}
                        size="small"
                        color={type === "rest" ? "primary" : "secondary"}
                      />
                    ))}
                  </Box>
                )
              }
            />
          </ListItemButton>
        </ListItem>
        {isExpanded && hasChildren && (
          <Collapse in={isExpanded}>
            {resource.children!.map((child) =>
              renderResource(child, level + 1),
            )}
          </Collapse>
        )}
      </Box>
    );
  };

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Typography variant="h4" gutterBottom>
        {editId ? "Update API" : "Create API"}
      </Typography>

      {loadingEdit && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Loading API details...
        </Alert>
      )}

      {success && (
        <Alert
          severity="success"
          action={
            <Box>
              <Button
                size="small"
                onClick={() => navigate(`/apis/${success.id}`)}
              >
                View API
              </Button>
              <Button size="small" onClick={() => navigate("/apis/create")}>
                Create another
              </Button>
            </Box>
          }
          sx={{ mb: 2 }}
        >
          API {editId ? "updated" : "created"} successfully.
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box component="form" onSubmit={handleCreate}>
        <Grid container spacing={3}>
          {/* Left: Basic Info */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                API Details
              </Typography>
              <Stack spacing={2}>
                <TextField
                  label="Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  fullWidth
                  required
                  disabled={loadingEdit}
                />
                <TextField
                  label="Description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  fullWidth
                  multiline
                  rows={2}
                  disabled={loadingEdit}
                />
                <TextField
                  label="Version"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  disabled={loadingEdit}
                />
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Type
                  </Typography>
                  <RadioGroup
                    row
                    value={type}
                    onChange={(e) => handleTypeChange(e.target.value)}
                  >
                    <FormControlLabel
                      value="rest"
                      control={<Radio />}
                      label="REST API"
                      disabled={loadingEdit}
                    />
                    <FormControlLabel
                      value="graphql"
                      control={<Radio />}
                      label="GraphQL API"
                      disabled={loadingEdit}
                    />
                  </RadioGroup>
                </Box>
              </Stack>
            </Paper>

            {/* Resource Tree */}
            <Paper sx={{ p: 2, mt: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1,
                }}
              >
                <Typography variant="h6">Resources</Typography>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => {
                    if (!selectedResource) {
                      setSelectedResource(resources[0]);
                    }
                    setResourceDialogOpen(true);
                  }}
                  disabled={loadingEdit}
                >
                  Create
                </Button>
              </Box>
              <List dense>
                {resources.map((resource) => renderResource(resource))}
              </List>
            </Paper>
          </Grid>

          {/* Right: Resource Details */}
          <Grid item xs={12} md={8}>
            <ResourceDetailsPanel
              selectedResource={selectedResource}
              apiType={type}
              onOpenResourceDialog={handleOpenResourceDialog}
              onOpenMethodDialog={openMethodDialog}
              onEditMethod={openEditMethodDialog}
              onDeleteMethod={deleteMethod}
            />

            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 1,
                mt: 2,
              }}
            >
              <Button onClick={() => navigate(-1)}>Cancel</Button>
              <Button
                variant="contained"
                color="primary"
                type="submit"
                disabled={loading || loadingEdit}
              >
                {editId
                  ? loading
                    ? "Updating…"
                    : "Update API"
                  : loading
                    ? "Creating…"
                    : "Create API"}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* Extracted Dialog Components */}
      <ResourceDialog
        open={resourceDialogOpen}
        onClose={handleCloseResourceDialog}
        onSubmit={addResource}
        newResourcePath={newResourcePath}
        onPathChange={setNewResourcePath}
        selectedResourcePath={selectedResource?.path}
      />

      <MethodDialog
        open={methodDialogOpen}
        onClose={handleCloseMethodDialog}
        onSubmit={addMethod}
        apiType={type}
        method={newMethod}
        onMethodChange={setNewMethod}
        editingMethodIndex={editingMethodIndex}
        validationError={validationError}
      />

      <TypeChangeDialog
        open={typeChangeDialogOpen}
        onConfirm={confirmTypeChange}
        onCancel={cancelTypeChange}
        currentType={type}
        pendingType={pendingType}
      />
    </Container>
  );
}
