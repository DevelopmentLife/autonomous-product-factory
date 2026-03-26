import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePipelines, useCreatePipeline } from '../hooks/usePipelines'
import { StatusBadge } from '../components/StatusBadge'
import { formatDistanceToNow } from 'date-fns'
import { Plus, Loader2 } from 'lucide-react'

export default function PipelinesPage() {
  const { data: pipelines, isLoading } = usePipelines()
  const createPipeline = useCreatePipeline()
  const [idea, setIdea] = useState('')
  const [showForm, setShowForm] = useState(false)
  const navigate = useNavigate()

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) return
    const p = await createPipeline.mutateAsync({ idea: idea.trim(), auto_approve: true })
    setIdea('')
    setShowForm(false)
    navigate(`/pipelines/${p.id}`)
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Pipelines</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Pipeline
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 bg-gray-900 rounded-xl p-4 border border-gray-800 flex gap-3">
          <input
            autoFocus
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Describe your product idea..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            disabled={createPipeline.isPending}
            className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            {createPipeline.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Run'}
          </button>
        </form>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="animate-spin text-brand-500" size={32} /></div>
      ) : (
        <div className="space-y-3">
          {(pipelines ?? []).map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/pipelines/${p.id}`)}
              className="bg-gray-900 border border-gray-800 rounded-xl p-4 cursor-pointer hover:border-gray-600 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 mr-4">
                  <p className="font-medium text-white truncate">{p.idea}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {formatDistanceToNow(new Date(p.created_at), { addSuffix: true })}
                    {p.current_stage && ` · ${p.current_stage}`}
                  </p>
                </div>
                <StatusBadge status={p.status} />
              </div>
            </div>
          ))}
          {(pipelines ?? []).length === 0 && (
            <p className="text-gray-500 text-center py-12">No pipelines yet. Create one to get started.</p>
          )}
        </div>
      )}
    </div>
  )
}
