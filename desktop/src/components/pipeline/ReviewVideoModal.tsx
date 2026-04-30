/**
 * Review video modal — matches actual VideoReview API response shape.
 * POST /api/videos/{vid}/review?project_id=...&mode=light|deep
 */
import { useState } from 'react'
import { AlertTriangle, CheckCircle, RefreshCw, SkipForward } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'

// ─── Types matching agent/models/review.py ─────────────────────
interface DimensionScores {
    character_consistency: number
    prompt_adherence: number
    motion_quality: number
    visual_fidelity: number
    temporal_coherence: number
    composition: number
}

interface VideoError {
    severity: 'CRITICAL' | 'HIGH' | 'MINOR'
    time_range: string
    description: string
}

interface SceneReview {
    scene_id: string
    overall_score: number
    verdict: string
    dimensions: DimensionScores
    errors: VideoError[]
    fix_guide: string
    frames_analyzed: number
    fps_used: number
    has_critical_errors: boolean
}

interface VideoReview {
    video_id: string
    project_id: string
    mode: string
    orientation: string
    overall_score: number
    verdict: string
    scene_reviews: SceneReview[]
    scenes_reviewed: number
    scenes_skipped: number
}

interface Props {
    videoId: string
    projectId: string
    onClose: () => void
}

// ─── Helpers ───────────────────────────────────────────────────
const SCORE_COLOR = (s: number) => s >= 7.5 ? 'var(--green)' : s >= 5 ? 'var(--yellow)' : 'var(--red)'
const SEVERITY_COLOR: Record<string, string> = {
    CRITICAL: 'var(--red)', HIGH: 'var(--yellow)', MINOR: 'var(--muted)'
}

function ScoreBar({ score }: { score: number }) {
    const color = SCORE_COLOR(score)
    return (
        <div className="flex items-center gap-2">
            <div className="flex-1 rounded-full overflow-hidden h-1.5" style={{ background: 'var(--border)' }}>
                <div className="h-full rounded-full transition-all" style={{ width: `${(score / 10) * 100}%`, background: color }} />
            </div>
            <span className="text-xs font-bold w-8 text-right" style={{ color }}>{score.toFixed(1)}</span>
        </div>
    )
}

