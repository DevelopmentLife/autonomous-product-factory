import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pipelinesApi, type CreatePipelineRequest } from '../api/pipelines'

export function usePipelines() {
  return useQuery({ queryKey: ['pipelines'], queryFn: pipelinesApi.list, refetchInterval: 5_000 })
}

export function usePipeline(id: string) {
  return useQuery({ queryKey: ['pipeline', id], queryFn: () => pipelinesApi.get(id) })
}

export function usePipelineStages(id: string) {
  return useQuery({
    queryKey: ['pipeline-stages', id],
    queryFn: () => pipelinesApi.stages(id),
    refetchInterval: 3_000,
  })
}

export function useCreatePipeline() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreatePipelineRequest) => pipelinesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
}

export function useCancelPipeline() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => pipelinesApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
}
