import { useParams, useNavigate } from 'react-router-dom'
import { usePipeline, usePipelineStages, useCancelPipeline } from '../hooks/usePipelines'
import { usePipelineWS } from '../hooks/usePipelineWS'
import { StatusBadge } from '../components/StatusBadge'
import { StageTimeline } from '../components/StageTimeline'
import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, XCircle, Loader2 } from 'lucide-react'
import { apiClient } from '../api/client'

export default function PipelineDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: pipeline } = usePipeline(id!)
  const { data: stages } = usePipelineStages(id!)
  const cancelPipeline = useCancelPipeline()
  usePipelineWS(id!)

  if (!pipeline) {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-brand-500" size={32} /></div>
  }

  const handleCancel = async () => {
    await cancelPipeline.mutateAsync(id!)
    navigate('/pipelines')
  }

  const handlePauseResume = async () => {
    if (pipeline.status === 'paused') {
      await apiClient.post(`/pipelines/${id}/resume`)
    } else {
      await apiClient.post(`/pipelines/${id}/pause`)
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <button
        onClick={() => navigate('/pipelines')}
        className="flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-6 transition-colors"
      >
        <ArrowLeft size={14} /> Pipelines
      </button>

      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-xl font-bold text-white mb-2">{pipeline.idea}</h1>
          <div className="flex items-center gap-3">
            <StatusBadge status={pipeline.status} />
            <span className="text-xs text-gray-500">
              Created {formatDistanceToNow(new Date(pipeline.created_at), { addSuffix: true })}
            </span>
            {pipeline.current_stage && (
              <span className="text-xs text-gray-400">Stage: {pipeline.current_stage}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {['running', 'paused'].includes(pipeline.status) && (
            <button
              onClick={handlePauseResume}
              className="text-sm px-3 py-1.5 rounded-md bg-yellow-900 text-yellow-300 hover:bg-yellow-800 transition-colors"
            >
              {pipeline.status === 'paused' ? 'Resume' : 'Pause'}
            </button>
          )}
          {['pending', 'running', 'paused'].includes(pipeline.status) && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-md bg-red-900 text-red-300 hover:bg-red-800 transition-colors"
            >
              <XCircle size={14} /> Cancel
            </button>
          )}
        </div>
      </div>

      {stages && stages.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-200 mb-4">Stages</h2>
          <StageTimeline stages={stages} />
        </div>
      )}
    </div>
  )
}
