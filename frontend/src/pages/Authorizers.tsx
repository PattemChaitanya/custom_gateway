import React, { useState } from "react";
import {
  Box,
  Button,
  Card,
  Chip,
  IconButton,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Alert,
  Tooltip,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PersonAdd as PersonAddIcon,
  Security as SecurityIcon,
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
import {
  RoleDialog,
  PermissionDialog,
  UserEditDialog,
  UserDetailsDialog,
  AssignRoleDialog,
  ConfirmDeleteDialog,
} from "./Authorizers/index";
import { useQueryCache } from "../hooks/useQueryCache";
import { TableSkeleton } from "../components/Skeletons";

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

const Authorizers: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Cached queries per tab
  const {
    data: roles = [],
    loading: rolesLoading,
    error: rolesError,
    refetch: refetchRoles,
  } = useQueryCache<Role[]>("authorizer-roles", () =>
    authorizersService.listRoles(),
  );
  const {
    data: permissions = [],
    loading: permissionsLoading,
    error: permissionsError,
    refetch: refetchPermissions,
  } = useQueryCache<Permission[]>("authorizer-permissions", () =>
    authorizersService.listPermissions(),
  );
  const {
    data: users = [],
    loading: usersLoading,
    error: usersError,
    refetch: refetchUsers,
  } = useQueryCache<User[]>("authorizer-users", () => userService.listUsers());

  const loading =
    tabValue === 0
      ? rolesLoading
      : tabValue === 1
        ? permissionsLoading
        : usersLoading;
  const fetchError = rolesError || permissionsError || usersError;
  const displayError = fetchError || error;

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
      refetchRoles();
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
      refetchRoles();
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
      refetchPermissions();
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
      refetchPermissions();
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
      refetchUsers();
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
      refetchUsers();
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
      refetchUsers();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete user");
    }
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

      {displayError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {displayError}
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
          {rolesLoading ? (
            <TableSkeleton columns={5} rows={3} />
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
          {permissionsLoading ? (
            <TableSkeleton columns={6} rows={3} />
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
          {usersLoading ? (
            <TableSkeleton columns={5} rows={3} />
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
                            <Chip label="Yes" color="error" size="small" />
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
                              onClick={() =>
                                handleOpenAssignRoleDialog(user.id)
                              }
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
      <RoleDialog
        open={roleDialogOpen}
        onClose={handleCloseRoleDialog}
        onSubmit={handleSubmitRole}
        editingRole={editingRole}
        formData={roleFormData}
        onFormDataChange={setRoleFormData}
        permissions={permissions}
      />

      {/* Permission Create Dialog */}
      <PermissionDialog
        open={permissionDialogOpen}
        onClose={handleClosePermissionDialog}
        onSubmit={handleSubmitPermission}
        formData={permissionFormData}
        onFormDataChange={setPermissionFormData}
      />

      {/* User Edit Dialog */}
      <UserEditDialog
        open={editDialogOpen}
        onClose={handleCloseEditDialog}
        onSubmit={handleSubmitEdit}
        editingUser={editingUser}
        formData={editFormData}
        onFormDataChange={setEditFormData}
      />

      {/* User Details Dialog */}
      <UserDetailsDialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        user={selectedUser}
      />

      {/* Assign Role Dialog */}
      <AssignRoleDialog
        open={assignRoleDialogOpen}
        onClose={handleCloseAssignRoleDialog}
        onSubmit={handleAssignRole}
        roles={roles}
        selectedRoleId={selectedRoleId}
        onSelectedRoleIdChange={setSelectedRoleId}
      />

      {/* Delete Role Confirmation */}
      <ConfirmDeleteDialog
        open={deleteRoleDialogOpen}
        onClose={() => setDeleteRoleDialogOpen(false)}
        onConfirm={handleDeleteRole}
        message="Are you sure you want to delete this role?"
      />

      {/* Delete Permission Confirmation */}
      <ConfirmDeleteDialog
        open={deletePermissionDialogOpen}
        onClose={() => setDeletePermissionDialogOpen(false)}
        onConfirm={handleDeletePermission}
        message="Are you sure you want to delete this permission?"
      />

      {/* Delete User Confirmation */}
      <ConfirmDeleteDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteUser}
        message={`Are you sure you want to delete user ${userToDelete?.email}?`}
      />
    </Box>
  );
};

export default Authorizers;
