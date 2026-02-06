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
  Switch,
  FormControlLabel,
  Paper,
  Tooltip,
} from "@mui/material";
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  PersonAdd as PersonAddIcon,
  Security as SecurityIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import userService, {
  type User,
  type UserWithRoles,
  type UserUpdate,
} from "../services/users";
import authorizersService, { type Role } from "../services/authorizers";
import usePermissions from "../hooks/usePermissions";

const Users: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Edit user dialog
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editFormData, setEditFormData] = useState<UserUpdate>({});

  // User details dialog
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserWithRoles | null>(null);

  // Assign role dialog
  const [assignRoleDialogOpen, setAssignRoleDialogOpen] = useState(false);
  const [assignRoleUserId, setAssignRoleUserId] = useState<number | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number | string>("");

  // Delete dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);

  const { hasPermission, isSuperuser } = usePermissions();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [usersData, rolesData] = await Promise.all([
        userService.listUsers(),
        authorizersService.listRoles(),
      ]);
      setUsers(usersData);
      setRoles(rolesData);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

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

  const handleOpenDeleteDialog = (user: User) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const handleCloseDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setUserToDelete(null);
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;

    try {
      await userService.deleteUser(userToDelete.id);
      setSuccess("User deleted successfully");
      handleCloseDeleteDialog();
      loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete user");
    }
  };

  if (!hasPermission("user:list") && !isSuperuser) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          You don't have permission to view users. Required permission:
          user:list
        </Alert>
      </Box>
    );
  }

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
        <Typography variant="h4" component="h1">
          User Management
        </Typography>
        <Box>
          <Button startIcon={<RefreshIcon />} onClick={loadData} sx={{ mr: 1 }}>
            Refresh
          </Button>
        </Box>
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

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Roles</TableCell>
                  <TableCell>Superuser</TableCell>
                  <TableCell>Created At</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.id}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? "Active" : "Inactive"}
                        color={user.is_active ? "success" : "default"}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {user.roles ? (
                        user.roles
                          .split(",")
                          .map((role, idx) => (
                            <Chip
                              key={idx}
                              label={role.trim()}
                              size="small"
                              sx={{ mr: 0.5 }}
                            />
                          ))
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          None
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.is_superuser ? (
                        <Chip
                          icon={<SecurityIcon />}
                          label="Yes"
                          color="error"
                          size="small"
                        />
                      ) : (
                        "No"
                      )}
                    </TableCell>
                    <TableCell>
                      {user.created_at
                        ? new Date(user.created_at).toLocaleDateString()
                        : "N/A"}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => handleViewDetails(user)}
                        >
                          <SecurityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {hasPermission("user:update") && (
                        <Tooltip title="Edit User">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenEditDialog(user)}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {hasPermission("role:assign") && (
                        <Tooltip title="Assign Role">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenAssignRoleDialog(user.id)}
                          >
                            <PersonAddIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {hasPermission("user:delete") && (
                        <Tooltip title="Delete User">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleOpenDeleteDialog(user)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {/* Edit User Dialog */}
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
            {isSuperuser && (
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
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditDialog}>Cancel</Button>
          <Button
            onClick={handleSubmitEdit}
            variant="contained"
            color="primary"
          >
            Save
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
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Basic Information
                </Typography>
                <Typography>
                  <strong>ID:</strong> {selectedUser.id}
                </Typography>
                <Typography>
                  <strong>Email:</strong> {selectedUser.email}
                </Typography>
                <Typography>
                  <strong>Active:</strong>{" "}
                  {selectedUser.is_active ? "Yes" : "No"}
                </Typography>
                <Typography>
                  <strong>Superuser:</strong>{" "}
                  {selectedUser.is_superuser ? "Yes" : "No"}
                </Typography>
              </Paper>

              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Roles ({selectedUser.roles.length})
                </Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {selectedUser.roles.length > 0 ? (
                    selectedUser.roles.map((role, idx) => (
                      <Chip key={idx} label={role} color="primary" />
                    ))
                  ) : (
                    <Typography color="text.secondary">
                      No roles assigned
                    </Typography>
                  )}
                </Box>
              </Paper>

              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Permissions ({selectedUser.permissions.length})
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 1,
                    maxHeight: 200,
                    overflow: "auto",
                  }}
                >
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
                      No permissions granted
                    </Typography>
                  )}
                </Box>
              </Paper>
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
          <Button
            onClick={handleAssignRole}
            variant="contained"
            color="primary"
            disabled={!selectedRoleId}
          >
            Assign
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete User Dialog */}
      <Dialog open={deleteDialogOpen} onClose={handleCloseDeleteDialog}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete user{" "}
            <strong>{userToDelete?.email}</strong>? This action cannot be
            undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDeleteDialog}>Cancel</Button>
          <Button onClick={handleDeleteUser} variant="contained" color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Users;
