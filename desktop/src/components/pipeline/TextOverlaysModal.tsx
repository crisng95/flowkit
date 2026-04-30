import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface OverlayItem {
    text: string
    style: 'date' | 'name' | 'stat' | 'cost'
}

interface Result {
    project_id: string
    video_id: string
    language: string
    scenes_total: number
    scenes_with_overlays: number
    items_total: number
    output_path: string
    overlays: Record<string, OverlayItem[]>
}

interface Props {
    videoId: string
    onClose: () => void
}

const LANG_OPTIONS = [
    { value: '', label: 'Auto detect' },
    { value: 'vi', label: 'Vietnamese' },
    { value: 'en', label: 'English' },
    { value: 'es', label: 'Spanish' },
]

export default function TextOverlaysModal({ videoId, onClose }: Props) {
    const [language, setLanguage] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [result, setResult] = useState<Result | null>(null)

    const run = async () => {
        setLoading(true)
        setError('')
        setResult(null)
        try {
            const r = await fetchAPI<Result>(`/api/workflows/videos/${videoId}/text-overlays`, {
                method: 'POST',
                body: JSON.stringify({ language: language || undefined }),
            })
            setResult(r)
        } catch (e: any) {
            setError(e.message ?? 'Failed to generate text overlays')
        } finally {
            setLoading(false)
        }
    }

    const rows = Object.entries(result?.overlays ?? {}).sort((a, b) => Number(a[0]) - Number(b[0]))

    return (
        <Modal title="Generate Text Overlays (fk:gen-text-overlays)" onClose={onClose} width={700}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Phân tích <code>narrator_text</code> của từng scene và tạo <code>text_overlays.json</code> cho flow concat-fit-narrator.
                </div>

                <div className="flex items-center gap-2">
                    <select value={language} onChange={e => setLanguage(e.target.value)} className="input" style={{ maxWidth: 220 }}>
                        {LANG_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <ActionButton variant="primary" onClick={run} disabled={loading}>
                        <Sparkles size={12} /> {loading ? 'Generating...' : 'Generate'}
                    </ActionButton>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {result && (
                    <>
                        <div className="rounded p-3 text-xs flex flex-wrap gap-x-4 gap-y-1" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <span><strong>Language:</strong> {result.language}</span>
                            <span><strong>Coverage:</strong> {result.scenes_with_overlays}/{result.scenes_total} scenes</span>
                            <span><strong>Items:</strong> {result.items_total}</span>
                            <span><strong>Output:</strong> {result.output_path}</span>
                        </div>

                        <div className="max-h-[360px] overflow-y-auto rounded" style={{ border: '1px solid var(--border)' }}>
                            <table className="w-full text-xs">
                                <thead style={{ background: 'var(--surface-alt)', color: 'var(--muted)' }}>
                                    <tr>
                                        <th className="text-left px-3 py-2">Scene</th>
                                        <th className="text-left px-3 py-2">Style</th>
                                        <th className="text-left px-3 py-2">Text</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows.flatMap(([sceneOrder, items]) =>
                                        items.map((item, idx) => (
                                            <tr key={`${sceneOrder}-${idx}`} style={{ borderTop: '1px solid var(--border)' }}>
                                                <td className="px-3 py-2" style={{ color: 'var(--muted)' }}>#{Number(sceneOrder) + 1}</td>
                                                <td className="px-3 py-2"><code>{item.style}</code></td>
                                                <td className="px-3 py-2" style={{ color: 'var(--text)' }}>{item.text}</td>
                                            </tr>
                                        )),
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </div>
        </Modal>
    )
}
