import { useEffect, useMemo, useState } from 'react'
import { Download, Music, RefreshCw, Scissors, VolumeX, Waves } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface Props {
    videoId: string
    projectId: string
    onClose: () => void
}

interface TemplateItem {
    id: string
    name: string
    category?: string
    description?: string
}

interface TaskClip {
    id: string
    title?: string
    audioUrl?: string
    audio_url?: string
    duration?: number
}

const MODELS = ['V4', 'V4_5', 'V4_5PLUS', 'V4_5ALL', 'V5', 'V5_5']

function extractClips(task: any): TaskClip[] {
    const response = task?.response ?? task?.task?.response ?? {}
    const clips = response?.sunoData || response?.data || task?.clips || []
    return Array.isArray(clips) ? clips : []
}

function extractLyrics(task: any): string {
    const response = task?.response ?? task?.task?.response ?? task ?? {}
    const candidates = [
        response?.lyrics,
        response?.lyric,
        response?.text,
        response?.content,
        response?.data?.lyrics,
        response?.data?.text,
    ]
    for (const c of candidates) {
        if (typeof c === 'string' && c.trim()) return c.trim()
    }
    return ''
}

export default function MusicModal({ projectId, onClose }: Props) {
    const [templates, setTemplates] = useState<TemplateItem[]>([])
    const [templateId, setTemplateId] = useState('')

    const [prompt, setPrompt] = useState('')
    const [style, setStyle] = useState('')
    const [title, setTitle] = useState('')
    const [customMode, setCustomMode] = useState(true)
    const [instrumental, setInstrumental] = useState(true)
    const [model, setModel] = useState('V4')

    const [taskId, setTaskId] = useState('')
    const [task, setTask] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const [extendPrompt, setExtendPrompt] = useState('')
    const [continueAt, setContinueAt] = useState('')

    const [credits, setCredits] = useState<any>(null)
    const [lyricsText, setLyricsText] = useState('')

    const clips = useMemo(() => extractClips(task), [task])

    const loadMeta = async () => {
        const [tpls, cre] = await Promise.all([
            fetchAPI<TemplateItem[]>('/api/music/templates').catch(() => []),
            fetchAPI<any>('/api/music/credits').catch(() => null),
        ])
        setTemplates(tpls)
        setCredits(cre)
        if (!templateId && tpls[0]) setTemplateId(tpls[0].id)
    }

    useEffect(() => {
        loadMeta().catch(() => { })
    }, [])

    const refreshTask = async (id = taskId) => {
        if (!id) return
        const t = await fetchAPI<any>(`/api/music/tasks/${id}`)
        setTask(t)
        setTaskId(id)
        setLyricsText(extractLyrics(t))
    }

    const generate = async () => {
        setLoading(true)
        setError('')
        setTask(null)
        try {
            const r = await fetchAPI<{ task_id: string; task?: any }>('/api/music/generate', {
                method: 'POST',
                body: JSON.stringify({
                    prompt: prompt.trim(),
                    style: style.trim(),
                    title: title.trim(),
                    instrumental,
                    model,
                    custom_mode: customMode,
                    template_id: templateId || undefined,
                    poll: false,
                }),
            })
            setTaskId(r.task_id)
            await refreshTask(r.task_id)
        } catch (e: any) {
            setError(e.message ?? 'Tạo nhạc thất bại')
        } finally {
            setLoading(false)
        }
    }

    const generateLyricsOnly = async () => {
        if (!prompt.trim()) return
        setLoading(true)
        setError('')
        setTask(null)
        setLyricsText('')
        try {
            const r = await fetchAPI<{ task_id: string }>('/api/music/generate-lyrics', {
                method: 'POST',
                body: JSON.stringify({
                    prompt: prompt.trim(),
                    template_id: templateId || undefined,
                    poll: false,
                }),
            })
            setTaskId(r.task_id)
            await refreshTask(r.task_id)
        } catch (e: any) {
            setError(e.message ?? 'Tạo lời thất bại')
        } finally {
            setLoading(false)
        }
    }

    const pollUntilDone = async () => {
        if (!taskId) return
        setLoading(true)
        setError('')
        try {
            const r = await fetchAPI<any>(`/api/music/tasks/${taskId}/poll`, { method: 'POST' })
            setTask(r)
        } catch (e: any) {
            setError(e.message ?? 'Lấy trạng thái thất bại')
        } finally {
            setLoading(false)
        }
    }

    const downloadAll = async () => {
        if (!taskId) return
        setLoading(true)
        setError('')
        try {
            const r = await fetchAPI<any>(`/api/music/tasks/${taskId}/download?project_id=${projectId}`, { method: 'POST' })
            const n = r?.downloaded?.length ?? 0
            setError('')
            alert(`Đã tải ${n} clip vào thư mục nhạc của dự án.`)
        } catch (e: any) {
            setError(e.message ?? 'Tải xuống thất bại')
        } finally {
            setLoading(false)
        }
    }

    const extendClip = async (audioId: string) => {
        setLoading(true)
        setError('')
        try {
            const r = await fetchAPI<{ task_id: string }>('/api/music/extend', {
                method: 'POST',
                body: JSON.stringify({
                    audio_id: audioId,
                    prompt: extendPrompt.trim(),
                    continue_at: continueAt.trim() ? Number(continueAt) : undefined,
                    model,
                    poll: false,
                }),
            })
            setTaskId(r.task_id)
            await refreshTask(r.task_id)
        } catch (e: any) {
            setError(e.message ?? 'Mở rộng clip thất bại')
        } finally {
            setLoading(false)
        }
    }

    const vocalRemoval = async (audioId: string) => {
        if (!taskId) return
        setLoading(true)
        setError('')
        try {
            const r = await fetchAPI<{ task_id: string }>('/api/music/vocal-removal', {
                method: 'POST',
                body: JSON.stringify({ task_id: taskId, audio_id: audioId, poll: false }),
            })
            setTaskId(r.task_id)
            await refreshTask(r.task_id)
        } catch (e: any) {
            setError(e.message ?? 'Tách vocal thất bại')
        } finally {
            setLoading(false)
        }
    }

    const convertWav = async (audioId: string) => {
        if (!taskId) return
        setLoading(true)
        setError('')
        try {
            const r = await fetchAPI<{ task_id: string }>('/api/music/convert-to-wav', {
                method: 'POST',
                body: JSON.stringify({ task_id: taskId, audio_id: audioId, poll: false }),
            })
            setTaskId(r.task_id)
            await refreshTask(r.task_id)
        } catch (e: any) {
            setError(e.message ?? 'Chuyển WAV thất bại')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Studio Nhạc (fk:gen-music parity)" onClose={onClose} width={820}>
            <div className="flex flex-col gap-4">
                <div className="flex flex-wrap gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                    <span>Tác vụ: {taskId || '-'}</span>
                    <span>Trạng thái: {task?.status ?? '-'}</span>
                    {credits && <span>Credits: {JSON.stringify(credits)}</span>}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                        <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Mẫu / Model</div>
                        <select className="input" value={templateId} onChange={e => setTemplateId(e.target.value)}>
                            <option value="">Không dùng mẫu</option>
                            {templates.map(t => (
                                <option key={t.id} value={t.id}>{t.name} {t.category ? `(${t.category})` : ''}</option>
                            ))}
                        </select>
                        <select className="input" value={model} onChange={e => setModel(e.target.value)}>
                            {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                        </select>
                        <label className="text-xs inline-flex items-center gap-2" style={{ color: 'var(--text)' }}>
                            <input type="checkbox" checked={customMode} onChange={e => setCustomMode(e.target.checked)} /> chế độ custom
                        </label>
                        <label className="text-xs inline-flex items-center gap-2" style={{ color: 'var(--text)' }}>
                            <input type="checkbox" checked={instrumental} onChange={e => setInstrumental(e.target.checked)} /> nhạc không lời
                        </label>
                    </div>

                    <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                        <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Tạo nhạc</div>
                        <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="Tiêu đề" />
                        <input className="input" value={style} onChange={e => setStyle(e.target.value)} placeholder="Tag phong cách (tùy chọn)" />
                        <textarea
                            className="input resize-none"
                            rows={4}
                            value={prompt}
                            onChange={e => setPrompt(e.target.value)}
                            placeholder="Lời bài hát (chế độ custom) hoặc mô tả bằng ngôn ngữ tự nhiên"
                        />
                        <div className="flex gap-2">
                            <ActionButton variant="primary" size="sm" onClick={generate} disabled={loading || !prompt.trim()}>
                                <Music size={12} /> Tạo nhạc
                            </ActionButton>
                            <ActionButton variant="ghost" size="sm" onClick={generateLyricsOnly} disabled={loading || !prompt.trim()}>
                                <Waves size={12} /> Chỉ tạo lời
                            </ActionButton>
                            <ActionButton variant="ghost" size="sm" onClick={() => refreshTask()} disabled={loading || !taskId}>
                                <RefreshCw size={12} /> Kiểm tra tác vụ
                            </ActionButton>
                            <ActionButton variant="ghost" size="sm" onClick={pollUntilDone} disabled={loading || !taskId}>
                                <Waves size={12} /> Theo dõi đến khi xong
                            </ActionButton>
                            <ActionButton variant="secondary" size="sm" onClick={downloadAll} disabled={loading || !taskId}>
                                <Download size={12} /> Tải clips
                            </ActionButton>
                        </div>
                    </div>
                </div>

                <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Tuỳ chọn mở rộng</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <input className="input" value={extendPrompt} onChange={e => setExtendPrompt(e.target.value)} placeholder="Prompt mở rộng" />
                        <input className="input" value={continueAt} onChange={e => setContinueAt(e.target.value)} placeholder="Tiếp tục từ giây (tùy chọn)" />
                    </div>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}
                {lyricsText && (
                    <div className="rounded p-3 flex flex-col gap-1 text-xs" style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.25)' }}>
                        <div style={{ color: 'var(--muted)' }}>Lời bài hát đã tạo</div>
                        <textarea
                            className="input resize-y"
                            rows={5}
                            value={lyricsText}
                            onChange={e => setLyricsText(e.target.value)}
                        />
                    </div>
                )}

                <div className="grid gap-3 max-h-[320px] overflow-y-auto" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
                    {clips.map((clip: TaskClip) => {
                        const audio = clip.audioUrl || clip.audio_url
                        return (
                            <div key={clip.id} className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                                <div className="text-xs font-semibold" style={{ color: 'var(--text)' }}>{clip.title || clip.id}</div>
                                {audio ? <audio controls src={audio} className="w-full" style={{ height: 30 }} /> : <div className="text-xs" style={{ color: 'var(--muted)' }}>Chưa có URL audio</div>}
                                <div className="flex flex-wrap gap-1.5">
                                    <ActionButton variant="ghost" size="sm" onClick={() => extendClip(clip.id)} disabled={loading}><Scissors size={10} /> Mở rộng</ActionButton>
                                    <ActionButton variant="ghost" size="sm" onClick={() => vocalRemoval(clip.id)} disabled={loading}><VolumeX size={10} /> Xóa vocal</ActionButton>
                                    <ActionButton variant="ghost" size="sm" onClick={() => convertWav(clip.id)} disabled={loading}><Waves size={10} /> WAV</ActionButton>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>
        </Modal>
    )
}