// ─── Main Component ────────────────────────────────────────────
export default function ReviewVideoModal({ videoId, projectId, onClose }: Props) {
    const [mode, setMode] = useState<'light' | 'deep'>('light')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<VideoReview | null>(null)
    const [error, setError] = useState('')
    const [regenning, setRegenning] = useState<Set<string>>(new Set())
    const [expanded, setExpanded] = useState<string | null>(null)

    const runReview = async () => {
        setLoading(true); setError(''); setResult(null)
        try {
            const r = await fetchAPI<VideoReview>(
                `/api/videos/${videoId}/review?project_id=${projectId}&mode=${mode}`,
                { method: 'POST' }
            )
            setResult(r)
        } catch (e: any) {
            setError(e.message ?? 'Review failed')
        } finally { setLoading(false) }
    }

    const regenScene = async (sr: SceneReview) => {
        setRegenning(prev => new Set([...prev, sr.scene_id]))
        try {
            if (sr.fix_guide) {
                const scene = await fetchAPI<any>(`/api/scenes/${sr.scene_id}`)
                const newPrompt = `${scene.video_prompt ?? ''}\n[FIX: ${sr.fix_guide}]`.trim()
                await patchAPI(`/api/scenes/${sr.scene_id}`, { video_prompt: newPrompt })
            }
            await fetchAPI('/api/requests/batch', {
                method: 'POST',
                body: JSON.stringify({
                    requests: [{
                        type: 'REGENERATE_VIDEO',
                        project_id: projectId,
                        video_id: videoId,
                        scene_id: sr.scene_id,
                        orientation: result?.orientation ?? 'VERTICAL',
                    }]
                }),
            })
        } finally {
            setRegenning(prev => { const n = new Set(prev); n.delete(sr.scene_id); return n })
        }
    }

    const regenAllFailed = async () => {
        if (!result) return
        const failed = result.scene_reviews.filter(s => s.overall_score < 7.5)
        for (const s of failed) await regenScene(s)
    }

    const failed = result?.scene_reviews.filter(s => s.overall_score < 7.5) ?? []
    const passed = !result || result.overall_score >= 7.5

    return (
        <Modal title="Review Videos" onClose={onClose} width={660}>
            <div className="flex flex-col gap-4">
                {/* Mode selector + run */}
                <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                        {(['light', 'deep'] as const).map(m => (
                            <button key={m} onClick={() => setMode(m)}
                                className="px-3 py-1.5 rounded text-xs font-semibold"
                                style={{ background: mode === m ? 'var(--accent)' : 'var(--card)', color: mode === m ? '#fff' : 'var(--muted)', border: '1px solid var(--border)' }}>
                                {m === 'light' ? '⚡ Light (4fps)' : '🔬 Deep (8fps)'}
                            </button>
                        ))}
                    </div>
                    <ActionButton variant="primary" onClick={runReview} disabled={loading}>
                        {loading ? '⏳ Reviewing...' : '▶ Run Review'}
                    </ActionButton>
                </div>

                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Uses Claude Vision to analyze each scene video. Scenes scoring &lt; 7.5 flagged for regen.
                </div>

                {error && (
                    <div className="text-xs p-3 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>
                )}

                {loading && (
                    <div className="flex items-center justify-center py-10 gap-3">
                        <div className="w-6 h-6 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
                        <span className="text-xs" style={{ color: 'var(--muted)' }}>Analyzing scene videos with Claude Vision...</span>
                    </div>
                )}

                {result && !loading && (
                    <div className="flex flex-col gap-4">
                        {/* Overall summary */}
                        <div className="rounded-lg p-4 flex flex-col gap-3" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <div className="flex items-center justify-between">
                                <div className="flex flex-col gap-1">
                                    <span className="text-xs font-bold" style={{ color: 'var(--text)' }}>
                                        Overall — {result.verdict.toUpperCase()}
                                    </span>
                                    <span className="text-xs" style={{ color: 'var(--muted)' }}>
                                        {result.scenes_reviewed} reviewed · {result.scenes_skipped} skipped (no video) · {result.orientation}
                                    </span>
                                </div>
                                {passed
                                    ? <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--green)' }}><CheckCircle size={13} /> Passed</span>
                                    : <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--red)' }}><AlertTriangle size={13} /> {failed.length} need regen</span>}
                            </div>
                            <ScoreBar score={result.overall_score} />
                            {failed.length > 0 && (
                                <ActionButton variant="danger" size="sm" onClick={regenAllFailed}>
                                    <RefreshCw size={11} /> Regen All Failed ({failed.length} scenes)
                                </ActionButton>
                            )}
                        </div>

                        {/* Per-scene */}
                        <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
                            {result.scene_reviews.map((sr, idx) => {
                                const isExpanded = expanded === sr.scene_id
                                const hasCritical = sr.has_critical_errors
                                return (
                                    <div key={sr.scene_id} className="rounded-lg flex flex-col"
                                        style={{ background: 'var(--card)', border: `1px solid ${sr.overall_score < 7.5 ? 'rgba(239,68,68,0.4)' : 'var(--border)'}` }}>
                                        {/* Header */}
                                        <div className="flex items-center gap-3 px-3 py-2 cursor-pointer"
                                            onClick={() => setExpanded(isExpanded ? null : sr.scene_id)}>
                                            <span className="text-xs font-bold w-6 flex-shrink-0" style={{ color: 'var(--muted)' }}>#{idx + 1}</span>
                                            <div className="flex-1"><ScoreBar score={sr.overall_score} /></div>
                                            <span className="text-xs flex-shrink-0" style={{ color: SCORE_COLOR(sr.overall_score) }}>{sr.verdict}</span>
                                            {sr.overall_score < 7.5 && (
                                                <span onClick={e => e.stopPropagation()}>
                                                    <ActionButton variant="ghost" size="sm"
                                                        onClick={() => regenScene(sr)}
                                                        disabled={regenning.has(sr.scene_id)}>
                                                        <RefreshCw size={10} /> {regenning.has(sr.scene_id) ? '...' : 'Regen'}
                                                    </ActionButton>
                                                </span>
                                            )}
                                        </div>

                                        {/* Expanded details */}
                                        {isExpanded && (
                                            <div className="flex flex-col gap-2 px-3 pb-3 text-xs" style={{ borderTop: '1px solid var(--border)' }}>
                                                {/* Dimension scores */}
                                                <div className="grid gap-1 pt-2" style={{ gridTemplateColumns: '1fr 1fr' }}>
                                                    {Object.entries(sr.dimensions).map(([k, v]) => (
                                                        <div key={k} className="flex flex-col gap-0.5">
                                                            <span style={{ color: 'var(--muted)' }}>{k.replace(/_/g, ' ')}</span>
                                                            <ScoreBar score={v as number} />
                                                        </div>
                                                    ))}
                                                </div>
                                                {/* Errors */}
                                                {sr.errors.length > 0 && (
                                                    <div className="flex flex-col gap-1 pt-1">
                                                        {sr.errors.map((e, i) => (
                                                            <div key={i} className="flex gap-2">
                                                                <span className="font-bold flex-shrink-0"
                                                                    style={{ color: SEVERITY_COLOR[e.severity] ?? 'var(--muted)' }}>
                                                                    [{e.severity}]
                                                                </span>
                                                                <span style={{ color: 'var(--text)' }}>{e.time_range}: {e.description}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                                {/* Fix guide */}
                                                {sr.fix_guide && (
                                                    <div className="p-2 rounded text-xs" style={{ background: 'rgba(59,130,246,0.08)', color: 'var(--muted)', border: '1px solid rgba(59,130,246,0.2)' }}>
                                                        💡 {sr.fix_guide}
                                                    </div>
                                                )}
                                                <div style={{ color: 'var(--muted)' }}>
                                                    {sr.frames_analyzed} frames @ {sr.fps_used}fps
                                                    {hasCritical && <span style={{ color: 'var(--red)' }}> · CRITICAL ERRORS</span>}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}

                            {result.scenes_skipped > 0 && (
                                <div className="flex items-center gap-2 px-3 py-2 rounded text-xs"
                                    style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
                                    <SkipForward size={11} /> {result.scenes_skipped} scenes skipped (no video generated yet)
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </Modal>
    )
}
