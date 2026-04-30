import { useEffect, useMemo, useState } from 'react'
import { Download, PlayCircle, Send } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'
import type { Scene } from '../../types'
import { normalizeOrientation, orientationAspectCss, sceneStatus, sceneUrl } from '../../lib/orientation'

interface Props {
    projectId: string
    videoId: string
    orientation: string
    onClose: () => void
}

type ReviewAction = 'ok' | 'regen-img' | 'regen-vid' | 'edit'

interface SceneFeedback {
    action: ReviewAction
    note: string
}

export default function ReviewBoardModal({ projectId, videoId, orientation, onClose }: Props) {
    const [scenes, setScenes] = useState<Scene[]>([])
    const [feedback, setFeedback] = useState<Record<string, SceneFeedback>>({})
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const ori = normalizeOrientation(orientation)

    useEffect(() => {
        fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`)
            .then(rows => {
                const sorted = rows.sort((a, b) => a.display_order - b.display_order)
                setScenes(sorted)
                const init: Record<string, SceneFeedback> = {}
                sorted.forEach(s => { init[s.id] = { action: 'ok', note: '' } })
                setFeedback(init)
            })
            .catch(() => setScenes([]))
    }, [videoId])

    const setAction = (sceneId: string, action: ReviewAction) => {
        setFeedback(prev => ({ ...prev, [sceneId]: { ...(prev[sceneId] ?? { note: '' }), action } }))
    }

    const setNote = (sceneId: string, note: string) => {
        setFeedback(prev => ({ ...prev, [sceneId]: { ...(prev[sceneId] ?? { action: 'ok' }), note } }))
    }

    const exportJson = () => {
        const payload = {
            project_id: projectId,
            video_id: videoId,
            orientation: ori,
            generated_at: new Date().toISOString(),
            feedback: scenes.map(scene => ({
                scene_id: scene.id,
                display_order: scene.display_order,
                action: feedback[scene.id]?.action ?? 'ok',
                note: feedback[scene.id]?.note ?? '',
            })),
        }
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `review_feedback_${videoId}.json`
        a.click()
        URL.revokeObjectURL(url)
    }

    const apply = async () => {
        setLoading(true)
        setError('')
        try {
            const requests: any[] = []
            for (const scene of scenes) {
                const fb = feedback[scene.id]
                if (!fb || fb.action === 'ok') continue

                if (fb.action === 'regen-img') {
                    requests.push({
                        type: 'REGENERATE_IMAGE',
                        project_id: projectId,
                        video_id: videoId,
                        scene_id: scene.id,
                        orientation: ori,
                    })
                }

                if (fb.action === 'regen-vid') {
                    requests.push({
                        type: 'REGENERATE_VIDEO',
                        project_id: projectId,
                        video_id: videoId,
                        scene_id: scene.id,
                        orientation: ori,
                    })
                }

                if (fb.action === 'edit') {
                    if (fb.note.trim()) {
                        await patchAPI(`/api/scenes/${scene.id}`, {
                            prompt: `${scene.prompt ?? ''}\n[EDIT REQUEST] ${fb.note.trim()}`.trim(),
                        })
                    }
                    requests.push({
                        type: 'EDIT_IMAGE',
                        project_id: projectId,
                        video_id: videoId,
                        scene_id: scene.id,
                        orientation: ori,
                    })
                }
            }

            if (requests.length > 0) {
                await fetchAPI('/api/requests/batch', {
                    method: 'POST',
                    body: JSON.stringify({ requests }),
                })
            }
        } catch (e: any) {
            setError(e.message ?? 'Failed to apply feedback')
        } finally {
            setLoading(false)
        }
    }

    const summary = useMemo(() => {
        const counts: Record<ReviewAction, number> = { ok: 0, 'regen-img': 0, 'regen-vid': 0, edit: 0 }
        Object.values(feedback).forEach(f => { counts[f.action] += 1 })
        return counts
    }, [feedback])

    return (
        <Modal title="Review Board (fk:review-board)" onClose={onClose} width={920}>
            <div className="flex flex-col gap-3">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Visual review từng scene, gắn action và note, export feedback JSON hoặc apply trực tiếp thành request queue.
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--muted)' }}>
                    <span>OK: {summary.ok}</span>
                    <span>Regen Image: {summary['regen-img']}</span>
                    <span>Regen Video: {summary['regen-vid']}</span>
                    <span>Edit: {summary.edit}</span>
                    <div className="flex-1" />
                    <ActionButton variant="ghost" size="sm" onClick={exportJson}><Download size={11} /> Export JSON</ActionButton>
                    <ActionButton variant="primary" size="sm" onClick={apply} disabled={loading}><Send size={11} /> {loading ? 'Applying...' : 'Apply Actions'}</ActionButton>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                <div className="grid gap-3 max-h-[540px] overflow-y-auto" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
                    {scenes.map(scene => {
                        const fb = feedback[scene.id] ?? { action: 'ok', note: '' }
                        const image = sceneUrl(scene, ori, 'image')
                        const video = sceneUrl(scene, ori, 'video')
                        const imageSt = sceneStatus(scene, ori, 'image')
                        const videoSt = sceneStatus(scene, ori, 'video')

                        return (
                            <div key={scene.id} className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                <div className="text-xs font-semibold" style={{ color: 'var(--text)' }}>
                                    #{scene.display_order + 1} · img {imageSt} · vid {videoSt}
                                </div>

                                <div className="rounded overflow-hidden" style={{ aspectRatio: orientationAspectCss(ori), background: 'var(--surface-alt)' }}>
                                    {video ? (
                                        <video src={video} controls className="w-full h-full object-cover" />
                                    ) : image ? (
                                        <img src={image} alt={`scene-${scene.display_order + 1}`} className="w-full h-full object-cover" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-xs" style={{ color: 'var(--muted)' }}>
                                            <PlayCircle size={12} />
                                        </div>
                                    )}
                                </div>

                                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                                    {(scene.prompt ?? scene.video_prompt ?? '(no prompt)').slice(0, 140)}
                                </div>

                                <select value={fb.action} onChange={e => setAction(scene.id, e.target.value as ReviewAction)} className="input">
                                    <option value="ok">OK</option>
                                    <option value="regen-img">Regen Image</option>
                                    <option value="regen-vid">Regen Video</option>
                                    <option value="edit">Edit Image (with note)</option>
                                </select>

                                <textarea
                                    rows={2}
                                    className="input resize-none"
                                    placeholder="Feedback note (required for edit)"
                                    value={fb.note}
                                    onChange={e => setNote(scene.id, e.target.value)}
                                />
                            </div>
                        )
                    })}
                </div>
            </div>
        </Modal>
    )
}
