import { clsx } from 'clsx'

const colors: Record<string, string> = {
  pending: 'bg-gray-700 text-gray-300',
  running: 'bg-blue-900 text-blue-300 animate-pulse',
  paused: 'bg-yellow-900 text-yellow-300',
  completed: 'bg-green-900 text-green-300',
  failed: 'bg-red-900 text-red-300',
  cancelled: 'bg-gray-800 text-gray-400',
  skipped: 'bg-gray-800 text-gray-500',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx('px-2 py-0.5 rounded text-xs font-semibold uppercase', colors[status] ?? 'bg-gray-700 text-gray-300')}>
      {status}
    </span>
  )
}
