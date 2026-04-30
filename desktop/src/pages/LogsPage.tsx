import { useState } from 'react'
import LogViewer from '../components/logs/LogViewer'
import StatusDashboard from '../components/logs/StatusDashboard'

export default function LogsPage() {
  const [tab, setTab] = useState<'status' | 'logs'>('status')

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setTab('status')}
          className="px-3 py-1.5 rounded text-xs font-semibold"
          style={{
            background: tab === 'status' ? 'var(--accent)' : 'var(--card)',
            color: tab === 'status' ? '#fff' : 'var(--muted)',
            border: '1px solid var(--border)',
          }}
        >
          Bảng trạng thái
        </button>
        <button
          onClick={() => setTab('logs')}
          className="px-3 py-1.5 rounded text-xs font-semibold"
          style={{
            background: tab === 'logs' ? 'var(--accent)' : 'var(--card)',
            color: tab === 'logs' ? '#fff' : 'var(--muted)',
            border: '1px solid var(--border)',
          }}
        >
          Nhật ký trực tiếp
        </button>
      </div>
      <div className="flex-1 min-h-0">
        {tab === 'status' ? <StatusDashboard /> : <LogViewer />}
      </div>
    </div>
  )
}
