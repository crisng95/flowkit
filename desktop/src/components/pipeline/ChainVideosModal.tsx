/**
 * ChainVideosModal
 * Sets end_scene_media_id on CONTINUATION scenes for smooth transitions,
 * then triggers batch video generation.
 * Corresponds to CLI skill: fk:gen-chain-videos
 */
import { useState } from 'react'
import { Link2, CheckCircle, AlertTriangle, Film } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'

interface Scene {
    id: string
    display_order: number
    chain_type: string
    parent_scene_id: string | null
    vertical_image_media_id: string | null
    horizontal_image_media_id: string | null
    vertical_video_status: string
    horizontal_video_status: string
}

interface ChainSetup {
    scene: Scene
    parent: Scene | null
    endImageSet: boolean
    status: 'ready' | 'missing_image' | 'not_continuation'
}

interface Props {
    videoId: string
    projectId: string
    orientation: string
    onClose: () => void
}

export default function ChainVideosModal({ videoId, projectId, orientation, onClose }: Props) {
    const [chains, setChains] = useState<ChainSetup[]>([])
    const [loading, setLoading] = useState(false)
    const [phase, setPhase] = useState<'idle' | 'setup' | 'generating' | 'done'>('idle')
    const [error, setError] = useState('')

    const setupChains = async () => {
        setLoading(true); setError('')
        try {
            const prefix = orientation === 'HORIZONTAL' ? 'horizontal' : 'vertical'
            const scenes = await fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`)
            const byId = Object.fromEntries(scenes.map(s => [s.id, s]))
            const sorted = [...scenes].sort((a, b) => a.display_order - b.display_order)

            const setupList: ChainSetup[] = []
            for (const scene of sorted) {
                if (scene.chain_type !== 'CONTINUATION') {
                    setupList.push({ scene, parent: null, endImageSet: false, status: 'not_continuation' })
                    continue
                }
                const parent = scene.parent_scene_id ? byId[scene.parent_scene_id] : null
                const parentImageMediaId = parent ? (parent as any)[`${prefix}_image_media_id`] : null
                if (!parentImageMediaId) {
                    setupList.push({ scene, parent, endImageSet: false, status: 'missing_image' })
                    continue
                }
                // Set end_scene_media_id to parent's image
                await patchAPI(`/api/scenes/${scene.id}`, {
                    [`${prefix}_end_scene_media_id`]: parentImageMediaId,
                })
                setupList.push({ scene, parent, endImageSet: true, status: 'ready' })
            }
            setChains(setupList)
            setPhase('setup')
        } catch (err: any) { setError(err.message) }
        finally { setLoading(false) }
    }

    const genVideos = async () => {
        setLoading(true); setError('')
        try {
            const scenes = await fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`)
            const requests = scenes.map(s => ({
                type: 'GENERATE_VIDEO',
                project_id: projectId,
                video_id: videoId,
                scene_id: s.id,
                orientation,
            }))
            await fetchAPI('/api/requests/batch', { method: 'POST', body: JSON.stringify({ requests }) })
            setPhase('generating')
        } catch (err: any) { setError(err.message) }
        finally { setLoading(false) }
    }

    const continuation = chains.filter(c => c.status === 'ready').length
    const missing = chains.filter(c => c.status === 'missing_image').length

    return (
        <Modal title="Chain Videos (Smooth Transitions)" onClose={onClose} width={560}>
            <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5 text-xs" style={{ color: 'var(--muted)' }}>
                    <p>Sets <code>end_scene_media_id</code> on CONTINUATION scenes so each video smoothly transitions into the next scene's visual world.</p>
                    <p className="rounded p-2" style={{ background: 'rgba(59,130,246,0.08)', color: 'var(--accent)', border: '1px solid rgba(59,130,246,0.2)' }}>
                        <strong>Prerequisite:</strong> All scenes must have generated images before chaining.
                    </p>
                </div>

                {phase === 'idle' && (
                    <ActionButton variant="primary" onClick={setupChains} disabled={loading}>
                        <Link2 size={12} /> Setup Chains
                    </ActionButton>
                )}

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {chains.length > 0 && (
                    <>
                        <div className="flex gap-3 text-xs">
                            <span style={{ color: 'var(--green)' }}>✓ {continuation} chains set</span>
                            {missing > 0 && <span style={{ color: 'var(--yellow)' }}>⚠ {missing} missing images</span>}
                            <span style={{ color: 'var(--muted)' }}>— {chains.filter(c => c.status === 'not_continuation').length} ROOT/standalone</span>
                        </div>

                        <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
                            {chains.map(c => (
                                <div key={c.scene.id} className="flex items-center gap-2 text-xs px-3 py-1.5 rounded"
                                    style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                    <span className="w-5 font-bold" style={{ color: 'var(--muted)' }}>#{c.scene.display_order + 1}</span>
                                    <span className="flex-1" style={{ color: 'var(--text)' }}>{c.scene.chain_type}</span>
                                    {c.status === 'ready' && <span style={{ color: 'var(--green)' }}><CheckCircle size={11} /> Chained</span>}
                                    {c.status === 'missing_image' && <span style={{ color: 'var(--yellow)' }}><AlertTriangle size={11} /> No image</span>}
                                    {c.status === 'not_continuation' && <span style={{ color: 'var(--muted)' }}>— standalone</span>}
                                </div>
                            ))}
                        </div>

                        {missing > 0 && (
                            <div className="text-xs p-2 rounded" style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--yellow)', border: '1px solid rgba(245,158,11,0.3)' }}>
                                ⚠ {missing} CONTINUATION scenes are missing parent images. Generate all scene images first, then re-run Setup Chains.
                            </div>
                        )}

                        {phase === 'setup' && continuation > 0 && (
                            <ActionButton variant="primary" onClick={genVideos} disabled={loading}>
                                <Film size={12} /> Generate All Chain Videos ({chains.length} scenes)
                            </ActionButton>
                        )}
                        {phase === 'generating' && (
                            <div className="text-xs p-2 rounded" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}>
                                ✓ Generation queued! Monitor progress in the Pipeline bar (Videos status bar).
                            </div>
                        )}
                    </>
                )}

                <div className="flex justify-end">
                    <ActionButton variant="ghost" onClick={onClose}>Close</ActionButton>
                </div>
            </div>
        </Modal>
    )
}
