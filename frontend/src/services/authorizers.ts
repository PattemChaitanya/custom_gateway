import api from "./api";

export interface Role {
  id: number;
  name: string;
  description?: string;
  permissions: string[];
  created_at: string;
  updated_at?: string;
}

export interface CreateRoleRequest {
  name: string;
  description?: string;
  permissions?: string[];
}

export interface UpdateRoleRequest {
  name?: string;
  description?: string;
  permissions?: string[];
}

export interface Permission {
  id: number;
  name: string;
  resource: string;
  action: string;
  description?: string;
  created_at: string;
}

export interface CreatePermissionRequest {
  name: string;
  resource: string;
  action: string;
  description?: string;
}

export interface UserRoleAssignment {
  user_id: number;
  role_id: number;
}

const authorizersService = {
  // Roles
  async listRoles(): Promise<Role[]> {
    const response = await api.get("/api/authorizers/roles");
    return response.data;
  },

  async getRole(id: number): Promise<Role> {
    const response = await api.get(`/api/authorizers/roles/${id}`);
    return response.data;
  },

  async createRole(data: CreateRoleRequest): Promise<Role> {
    const response = await api.post("/api/authorizers/roles", data);
    return response.data;
  },

  async updateRole(id: number, data: UpdateRoleRequest): Promise<Role> {
    const response = await api.put(`/api/authorizers/roles/${id}`, data);
    return response.data;
  },

  async deleteRole(id: number): Promise<void> {
    await api.delete(`/api/authorizers/roles/${id}`);
  },

  // Permissions
  async listPermissions(): Promise<Permission[]> {
    const response = await api.get("/api/authorizers/permissions");
    return response.data;
  },

  async getPermission(id: number): Promise<Permission> {
    const response = await api.get(`/api/authorizers/permissions/${id}`);
    return response.data;
  },

  async createPermission(data: CreatePermissionRequest): Promise<Permission> {
    const response = await api.post("/api/authorizers/permissions", data);
    return response.data;
  },

  async deletePermission(id: number): Promise<void> {
    await api.delete(`/api/authorizers/permissions/${id}`);
  },

  // User-Role assignments
  async assignRoleToUser(data: UserRoleAssignment): Promise<void> {
    await api.post("/api/authorizers/users/assign-role", data);
  },

  async removeRoleFromUser(userId: number, roleId: number): Promise<void> {
    await api.delete(`/api/authorizers/users/${userId}/roles/${roleId}`);
  },

  async getUserRoles(userId: number): Promise<Role[]> {
    const response = await api.get(`/api/authorizers/users/${userId}/roles`);
    return response.data;
  },
};

export default authorizersService;
