import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchAPI } from '../../api/client'
import { Progress } from './progress'
import { Badge } from './badge'
import { ChevronDown, ChevronRight, AlertCircle } from 'lucide-react'

interface BatchStatus {
    total: number
    pending: number
    queued_pending: number
    retry_waiting: number
    processing: number
    completed: number
    failed: number
    done: boolean
    all_succeeded?: boolean
    next_retry_at?: string | null
    next_retry_in_sec?: number | null
    status_hint?: string | null
    oldest_processing_sec?: number | null
}

interface FailedRequest {
    id: string
    scene_id: string | null
    character_id: string | null
    type: string
    error_message: string
    retry_count: number
}

interface BatchStatusBarProps {
    videoId: string
    type: string
    label: string
    lastEventType?: string | null
    orientation?: string
}

export default function BatchStatusBar({ videoId, type, label, lastEventType, orientation }: BatchStatusBarProps) {
    const [status, setStatus] = useState<BatchStatus | null>(null)
    const [failedList, setFailedList] = useState<FailedRequest[]>([])
    const [expanded, setExpanded] = useState(false)
    const prevFailedRef = useRef(0)

    const poll = useCallback(async () => {
        try {
            const params = new URLSearchParams({ video_id: videoId, type })
            if (orientation) params.set('orientation', orientation)
            const s = await fetchAPI<BatchStatus>(`/api/requests/batch-status?${params.toString()}`)
            setStatus(s)

            // Fetch failed details if there are failures
            if (s.failed > 0) {
                const fParams = new URLSearchParams({ video_id: videoId, type })
                if (orientation) fParams.set('orientation', orientation)
                const failed = await fetchAPI<FailedRequest[]>(`/api/requests/failed?${fParams.toString()}`)
                setFailedList(failed)

                // Auto-expand if new failures appeared
                if (s.failed > prevFailedRef.current) {
                    setExpanded(true)
                }
                prevFailedRef.current = s.failed
            } else {
                setFailedList([])
                prevFailedRef.current = 0
            }
        } catch { /* ignore */ }
    }, [videoId, type, orientation])

    useEffect(() => {
        poll()
        const timer = setInterval(() => { poll() }, 3000)
        return () => clearInterval(timer)
    }, [poll])

    useEffect(() => {
        if (lastEventType) poll()
    }, [lastEventType, poll])

    if (!status || status.total === 0) return null

    const pct = Math.round((status.completed / status.total) * 100)

    const badgeVariant = status.failed > 0
        ? 'destructive'
        : status.done
            ? 'success'
            : 'secondary'

    const badgeLabel = status.failed > 0
        ? `${status.completed}/${status.total} — ${status.failed} lỗi`
        : `${status.completed}/${status.total} (${pct}%)`

    const formatSeconds = (s?: number | null) => {
        if (!s || s <= 0) return 'ngay bây giờ'
        const m = Math.floor(s / 60)
        const sec = s % 60
        return m > 0 ? `${m}m ${sec}s` : `${sec}s`
    }

    const detailParts: string[] = []
    if (status.processing > 0) detailParts.push(`Đang xử lý: ${status.processing}`)
    if (status.queued_pending > 0) detailParts.push(`Trong hàng đợi: ${status.queued_pending}`)
    if (status.retry_waiting > 0) detailParts.push(`Đang chờ retry: ${status.retry_waiting}`)
    const detailText = detailParts.join(' • ')
    const hintClass = (() => {
        const text = (status.status_hint || '').toLowerCase()
        if (!text) return 'text-[10px] leading-tight'
        if (text.includes('captcha') || text.includes('lỗi') || text.includes('error')) return 'text-[10px] text-red-600 leading-tight'
        if (text.includes('retry')) return 'text-[10px] text-amber-600 leading-tight'
        return 'text-[10px] text-[hsl(var(--muted-foreground))] leading-tight'
    })()

    return (
        <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
                <span className="text-xs text-[hsl(var(--muted-foreground))]">{label}</span>
                <div className="flex items-center gap-1.5">
                    {status.failed > 0 && (
                        <button
                            onClick={() => setExpanded(v => !v)}
                            className="flex items-center gap-0.5 text-[10px] text-red-500 hover:text-red-700 font-medium"
                        >
                            {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                            Chi tiết lỗi
                        </button>
                    )}
                    <Badge variant={badgeVariant as 'destructive' | 'success' | 'secondary'} className="text-xs">
                        {badgeLabel}
                    </Badge>
                </div>
            </div>
            <Progress value={pct} className={status.failed > 0 ? '[&>div]:bg-red-500' : status.done ? '[&>div]:bg-green-500' : ''} />
            {(detailText || status.status_hint) && (
                <div className="flex flex-col gap-0.5 mt-0.5">
                    {detailText && (
                        <div className="text-[10px] text-[hsl(var(--muted-foreground))]">{detailText}</div>
                    )}
                    {status.retry_waiting > 0 && (
                        <div className="text-[10px] text-amber-600">
                            Retry tiếp theo sau khoảng {formatSeconds(status.next_retry_in_sec)}
                        </div>
                    )}
                    {status.processing > 0 && (status.oldest_processing_sec ?? 0) > 0 && (
                        <div className="text-[10px] text-[hsl(var(--muted-foreground))]">
                            Request xử lý lâu nhất: {formatSeconds(status.oldest_processing_sec)}
                        </div>
                    )}
                    {status.status_hint && (
                        <div className={hintClass}>{status.status_hint}</div>
                    )}
                </div>
            )}

            {/* Expanded failed list */}
            {expanded && failedList.length > 0 && (
                <div className="flex flex-col gap-1 mt-1 p-2 rounded-md bg-red-50 border border-red-200">
                    <div className="flex items-center gap-1.5 text-[10px] font-semibold text-red-700 uppercase tracking-wider">
                        <AlertCircle size={10} /> Danh sách lỗi ({failedList.length})
                    </div>
                    {failedList.map(f => (
                        <div key={f.id} className="flex flex-col gap-0.5 text-[11px] border-t border-red-100 pt-1 first:border-0 first:pt-0">
                            <div className="flex items-center gap-1 text-red-800 font-medium">
                                <span className="font-mono text-[10px] text-red-400">
                                    {f.scene_id ? `Scene …${f.scene_id.slice(-6)}` : f.character_id ? `Char …${f.character_id.slice(-6)}` : f.id.slice(-6)}
                                </span>
                                {f.retry_count > 0 && (
                                    <span className="text-[9px] text-red-400">(thử {f.retry_count + 1} lần)</span>
                                )}
                            </div>
                            <div className="text-red-600 leading-tight">{f.error_message}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
