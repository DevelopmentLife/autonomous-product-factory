import { useAuthStore } from '../stores/authStore'

export default function SettingsPage() {
  const username = useAuthStore((s) => s.username)
  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Logged in as</label>
          <p className="text-white font-medium">{username}</p>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">API URL</label>
          <p className="text-gray-300 text-sm font-mono">/api/v1</p>
        </div>
      </div>
    </div>
  )
}
