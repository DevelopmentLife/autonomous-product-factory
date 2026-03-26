import { apiClient } from './client'

export interface Connector {
  type: string
  enabled: boolean
  config: Record<string, string>
}

export const connectorsApi = {
  list: () => apiClient.get<Connector[]>('/connectors').then((r) => r.data),
  get: (type: string) => apiClient.get<Connector>(`/connectors/${type}`).then((r) => r.data),
  update: (type: string, config: Record<string, string>) =>
    apiClient.put(`/connectors/${type}`, { config }),
  delete: (type: string) => apiClient.delete(`/connectors/${type}`),
}
