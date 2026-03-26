import type { Stage } from '../api/pipelines'
import { StatusBadge } from './StatusBadge'
import { formatDistanceToNow } from 'date-fns'

const STAGE_ORDER = [
  'prd', 'architect', 'market', 'ux', 'engineering',
  'developer', 'qa', 'regression', 'review', 'devops', 'readme',
]

export function StageTimeline({ stages }: { stages: Stage[] }) {
  const sorted = [...stages].sort(
    (a, b) => STAGE_ORDER.indexOf(a.name) - STAGE_ORDER.indexOf(b.name),
  )
  return (
    <ol className="relative border-l border-gray-700 ml-4">
      {sorted.map((s) => (
        <li key={s.id} className="mb-6 ml-6">
          <span className="absolute -left-2 w-4 h-4 rounded-full bg-gray-700 border-2 border-gray-900 mt-0.5" />
          <div className="flex items-center gap-3">
            <span className="font-semibold text-gray-200 capitalize">{s.name}</span>
            <StatusBadge status={s.status} />
          </div>
          {s.started_at && (
            <p className="text-xs text-gray-500 mt-1">
              Started {formatDistanceToNow(new Date(s.started_at), { addSuffix: true })}
            </p>
          )}
          {s.error_message && (
            <p className="text-xs text-red-400 mt-1">{s.error_message}</p>
          )}
        </li>
      ))}
    </ol>
  )
}
