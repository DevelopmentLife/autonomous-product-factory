import { apiClient } from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  login: (username: string, password: string) => {
    const body = new URLSearchParams({ username, password })
    return apiClient
      .post<LoginResponse>('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .then((r) => r.data)
  },
  whoami: () => apiClient.get('/auth/whoami').then((r) => r.data),
}
