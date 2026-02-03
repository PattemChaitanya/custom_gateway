import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
    const token = localStorage.getItem("token");

    const response = await axios.get(`${API_URL}/api/authorizers/roles`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  },

  async getRole(id: number): Promise<Role> {
    const token = localStorage.getItem("token");

    const response = await axios.get(`${API_URL}/api/authorizers/roles/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  },

  async createRole(data: CreateRoleRequest): Promise<Role> {
    const token = localStorage.getItem("token");

    const response = await axios.post(
      `${API_URL}/api/authorizers/roles`,
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      },
    );

    return response.data;
  },

  async updateRole(id: number, data: UpdateRoleRequest): Promise<Role> {
    const token = localStorage.getItem("token");

    const response = await axios.put(
      `${API_URL}/api/authorizers/roles/${id}`,
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      },
    );

    return response.data;
  },

  async deleteRole(id: number): Promise<void> {
    const token = localStorage.getItem("token");

    await axios.delete(`${API_URL}/api/authorizers/roles/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  // Permissions
  async listPermissions(): Promise<Permission[]> {
    const token = localStorage.getItem("token");

    const response = await axios.get(`${API_URL}/api/authorizers/permissions`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  },

  async getPermission(id: number): Promise<Permission> {
    const token = localStorage.getItem("token");

    const response = await axios.get(
      `${API_URL}/api/authorizers/permissions/${id}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    return response.data;
  },

  async createPermission(data: CreatePermissionRequest): Promise<Permission> {
    const token = localStorage.getItem("token");

    const response = await axios.post(
      `${API_URL}/api/authorizers/permissions`,
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      },
    );

    return response.data;
  },

  async deletePermission(id: number): Promise<void> {
    const token = localStorage.getItem("token");

    await axios.delete(`${API_URL}/api/authorizers/permissions/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  // User-Role assignments
  async assignRoleToUser(data: UserRoleAssignment): Promise<void> {
    const token = localStorage.getItem("token");

    await axios.post(`${API_URL}/api/authorizers/users/assign-role`, data, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
  },

  async removeRoleFromUser(userId: number, roleId: number): Promise<void> {
    const token = localStorage.getItem("token");

    await axios.delete(
      `${API_URL}/api/authorizers/users/${userId}/roles/${roleId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
  },

  async getUserRoles(userId: number): Promise<Role[]> {
    const token = localStorage.getItem("token");

    const response = await axios.get(
      `${API_URL}/api/authorizers/users/${userId}/roles`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    return response.data;
  },
};

export default authorizersService;
