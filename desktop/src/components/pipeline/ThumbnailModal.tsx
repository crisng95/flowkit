/**
 * ThumbnailModal
 * Generates 4 YouTube-optimized thumbnail variants via POST /api/projects/{pid}/generate-thumbnail
 * Corresponds to CLI skill: fk:thumbnail
 */
import { useState } from 'react'
import { ImageIcon, Download } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface ThumbnailResult {
    image_url?: string
    output_path?: string
    // backward-compatible aliases
    url?: string
    local_path?: string
    prompt?: string
}

interface Props {
    projectId: string
    projectName: string
    onClose: () => void
}

const THUMBNAIL_STYLES = [
    { id: 'dramatic', label: '🎬 Dramatic', prompt: 'Epic cinematic thumbnail, bold text overlay space, high contrast, dramatic lighting' },
    { id: 'emotional', label: '😢 Emotional', prompt: 'Emotionally charged scene, soft warm tones, human element prominent' },
    { id: 'action', label: '⚔️ Action', prompt: 'High-energy action shot, motion blur, intense close-up, power feel' },
    { id: 'reveal', label: '🌅 Reveal', prompt: 'Wide establishing shot, epic scale, reveals scope of story' },
]

export default function ThumbnailModal({ projectId, projectName, onClose }: Props) {
    const [prompt, setPrompt] = useState('')
    const [results, setResults] = useState<{ style: string; result: ThumbnailResult | null; error?: string }[]>([])
    const [loading, setLoading] = useState<string | null>(null)
    const [activeStyle, setActiveStyle] = useState<string | null>(null)

    const generate = async (styleId: string, stylePrompt: string) => {
        setLoading(styleId); setActiveStyle(styleId)
        const fullPrompt = `${stylePrompt}${prompt ? `. ${prompt}` : ''}`
        try {
            const r = await fetchAPI<ThumbnailResult>(`/api/projects/${projectId}/generate-thumbnail`, {
                method: 'POST',
                body: JSON.stringify({ prompt: fullPrompt, output_filename: `thumbnail_${styleId}.png` }),
            })
            setResults(prev => {
                const filtered = prev.filter(x => x.style !== styleId)
                return [...filtered, { style: styleId, result: r }]
            })
        } catch (err: any) {
            setResults(prev => {
                const filtered = prev.filter(x => x.style !== styleId)
                return [...filtered, { style: styleId, result: null, error: err.message }]
            })
        } finally { setLoading(null) }
    }

    const generateAll = async () => {
        for (const s of THUMBNAIL_STYLES) {
            await generate(s.id, s.prompt)
        }
    }

    const getResult = (styleId: string) => results.find(r => r.style === styleId)

    return (
        <Modal title="Generate Thumbnails" onClose={onClose} width={600}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Generate 4 YouTube-optimized thumbnail variants for <strong>{projectName}</strong>.
                    Each uses a different visual style to maximize CTR.
                </div>

                {/* Custom context */}
                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Custom Context (optional)</label>
                    <input value={prompt} onChange={e => setPrompt(e.target.value)}
                        placeholder="e.g. war scene, historical documentary, 1954 Vietnam..."
                        className="input" />
                    <p className="text-xs" style={{ color: 'var(--muted)' }}>Added to each style prompt for context relevance.</p>
                </div>

                {/* Generate all */}
                <ActionButton variant="primary" onClick={generateAll} disabled={!!loading}>
                    <ImageIcon size={12} /> Generate All 4 Variants
                </ActionButton>

                {/* Style cards */}
                <div className="grid grid-cols-2 gap-3">
                    {THUMBNAIL_STYLES.map(s => {
                        const r = getResult(s.id)
                        const isLoading = loading === s.id
                        const previewUrl = r?.result?.image_url || r?.result?.url
                        const outputPath = r?.result?.output_path || r?.result?.local_path
                        return (
                            <div key={s.id} className="flex flex-col gap-2 rounded-lg p-3"
                                style={{ background: 'var(--card)', border: `1px solid ${activeStyle === s.id ? 'var(--accent)' : 'var(--border)'}` }}>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-semibold" style={{ color: 'var(--text)' }}>{s.label}</span>
                                    <ActionButton variant="ghost" size="sm" onClick={() => generate(s.id, s.prompt)} disabled={!!loading}>
                                        {isLoading ? '⏳' : '▶ Gen'}
                                    </ActionButton>
                                </div>

                                {/* Thumbnail preview */}
                                <div className="rounded overflow-hidden" style={{ aspectRatio: '16/9', background: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    {previewUrl ? (
                                        <img src={previewUrl} alt={s.label} className="w-full h-full object-cover" />
                                    ) : isLoading ? (
                                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Generating...</div>
                                    ) : r?.error ? (
                                        <div className="text-xs text-center p-2" style={{ color: 'var(--red)' }}>✗ {r.error}</div>
                                    ) : (
                                        <div className="text-xs text-center" style={{ color: 'var(--muted)' }}>
                                            <ImageIcon size={20} style={{ margin: '0 auto 4px' }} />
                                            Not generated
                                        </div>
                                    )}
                                </div>

                                {outputPath && (
                                    <div className="text-xs font-mono truncate" style={{ color: 'var(--muted)' }}>{outputPath}</div>
                                )}
                            </div>
                        )
                    })}
                </div>

                <div className="flex justify-end">
                    <ActionButton variant="ghost" onClick={onClose}>Close</ActionButton>
                </div>
            </div>
        </Modal>
    )
}
