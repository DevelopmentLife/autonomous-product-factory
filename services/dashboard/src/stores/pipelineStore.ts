import { create } from 'zustand'
import type { Pipeline } from '../api/pipelines'

interface PipelineState {
  pipelines: Record<string, Pipeline>
  setPipeline: (p: Pipeline) => void
  updatePipeline: (id: string, patch: Partial<Pipeline>) => void
}

export const usePipelineStore = create<PipelineState>()((set) => ({
  pipelines: {},
  setPipeline: (p) => set((s) => ({ pipelines: { ...s.pipelines, [p.id]: p } })),
  updatePipeline: (id, patch) =>
    set((s) => ({
      pipelines: { ...s.pipelines, [id]: { ...s.pipelines[id], ...patch } },
    })),
}))
