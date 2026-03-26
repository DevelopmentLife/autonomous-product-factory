import { apiClient } from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  login: (username: string, password: string) =>
    apiClient
      .post<LoginResponse>('/auth/login', { username, password })
      .then((r) => r.data),
  whoami: () => apiClient.get('/auth/whoami').then((r) => r.data),
}
