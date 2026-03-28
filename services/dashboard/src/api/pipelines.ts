import { apiClient } from './client'

export interface Pipeline {
  id: string
  idea: string
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
  current_stage: string | null
  created_at: string
  updated_at: string
}

export interface Stage {
  id: string
  pipeline_id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface CreatePipelineRequest {
  idea: string
  auto_approve?: boolean
}

export const pipelinesApi = {
  list: () =>
    apiClient.get<{ items: Pipeline[] } | Pipeline[]>('/pipelines').then((r) =>
      Array.isArray(r.data) ? r.data : r.data.items,
    ),
  get: (id: string) => apiClient.get<Pipeline>(`/pipelines/${id}`).then((r) => r.data),
  create: (data: CreatePipelineRequest) =>
    apiClient.post<Pipeline>('/pipelines', data).then((r) => r.data),
  cancel: (id: string) => apiClient.delete(`/pipelines/${id}`),
  pause: (id: string) => apiClient.post(`/pipelines/${id}/pause`),
  resume: (id: string) => apiClient.post(`/pipelines/${id}/resume`),
  stages: (id: string) => apiClient.get<Stage[]>(`/pipelines/${id}/stages`).then((r) => r.data),
  approveStage: (pipelineId: string, stageId: string) =>
    apiClient.post(`/pipelines/${pipelineId}/stages/${stageId}/approve`),
}
