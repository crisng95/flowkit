import { useEffect, useMemo, useState } from 'react'
import { Sparkles } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'
import type { Scene } from '../../types'
import { normalizeOrientation } from '../../lib/orientation'

interface Props {
    projectId: string
    videoId: string
    orientation: string
    onClose: () => void
}

interface Suggestion {
    id: string
    afterSceneId: string
    afterOrder: number
    label: string
    prompt: string
    video_prompt: string
    narrator_text: string
    character_names: string[]
}

function parseChars(raw: Scene['character_names']): string[] {
    if (!raw) return []
    if (Array.isArray(raw)) return raw
    try {
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed) ? parsed : []
    } catch {
        return []
    }
}

function buildSuggestions(scenes: Scene[]): Suggestion[] {
    const keywords = /(battle|fight|attack|reveal|explosion|escape|close[- ]up|dramatic|confront)/i
    const out: Suggestion[] = []

    scenes.forEach((scene, idx) => {
        const prompt = `${scene.prompt ?? ''} ${scene.video_prompt ?? ''}`.trim()
        const shouldPick = keywords.test(prompt) || idx % 3 === 1
        if (!shouldPick) return

        const charNames = parseChars(scene.character_names)
        out.push({
            id: `mix-${scene.id}`,
            afterSceneId: scene.id,
            afterOrder: scene.display_order,
            label: `Insert close-up after #${scene.display_order + 1}`,
            prompt: 'Close-up cinematic angle of the previous action beat, keeping same characters and environment consistency.',
            video_prompt: '0-3s: close-up detail reveal. 3-6s: subtle camera push-in. 6-8s: hold dramatic expression.',
            narrator_text: scene.narrator_text ?? '',
            character_names: charNames,
        })
    })

    return out.slice(0, 12)
}

export default function CreativeMixModal({ projectId, videoId, orientation, onClose }: Props) {
    const [scenes, setScenes] = useState<Scene[]>([])
    const [selected, setSelected] = useState<Record<string, boolean>>({})
    const [queueImages, setQueueImages] = useState(true)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [createdCount, setCreatedCount] = useState(0)

    const ori = normalizeOrientation(orientation)

    useEffect(() => {
        fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`)
            .then(rows => {
                const sorted = rows.sort((a, b) => a.display_order - b.display_order)
                setScenes(sorted)
                const defaults: Record<string, boolean> = {}
                buildSuggestions(sorted).forEach(s => { defaults[s.id] = true })
                setSelected(defaults)
            })
            .catch(() => setScenes([]))
    }, [videoId])

    const suggestions = useMemo(() => buildSuggestions(scenes), [scenes])

    const apply = async () => {
        setLoading(true)
        setError('')
        setCreatedCount(0)

        try {
            const picked = suggestions.filter(s => selected[s.id])
            if (picked.length === 0) return

            const createdSceneIds: string[] = []
            for (const s of picked) {
                const created = await fetchAPI<{ id: string }>('/api/scenes', {
                    method: 'POST',
                    body: JSON.stringify({
                        video_id: videoId,
                        display_order: s.afterOrder + 1,
                        chain_type: 'INSERT',
                        parent_scene_id: s.afterSceneId,
                        source: 'system',
                        prompt: s.prompt,
                        video_prompt: s.video_prompt,
                        narrator_text: s.narrator_text || null,
                        character_names: s.character_names.length > 0 ? s.character_names : null,
                    }),
                })
                createdSceneIds.push(created.id)
            }

            if (queueImages && createdSceneIds.length > 0) {
                await fetchAPI('/api/requests/batch', {
                    method: 'POST',
                    body: JSON.stringify({
                        requests: createdSceneIds.map(sceneId => ({
                            type: 'GENERATE_IMAGE',
                            project_id: projectId,
                            video_id: videoId,
                            scene_id: sceneId,
                            orientation: ori,
                        })),
                    }),
                })
            }

            setCreatedCount(createdSceneIds.length)
        } catch (e: any) {
            setError(e.message ?? 'Failed to apply creative mix')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Creative Mix (fk:creative-mix)" onClose={onClose} width={760}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Đề xuất các INSERT scene (source=system) để tạo multi-angle/cutaway cinematic từ scene hiện có.
                </div>

                {suggestions.length === 0 ? (
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>No suitable scenes detected for creative mix suggestions.</div>
                ) : (
                    <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto">
                        {suggestions.map(s => (
                            <label key={s.id} className="rounded p-3 flex gap-2 items-start" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                <input
                                    type="checkbox"
                                    checked={!!selected[s.id]}
                                    onChange={e => setSelected(prev => ({ ...prev, [s.id]: e.target.checked }))}
                                />
                                <div className="flex-1 min-w-0">
                                    <div className="text-xs font-semibold" style={{ color: 'var(--text)' }}>{s.label}</div>
                                    <div className="text-xs" style={{ color: 'var(--muted)' }}>{s.prompt}</div>
                                </div>
                            </label>
                        ))}
                    </div>
                )}

                <label className="text-xs inline-flex items-center gap-2" style={{ color: 'var(--text)' }}>
                    <input type="checkbox" checked={queueImages} onChange={e => setQueueImages(e.target.checked)} />
                    Queue GENERATE_IMAGE ngay sau khi tạo insert scenes
                </label>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}
                {createdCount > 0 && (
                    <div className="text-xs p-2 rounded" style={{ background: 'rgba(34,197,94,0.12)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}>
                        ✓ Created {createdCount} insert scene(s){queueImages ? ' and queued image generation' : ''}.
                    </div>
                )}

                <div className="flex justify-end gap-2">
                    <ActionButton variant="ghost" onClick={onClose}>Close</ActionButton>
                    <ActionButton variant="primary" onClick={apply} disabled={loading || suggestions.length === 0}>
                        <Sparkles size={12} /> {loading ? 'Applying...' : 'Apply Creative Mix'}
                    </ActionButton>
                </div>
            </div>
        </Modal>
    )
}
