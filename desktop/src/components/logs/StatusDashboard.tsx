import { useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface ProjectSummary {
    id: string
    name: string
    status: string
    tier: string | null
    orientation: string
    material: string
    video_count: number
    created_at: string
}

interface ProjectStatus {
    project: { id: string; name: string; status: string; material: string }
    video: { id: string; title: string; orientation: string }
    counts: {
        refs_done: number
        refs_total: number
        images_done: number
        images_total: number
        videos_done: number
        videos_total: number
        upscales_done: number
        upscales_total: number
        tts_done?: number
        tts_total?: number
        downloads_done?: number
        downloads_total?: number
    }
    queue: { pending: number; processing: number; failed: number }
    characters: Array<{ id: string; name: string; entity_type: string; ready: boolean; media_id: string | null }>
    scenes: Array<{
        id: string
        display_order: number
        prompt: string | null
        narrator_text?: string | null
        image_status: string
        video_status: string
        upscale_status: string
        tts_status?: string
        tts_audio_path?: string | null
        download_ready?: boolean
        download_path?: string | null
    }>
    suggested_next_action: string
}

function CountPill({ label, value }: { label: string; value: string }) {
    return (
        <span className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs" style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
            <strong>{label}</strong> {value}
        </span>
    )
}

export default function StatusDashboard() {
    const [projects, setProjects] = useState<ProjectSummary[]>([])
    const [projectId, setProjectId] = useState('')
    const [status, setStatus] = useState<ProjectStatus | null>(null)
    const [autoRefresh, setAutoRefresh] = useState(true)
    const [error, setError] = useState('')

    const loadProjects = async () => {
        const res = await fetchAPI<{ projects: ProjectSummary[] }>('/api/workflows/status')
        setProjects(res.projects)
        if (!projectId && res.projects[0]) setProjectId(res.projects[0].id)
    }

    const loadStatus = async () => {
        if (!projectId) return
        const res = await fetchAPI<ProjectStatus>(`/api/workflows/status?project_id=${projectId}`)
        setStatus(res)
    }

    useEffect(() => {
        loadProjects().catch((e: any) => setError(e.message ?? 'Không tải được danh sách dự án'))
    }, [])

    useEffect(() => {
        loadStatus().catch((e: any) => setError(e.message ?? 'Không tải được trạng thái'))
    }, [projectId])

    useEffect(() => {
        if (!autoRefresh) return
        const timer = setInterval(() => {
            Promise.all([loadProjects(), loadStatus()]).catch(() => { })
        }, 10000)
        return () => clearInterval(timer)
    }, [autoRefresh, projectId])

    const sceneRows = useMemo(() => (status?.scenes ?? []).slice(0, 80), [status])

    return (
        <div className="flex flex-col gap-3 h-full">
            <div className="flex flex-wrap items-center gap-2">
                <select value={projectId} onChange={e => setProjectId(e.target.value)} className="input" style={{ maxWidth: 320 }}>
                    <option value="">Chọn dự án...</option>
                    {projects.map(p => (
                        <option key={p.id} value={p.id}>{p.name} · {p.status}</option>
                    ))}
                </select>

                <ActionButton variant="ghost" size="sm" onClick={() => Promise.all([loadProjects(), loadStatus()]).catch(() => { })}>
                    <RefreshCw size={11} /> Tải lại
                </ActionButton>

                <label className="text-xs inline-flex items-center gap-1" style={{ color: 'var(--muted)' }}>
                    <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} /> tự làm mới (10s)
                </label>

                <div className="flex-1" />
                <ActionButton variant="ghost" size="sm" onClick={async () => {
                    if (!projectId) return
                    await fetchAPI('/api/active-project', { method: 'PUT', body: JSON.stringify({ project_id: projectId }) })
                }}>
                    Đặt đang dùng
                </ActionButton>
                <ActionButton variant="ghost" size="sm" onClick={async () => {
                    await fetchAPI('/api/active-project', { method: 'DELETE' })
                }}>
                    Bỏ đang dùng
                </ActionButton>
            </div>

            {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

            {status && (
                <div className="flex flex-col gap-2">
                    <div className="text-xs font-semibold" style={{ color: 'var(--text)' }}>
                        {status.project.name} · {status.video.title} · {status.video.orientation}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <CountPill label="Ref" value={`${status.counts.refs_done}/${status.counts.refs_total}`} />
                        <CountPill label="Ảnh" value={`${status.counts.images_done}/${status.counts.images_total}`} />
                        <CountPill label="Video" value={`${status.counts.videos_done}/${status.counts.videos_total}`} />
                        <CountPill label="Upscale" value={`${status.counts.upscales_done}/${status.counts.upscales_total}`} />
                        {typeof status.counts.tts_total === 'number' && (
                            <CountPill label="TTS" value={`${status.counts.tts_done ?? 0}/${status.counts.tts_total}`} />
                        )}
                        {typeof status.counts.downloads_total === 'number' && (
                            <CountPill label="4K DL" value={`${status.counts.downloads_done ?? 0}/${status.counts.downloads_total}`} />
                        )}
                        <CountPill label="Hàng đợi" value={`${status.queue.pending} chờ / ${status.queue.processing} chạy / ${status.queue.failed} lỗi`} />
                        <CountPill label="Bước kế tiếp" value={status.suggested_next_action} />
                    </div>
                </div>
            )}

            <div className="grid gap-3 min-h-0 flex-1" style={{ gridTemplateColumns: '1fr 2fr' }}>
                <div className="rounded p-2 overflow-auto" style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
                    <div className="text-xs font-semibold mb-2" style={{ color: 'var(--muted)' }}>Thực thể</div>
                    <div className="flex flex-col gap-1">
                        {(status?.characters ?? []).map(c => (
                            <div key={c.id} className="text-xs rounded px-2 py-1" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                <div style={{ color: 'var(--text)' }}>{c.name}</div>
                                <div style={{ color: c.ready ? 'var(--green)' : 'var(--red)' }}>{c.ready ? 'Sẵn sàng' : 'Thiếu media_id'}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="rounded overflow-auto" style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
                    <table className="w-full text-xs">
                        <thead style={{ background: 'var(--surface-alt)', color: 'var(--muted)' }}>
                            <tr>
                                <th className="text-left px-3 py-2">#</th>
                                <th className="text-left px-3 py-2">Prompt</th>
                                <th className="text-left px-3 py-2">Ảnh</th>
                                <th className="text-left px-3 py-2">Video</th>
                                <th className="text-left px-3 py-2">TTS</th>
                                <th className="text-left px-3 py-2">Upscale</th>
                                <th className="text-left px-3 py-2">Local</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sceneRows.map(s => (
                                <tr key={s.id} style={{ borderTop: '1px solid var(--border)' }}>
                                    <td className="px-3 py-2" style={{ color: 'var(--muted)' }}>#{s.display_order + 1}</td>
                                    <td className="px-3 py-2" style={{ color: 'var(--text)' }}>{(s.prompt ?? '').slice(0, 72)}</td>
                                    <td className="px-3 py-2">{s.image_status}</td>
                                    <td className="px-3 py-2">{s.video_status}</td>
                                    <td className="px-3 py-2" title={s.tts_audio_path ?? ''}>{s.tts_status ?? ((s.narrator_text ?? '').trim() ? 'PENDING' : 'SKIPPED')}</td>
                                    <td className="px-3 py-2">{s.upscale_status}</td>
                                    <td className="px-3 py-2" title={s.download_path ?? ''}>{s.download_ready ? 'READY' : '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
