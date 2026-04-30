/**
 * YouTubeUploadModal
 * Configures YouTube channel credentials and triggers upload.
 * Corresponds to CLI skill: fk:youtube-upload
 */
import { useState } from 'react'
import { Tv2, ExternalLink } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface Props {
    videoId: string
    projectId: string
    videoPath?: string
    onClose: () => void
}

const PRIVACY_OPTIONS = ['private', 'unlisted', 'public'] as const
type Privacy = typeof PRIVACY_OPTIONS[number]

export default function YouTubeUploadModal({ videoId, projectId, videoPath, onClose }: Props) {
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [tags, setTags] = useState('')
    const [privacy, setPrivacy] = useState<Privacy>('private')
    const [status, setStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
    const [result, setResult] = useState<{ url?: string; video_id?: string } | null>(null)
    const [error, setError] = useState('')

    const upload = async () => {
        if (!title.trim()) { setError('Tiêu đề là bắt buộc'); return }
        setStatus('uploading'); setError('')
        try {
            const r = await fetchAPI<{ url?: string; video_id?: string }>('/api/youtube/upload', {
                method: 'POST',
                body: JSON.stringify({
                    project_id: projectId,
                    video_id: videoId,
                    video_path: videoPath,
                    title: title.trim(),
                    description: description.trim(),
                    tags: tags.split(',').map(t => t.trim()).filter(Boolean),
                    privacy_status: privacy,
                }),
            })
            setResult(r)
            setStatus('done')
        } catch (err: any) {
            setStatus('error')
            setError(err.message)
        }
    }

    return (
        <Modal title="Tải Lên YouTube" onClose={onClose} width={520}>
            <div className="flex flex-col gap-4">
                {/* Warning about credentials */}
                <div className="rounded p-3 text-xs" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', color: 'var(--yellow)' }}>
                    ⚠ Cần cấu hình thông tin YouTube OAuth trong agent (<code>youtube/channels/</code>).
                    Xem hướng dẫn <a href="#" className="underline">fk:youtube-upload</a>.
                </div>

                <div className="flex flex-col gap-3">
                    <Field label="Tiêu đề *">
                        <input value={title} onChange={e => setTitle(e.target.value)} className="input" placeholder="Tiêu đề video (tối đa 100 ký tự)" maxLength={100} />
                        <span className="text-xs text-right" style={{ color: 'var(--muted)' }}>{title.length}/100</span>
                    </Field>
                    <Field label="Mô tả">
                        <textarea value={description} onChange={e => setDescription(e.target.value)} className="input resize-y" rows={4} placeholder="Mô tả video..." />
                    </Field>
                    <Field label="Tags (ngăn cách bằng dấu phẩy)">
                        <input value={tags} onChange={e => setTags(e.target.value)} className="input" placeholder="documentary, history, vietnam, ..." />
                    </Field>
                    <Field label="Quyền riêng tư">
                        <div className="flex gap-2">
                            {PRIVACY_OPTIONS.map(p => (
                                <button key={p} onClick={() => setPrivacy(p)}
                                    className="flex-1 px-3 py-1.5 rounded text-xs font-semibold capitalize"
                                    style={{
                                        background: privacy === p ? 'var(--accent)' : 'var(--card)',
                                        color: privacy === p ? '#fff' : 'var(--muted)',
                                        border: '1px solid var(--border)',
                                    }}>
                                    {p}
                                </button>
                            ))}
                        </div>
                    </Field>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {status === 'uploading' && (
                    <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                        <div className="w-4 h-4 rounded-full border border-current animate-spin" style={{ borderTopColor: 'transparent' }} />
                        Đang upload lên YouTube... có thể mất vài phút
                    </div>
                )}

                {status === 'done' && result && (
                    <div className="flex flex-col gap-2 text-xs p-3 rounded" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}>
                        <div>✓ Upload hoàn tất!</div>
                        {result.url && (
                            <a href={result.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:underline" style={{ color: 'var(--accent)' }}>
                                <ExternalLink size={11} /> Mở trên YouTube →
                            </a>
                        )}
                    </div>
                )}

                <div className="flex justify-end gap-2">
                    <ActionButton variant="ghost" onClick={onClose}>Hủy</ActionButton>
                    <ActionButton variant="primary" onClick={upload} disabled={status === 'uploading'}>
                        <Tv2 size={12} /> Tải lên
                    </ActionButton>
                </div>
            </div>
        </Modal>
    )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>{label}</label>
            {children}
        </div>
    )
}
