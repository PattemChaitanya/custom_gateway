import api from "./api";

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  roles?: string;
  created_at?: string;
}

export interface UserWithRoles {
  id: number;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  legacy_roles?: string;
  roles: string[];
  permissions: string[];
  created_at?: string;
}

export interface UserUpdate {
  email?: string;
  is_active?: boolean;
  is_superuser?: boolean;
}

const userService = {
  /**
   * Get list of all users
   */
  async listUsers(): Promise<User[]> {
    const response = await api.get("/user/");
    return response.data;
  },

  /**
   * Get detailed user information including roles and permissions
   */
  async getUser(userId: number): Promise<UserWithRoles> {
    const response = await api.get(`/user/${userId}`);
    return response.data;
  },

  /**
   * Get current user's information
   */
  async getCurrentUser(): Promise<UserWithRoles> {
    const response = await api.get("/user/me");
    return response.data;
  },

  /**
   * Update user information
   */
  async updateUser(userId: number, data: UserUpdate): Promise<User> {
    const response = await api.put(`/user/${userId}`, data);
    return response.data;
  },

  /**
   * Delete a user
   */
  async deleteUser(userId: number): Promise<{ message: string }> {
    const response = await api.delete(`/user/${userId}`);
    return response.data;
  },
};

export default userService;
