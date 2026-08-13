import { apiClient } from './client';

export interface User {
  id: number;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export const authApi = {
  register: async (email: string, password: string): Promise<User> => {
    const res = await apiClient.post<User>('/auth/register', { email, password });
    return res.data;
  },

  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>('/auth/login', { email, password });
    if (res.data.access_token) {
      localStorage.setItem('auth_token', res.data.access_token);
    }
    return res.data;
  },

  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  logout: () => {
    localStorage.removeItem('auth_token');
  },
};
