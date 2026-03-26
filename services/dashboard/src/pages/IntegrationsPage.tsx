import { useQuery } from '@tanstack/react-query'
import { connectorsApi } from '../api/connectors'
import { StatusBadge } from '../components/StatusBadge'

const CONNECTORS = ['github', 'slack', 'jira', 'confluence', 'aws']

export default function IntegrationsPage() {
  const { data: connectors } = useQuery({
    queryKey: ['connectors'],
    queryFn: connectorsApi.list,
  })

  const enabledMap = Object.fromEntries((connectors ?? []).map((c) => [c.type, c]))

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-6">Integrations</h1>
      <div className="space-y-3">
        {CONNECTORS.map((type) => {
          const c = enabledMap[type]
          return (
            <div key={type} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-white capitalize">{type}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {c ? 'Configured' : 'Not configured'}
                </p>
              </div>
              <StatusBadge status={c?.enabled ? 'completed' : 'pending'} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
