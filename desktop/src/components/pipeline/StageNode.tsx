import type { LucideIcon } from 'lucide-react'

type StageStatus = 'completed' | 'processing' | 'pending' | 'failed'

interface StageNodeProps {
  name: string
  icon: LucideIcon
  completed: number
  total: number
  status: StageStatus
  failedCount?: number
  isExpanded: boolean
  onClick: () => void
}

const STATUS_COLORS: Record<StageStatus, string> = {
  completed: 'var(--green)',
  processing: 'var(--yellow)',
  pending: 'var(--border)',
  failed: 'var(--red)',
}

export default function StageNode({
  name,
  icon: Icon,
  completed,
  total,
  status,
  failedCount = 0,
  isExpanded,
  onClick,
}: StageNodeProps) {
  const pct = total === 0 ? 0 : Math.round((completed / total) * 100)
  const borderColor = STATUS_COLORS[status]
  const pendingCount = Math.max(0, total - completed - failedCount)
  const statusText = (
    status === 'failed'
      ? `${failedCount} lỗi`
      : status === 'completed'
        ? `${pct}% hoàn tất`
        : status === 'processing'
          ? `${completed}/${total} đã xong`
          : `${pendingCount} đang chờ`
  )

  return (
    <button
      onClick={onClick}
      className="flex flex-col gap-2 p-3 rounded text-left transition-opacity hover:opacity-90 flex-1 min-w-0"
      style={{
        background: 'var(--card)',
        border: `1px solid var(--border)`,
        borderLeft: `3px solid ${borderColor}`,
        outline: isExpanded ? `1px solid ${borderColor}` : 'none',
      }}
    >
      <div className="flex items-center gap-2">
        <Icon size={14} style={{ color: borderColor }} />
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
          {name}
        </span>
        {status === 'processing' && (
          <span
            className="ml-auto inline-block w-1.5 h-1.5 rounded-full"
            style={{ background: 'var(--yellow)', animation: 'pulse 1.5s ease-in-out infinite' }}
          />
        )}
      </div>

      <div className="text-xl font-bold" style={{ color: 'var(--text)' }}>
        {completed}
        <span className="text-sm font-normal" style={{ color: 'var(--muted)' }}>
          /{total}
        </span>
      </div>

      <div className="w-full rounded-full overflow-hidden" style={{ background: 'var(--border)', height: '3px' }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: borderColor }}
        />
      </div>

      <div className="text-xs" style={{ color: 'var(--muted)' }}>{statusText}</div>
    </button>
  )
}
