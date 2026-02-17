import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  Card,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Switch,
  FormControlLabel,
  Paper,
  Tooltip,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PersonAdd as PersonAddIcon,
  Security as SecurityIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import authorizersService from "../services/authorizers";
import type {
  Role,
  CreateRoleRequest,
  Permission,
  CreatePermissionRequest,
} from "../services/authorizers";
import userService, {
  type User,
  type UserWithRoles,
  type UserUpdate,
} from "../services/users";
import usePermissions from "../hooks/usePermissions";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

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

const Authorizers: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Role dialog state
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [roleFormData, setRoleFormData] = useState<CreateRoleRequest>({
    name: "",
    description: "",
    permissions: [],
  });

  // Permission dialog state
  const [permissionDialogOpen, setPermissionDialogOpen] = useState(false);
  const [permissionFormData, setPermissionFormData] =
    useState<CreatePermissionRequest>({
      name: "",
      resource: "api",
      action: "read",
      description: "",
    });

  // User dialog states
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editFormData, setEditFormData] = useState<UserUpdate>({});
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserWithRoles | null>(null);
  const [assignRoleDialogOpen, setAssignRoleDialogOpen] = useState(false);
  const [assignRoleUserId, setAssignRoleUserId] = useState<number | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number | string>("");

  // Delete dialogs
  const [deleteRoleDialogOpen, setDeleteRoleDialogOpen] = useState(false);
  const [roleToDelete, setRoleToDelete] = useState<number | null>(null);
  const [deletePermissionDialogOpen, setDeletePermissionDialogOpen] =
    useState(false);
  const [permissionToDelete, setPermissionToDelete] = useState<number | null>(
    null,
  );
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);

  const { hasPermission, isSuperuser } = usePermissions();

  useEffect(() => {
    loadData();
  }, [tabValue]);

  const loadData = async () => {
    try {
      setLoading(true);
      if (tabValue === 0) {
        const rolesData = await authorizersService.listRoles();
        setRoles(rolesData);
      } else if (tabValue === 1) {
        const permissionsData = await authorizersService.listPermissions();
        setPermissions(permissionsData);
      } else if (tabValue === 2) {
        const [usersData, rolesData] = await Promise.all([
          userService.listUsers(),
          authorizersService.listRoles(),
        ]);
        setUsers(usersData);
        setRoles(rolesData);
      }
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  // Role handlers
  const handleOpenRoleDialog = (role?: Role) => {
    if (role) {
      setEditingRole(role);
      setRoleFormData({
        name: role.name,
        description: role.description,
        permissions: role.permissions,
      });
    } else {
      setEditingRole(null);
      setRoleFormData({
        name: "",
        description: "",
        permissions: [],
      });
    }
    setRoleDialogOpen(true);
  };

  const handleCloseRoleDialog = () => {
    setRoleDialogOpen(false);
    setEditingRole(null);
  };

  const handleSubmitRole = async () => {
    try {
      if (editingRole) {
        await authorizersService.updateRole(editingRole.id, roleFormData);
        setSuccess("Role updated successfully");
      } else {
        await authorizersService.createRole(roleFormData);
        setSuccess("Role created successfully");
      }

      handleCloseRoleDialog();
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to save role");
    }
  };

  const handleDeleteRole = async () => {
    if (!roleToDelete) return;

    try {
      await authorizersService.deleteRole(roleToDelete);
      setSuccess("Role deleted successfully");
      setDeleteRoleDialogOpen(false);
      setRoleToDelete(null);
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete role");
    }
  };

  // Permission handlers
  const handleOpenPermissionDialog = () => {
    setPermissionFormData({
      name: "",
      resource: "api",
      action: "read",
      description: "",
    });
    setPermissionDialogOpen(true);
  };

  const handleClosePermissionDialog = () => {
    setPermissionDialogOpen(false);
  };

  const handleSubmitPermission = async () => {
    try {
      await authorizersService.createPermission(permissionFormData);
      setSuccess("Permission created successfully");

      handleClosePermissionDialog();
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create permission");
    }
  };

  const handleDeletePermission = async () => {
    if (!permissionToDelete) return;

    try {
      await authorizersService.deletePermission(permissionToDelete);
      setSuccess("Permission deleted successfully");
      setDeletePermissionDialogOpen(false);
      setPermissionToDelete(null);
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete permission");
    }
  };

  // User handlers
  const handleViewDetails = async (user: User) => {
    try {
      const detailedUser = await userService.getUser(user.id);
      setSelectedUser(detailedUser);
      setDetailsDialogOpen(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load user details");
    }
  };

  const handleOpenEditDialog = (user: User) => {
    setEditingUser(user);
    setEditFormData({
      email: user.email,
      is_active: user.is_active,
      is_superuser: user.is_superuser,
    });
    setEditDialogOpen(true);
  };

  const handleCloseEditDialog = () => {
    setEditDialogOpen(false);
    setEditingUser(null);
    setEditFormData({});
  };

  const handleSubmitEdit = async () => {
    if (!editingUser) return;

    try {
      await userService.updateUser(editingUser.id, editFormData);
      setSuccess("User updated successfully");
      handleCloseEditDialog();
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update user");
    }
  };

  const handleOpenAssignRoleDialog = (userId: number) => {
    setAssignRoleUserId(userId);
    setSelectedRoleId("");
    setAssignRoleDialogOpen(true);
  };

  const handleCloseAssignRoleDialog = () => {
    setAssignRoleDialogOpen(false);
    setAssignRoleUserId(null);
    setSelectedRoleId("");
  };

  const handleAssignRole = async () => {
    if (!assignRoleUserId || !selectedRoleId) return;

    try {
      await authorizersService.assignRoleToUser({
        user_id: assignRoleUserId,
        role_id: Number(selectedRoleId),
      });
      setSuccess("Role assigned successfully");
      handleCloseAssignRoleDialog();
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to assign role");
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;

    try {
      await userService.deleteUser(userToDelete.id);
      setSuccess("User deleted successfully");
      setDeleteDialogOpen(false);
      setUserToDelete(null);
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete user");
    }
  };

  const handlePermissionsChange = (event: SelectChangeEvent<string[]>) => {
    const {
      target: { value },
    } = event;
    setRoleFormData({
      ...roleFormData,
      permissions: typeof value === "string" ? value.split(",") : value,
    });
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4">Authorizers (RBAC)</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            if (tabValue === 0) handleOpenRoleDialog();
            else if (tabValue === 1) handleOpenPermissionDialog();
          }}
        >
          Add {tabValue === 0 ? "Role" : tabValue === 1 ? "Permission" : ""}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          onClose={() => setSuccess(null)}
        >
          {success}
        </Alert>
      )}

      <Card>
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
        >
          <Tab label="Roles" />
          <Tab label="Permissions" />
          <Tab label="Users" />
        </Tabs>

        {/* Roles Tab */}
        <TabPanel value={tabValue} index={0}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Permissions</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {roles.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography color="textSecondary">
                          No roles found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    roles.map((role) => (
                      <TableRow key={role.id}>
                        <TableCell>{role.name}</TableCell>
                        <TableCell>{role.description || "-"}</TableCell>
                        <TableCell>
                          <Box
                            sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}
                          >
                            {role.permissions.slice(0, 3).map((perm, idx) => (
                              <Chip key={idx} label={perm} size="small" />
                            ))}
                            {role.permissions.length > 3 && (
                              <Chip
                                label={`+${role.permissions.length - 3} more`}
                                size="small"
                              />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          {new Date(role.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleOpenRoleDialog(role)}
                          >
                            <EditIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              setRoleToDelete(role.id);
                              setDeleteRoleDialogOpen(true);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Permissions Tab */}
        <TabPanel value={tabValue} index={1}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Resource</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {permissions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography color="textSecondary">
                          No permissions found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    permissions.map((permission) => (
                      <TableRow key={permission.id}>
                        <TableCell>{permission.name}</TableCell>
                        <TableCell>
                          <Chip
                            label={permission.resource}
                            size="small"
                            color="primary"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={permission.action}
                            size="small"
                            color="secondary"
                          />
                        </TableCell>
                        <TableCell>{permission.description || "-"}</TableCell>
                        <TableCell>
                          {new Date(permission.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              setPermissionToDelete(permission.id);
                              setDeletePermissionDialogOpen(true);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Users Tab */}
        <TabPanel value={tabValue} index={2}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Email</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Superuser</TableCell>
                    <TableCell>Roles</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography color="textSecondary">
                          No users found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>
                          <Chip
                            label={user.is_active ? "Active" : "Inactive"}
                            color={user.is_active ? "success" : "default"}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {user.is_superuser ? (
                            <Chip
                              label="Yes"
                              color="error"
                              size="small"
                            />
                          ) : (
                            <Chip label="No" variant="outlined" size="small" />
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={user.roles || "No roles"}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          {user.created_at
                            ? new Date(user.created_at).toLocaleDateString()
                            : "-"}
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="View Details">
                            <IconButton
                              size="small"
                              onClick={() => handleViewDetails(user)}
                            >
                              <SecurityIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit User">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleOpenEditDialog(user)}
                            >
                              <EditIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Assign Role">
                            <IconButton
                              size="small"
                              color="secondary"
                              onClick={() => handleOpenAssignRoleDialog(user.id)}
                            >
                              <PersonAddIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete User">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                setUserToDelete(user);
                                setDeleteDialogOpen(true);
                              }}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>
      </Card>

      {/* Role Create/Edit Dialog */}
      <Dialog
        open={roleDialogOpen}
        onClose={handleCloseRoleDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{editingRole ? "Edit Role" : "Create Role"}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Name"
              fullWidth
              value={roleFormData.name}
              onChange={(e) =>
                setRoleFormData({ ...roleFormData, name: e.target.value })
              }
              required
            />

            <TextField
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={roleFormData.description}
              onChange={(e) =>
                setRoleFormData({
                  ...roleFormData,
                  description: e.target.value,
                })
              }
            />

            <FormControl fullWidth>
              <InputLabel>Permissions</InputLabel>
              <Select
                multiple
                value={roleFormData.permissions || []}
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
          <Button onClick={handleCloseRoleDialog}>Cancel</Button>
          <Button onClick={handleSubmitRole} variant="contained">
            {editingRole ? "Update" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Permission Create Dialog */}
      <Dialog
        open={permissionDialogOpen}
        onClose={handleClosePermissionDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create Permission</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Name"
              fullWidth
              value={permissionFormData.name}
              onChange={(e) =>
                setPermissionFormData({
                  ...permissionFormData,
                  name: e.target.value,
                })
              }
              required
              placeholder="e.g., api:create"
            />

            <FormControl fullWidth required>
              <InputLabel>Resource</InputLabel>
              <Select
                value={permissionFormData.resource}
                onChange={(e) =>
                  setPermissionFormData({
                    ...permissionFormData,
                    resource: e.target.value,
                  })
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
                value={permissionFormData.action}
                onChange={(e) =>
                  setPermissionFormData({
                    ...permissionFormData,
                    action: e.target.value,
                  })
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
              value={permissionFormData.description}
              onChange={(e) =>
                setPermissionFormData({
                  ...permissionFormData,
                  description: e.target.value,
                })
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePermissionDialog}>Cancel</Button>
          <Button onClick={handleSubmitPermission} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* User Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={handleCloseEditDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Email"
              type="email"
              fullWidth
              value={editFormData.email || ""}
              onChange={(e) =>
                setEditFormData({ ...editFormData, email: e.target.value })
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={editFormData.is_active ?? true}
                  onChange={(e) =>
                    setEditFormData({
                      ...editFormData,
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
                  checked={editFormData.is_superuser ?? false}
                  onChange={(e) =>
                    setEditFormData({
                      ...editFormData,
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
          <Button onClick={handleCloseEditDialog}>Cancel</Button>
          <Button onClick={handleSubmitEdit} variant="contained">
            Update
          </Button>
        </DialogActions>
      </Dialog>

      {/* User Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>User Details</DialogTitle>
        <DialogContent>
          {selectedUser && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="h6" gutterBottom>
                {selectedUser.email}
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Typography>
                  {selectedUser.is_active ? "Active" : "Inactive"}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Superuser
                </Typography>
                <Typography>
                  {selectedUser.is_superuser ? "Yes" : "No"}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Roles
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  {selectedUser.roles.length > 0 ? (
                    selectedUser.roles.map((role, idx) => (
                      <Chip key={idx} label={role} color="primary" />
                    ))
                  ) : (
                    <Typography color="text.secondary">No roles</Typography>
                  )}
                </Box>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Permissions
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  {selectedUser.permissions.length > 0 ? (
                    selectedUser.permissions.map((perm, idx) => (
                      <Chip
                        key={idx}
                        label={perm}
                        size="small"
                        variant="outlined"
                      />
                    ))
                  ) : (
                    <Typography color="text.secondary">
                      No permissions
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Assign Role Dialog */}
      <Dialog
        open={assignRoleDialogOpen}
        onClose={handleCloseAssignRoleDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Assign Role to User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Select Role</InputLabel>
              <Select
                value={selectedRoleId}
                onChange={(e) => setSelectedRoleId(e.target.value)}
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
          <Button onClick={handleCloseAssignRoleDialog}>Cancel</Button>
          <Button onClick={handleAssignRole} variant="contained">
            Assign
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Role Confirmation */}
      <Dialog
        open={deleteRoleDialogOpen}
        onClose={() => setDeleteRoleDialogOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this role?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteRoleDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteRole} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Permission Confirmation */}
      <Dialog
        open={deletePermissionDialogOpen}
        onClose={() => setDeletePermissionDialogOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this permission?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeletePermissionDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleDeletePermission}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete User Confirmation */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete user {userToDelete?.email}?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteUser} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Authorizers;
