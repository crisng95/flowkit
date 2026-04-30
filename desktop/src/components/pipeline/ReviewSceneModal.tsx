import { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle, RefreshCw, Wrench, Film, Sparkles } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'
import { normalizeOrientation } from '../../lib/orientation'

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

interface ScenePayload {
    id: string
    prompt: string | null
    video_prompt: string | null
}

interface Props {
    projectId: string
    videoId: string
    sceneId: string
    orientation?: string
    onClose: () => void
    onRegenerated?: () => void
    onPatched?: () => void
}

const SCORE_PASS = 7.5
const scoreColor = (score: number) => (score >= SCORE_PASS ? 'var(--green)' : score >= 5 ? 'var(--yellow)' : 'var(--red)')
const severityColor: Record<string, string> = {
    CRITICAL: 'var(--red)',
    HIGH: 'var(--yellow)',
    MINOR: 'var(--muted)',
}

function prettyKey(key: string) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function ScoreBar({ score }: { score: number }) {
    const color = scoreColor(score)
    return (
        <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                <div className="h-full rounded-full transition-all" style={{ width: `${(score / 10) * 100}%`, background: color }} />
            </div>
            <span className="w-8 text-right text-xs font-bold" style={{ color }}>{score.toFixed(1)}</span>
        </div>
    )
}

export default function ReviewSceneModal({
    projectId,
    videoId,
    sceneId,
    orientation = 'VERTICAL',
    onClose,
    onRegenerated,
    onPatched,
}: Props) {
    const [mode, setMode] = useState<'light' | 'deep'>('light')
    const [loading, setLoading] = useState(false)
    const [patching, setPatching] = useState(false)
    const [regenning, setRegenning] = useState(false)

    const [result, setResult] = useState<SceneReview | null>(null)
    const [error, setError] = useState('')
    const [statusMsg, setStatusMsg] = useState('')
    const [fixDraft, setFixDraft] = useState('')

    const ori = normalizeOrientation(orientation)

    const runReview = async () => {
        setLoading(true)
        setError('')
        setStatusMsg('')
        try {
            const r = await fetchAPI<SceneReview>(
                `/api/videos/${videoId}/scenes/${sceneId}/review?project_id=${projectId}&mode=${mode}&orientation=${ori}`,
                { method: 'POST' },
            )
            setResult(r)
            setFixDraft(r.fix_guide || '')
        } catch (e: any) {
            setError(e.message ?? 'Scene review thất bại')
        } finally {
            setLoading(false)
        }
    }

    const patchFixToScene = async () => {
        if (!fixDraft.trim()) {
            setError('Fix guide đang trống.')
            return
        }
        setPatching(true)
        setError('')
        setStatusMsg('')
        try {
            const scene = await fetchAPI<ScenePayload>(`/api/scenes/${sceneId}`)
            const basePrompt = (scene.video_prompt ?? '').trim()
            const fixLine = `[FIX: ${fixDraft.trim()}]`
            const alreadyIncluded = basePrompt.includes(fixLine)
            const nextVideoPrompt = alreadyIncluded
                ? basePrompt
                : [basePrompt, fixLine].filter(Boolean).join('\n')

            await patchAPI(`/api/scenes/${sceneId}`, { video_prompt: nextVideoPrompt })
            setStatusMsg('✓ Đã cập nhật fix vào video_prompt của scene.')
            onPatched?.()
        } catch (e: any) {
            setError(e.message ?? 'Patch fix thất bại')
        } finally {
            setPatching(false)
        }
    }

    const regenerateSceneVideo = async () => {
        setRegenning(true)
        setError('')
        setStatusMsg('')
        try {
            await fetchAPI('/api/requests/batch', {
                method: 'POST',
                body: JSON.stringify({
                    requests: [{
                        type: 'REGENERATE_VIDEO',
                        project_id: projectId,
                        video_id: videoId,
                        scene_id: sceneId,
                        orientation: ori,
                    }],
                }),
            })
            setStatusMsg('✓ Đã gửi yêu cầu REGENERATE_VIDEO cho scene này.')
            onRegenerated?.()
        } catch (e: any) {
            setError(e.message ?? 'Không thể tạo lại video scene')
        } finally {
            setRegenning(false)
        }
    }

    const patchAndRegen = async () => {
        await patchFixToScene()
        if (!error) {
            await regenerateSceneVideo()
        }
    }

    const pass = useMemo(() => (result ? result.overall_score >= SCORE_PASS : false), [result])

    return (
        <Modal title="Review Scene" onClose={onClose} width={680}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Review 1 scene với Claude Vision. Có thể ghi fix guide vào <code>video_prompt</code> và queue regenerate ngay.
                </div>

                <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                        {(['light', 'deep'] as const).map(m => (
                            <button
                                key={m}
                                onClick={() => setMode(m)}
                                className="px-3 py-1.5 rounded text-xs font-semibold"
                                style={{
                                    background: mode === m ? 'var(--accent)' : 'var(--card)',
                                    color: mode === m ? '#fff' : 'var(--muted)',
                                    border: '1px solid var(--border)',
                                }}
                            >
                                {m === 'light' ? '⚡ Light (4fps)' : '🔬 Deep (8fps)'}
                            </button>
                        ))}
                    </div>
                    <ActionButton variant="primary" onClick={runReview} disabled={loading}>
                        {loading ? (
                            <>
                                <RefreshCw size={11} className="animate-spin" /> Đang review...
                            </>
                        ) : (
                            <>
                                <Sparkles size={11} /> Review scene
                            </>
                        )}
                    </ActionButton>
                </div>

                {error && (
                    <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>
                        {error}
                    </div>
                )}

                {statusMsg && (
                    <div className="text-xs p-2 rounded" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--green)' }}>
                        {statusMsg}
                    </div>
                )}

                {result && (
                    <>
                        <div className="rounded-lg p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <div className="flex items-center justify-between">
                                <div className="flex flex-col">
                                    <span className="text-xs font-semibold" style={{ color: 'var(--text)' }}>
                                        Scene …{result.scene_id.slice(-8)} · {result.verdict.toUpperCase()}
                                    </span>
                                    <span className="text-xs" style={{ color: 'var(--muted)' }}>
                                        {result.frames_analyzed} frames @ {result.fps_used}fps
                                    </span>
                                </div>
                                {pass ? (
                                    <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--green)' }}>
                                        <CheckCircle size={12} /> Pass
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--red)' }}>
                                        <AlertTriangle size={12} /> Cần fix
                                    </span>
                                )}
                            </div>
                            <ScoreBar score={result.overall_score} />
                        </div>

                        <div className="rounded-lg p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Dimension scores</div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {Object.entries(result.dimensions).map(([k, v]) => (
                                    <div key={k} className="flex flex-col gap-1">
                                        <span className="text-[11px]" style={{ color: 'var(--muted)' }}>{prettyKey(k)}</span>
                                        <ScoreBar score={v as number} />
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-lg p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>
                                Lỗi phát hiện ({result.errors.length})
                            </div>
                            {result.errors.length === 0 ? (
                                <div className="text-xs" style={{ color: 'var(--green)' }}>Không phát hiện lỗi đáng kể.</div>
                            ) : (
                                <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
                                    {result.errors.map((e, idx) => (
                                        <div key={idx} className="text-xs rounded px-2 py-1.5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                                            <div className="font-semibold" style={{ color: severityColor[e.severity] ?? 'var(--muted)' }}>
                                                [{e.severity}] {e.time_range}
                                            </div>
                                            <div style={{ color: 'var(--text)' }}>{e.description}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="rounded-lg p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>
                                Fix guide (có thể chỉnh sửa trước khi áp dụng)
                            </div>
                            <textarea
                                rows={4}
                                className="input resize-y text-xs"
                                value={fixDraft}
                                onChange={(e) => setFixDraft(e.target.value)}
                                placeholder="Nhập hoặc chỉnh fix guide..."
                            />
                            <div className="flex flex-wrap gap-2">
                                <ActionButton variant="secondary" size="sm" onClick={patchFixToScene} disabled={patching || !fixDraft.trim()}>
                                    {patching ? (
                                        <>
                                            <RefreshCw size={11} className="animate-spin" /> Đang patch...
                                        </>
                                    ) : (
                                        <>
                                            <Wrench size={11} /> Áp fix vào prompt
                                        </>
                                    )}
                                </ActionButton>

                                <ActionButton variant="ghost" size="sm" onClick={regenerateSceneVideo} disabled={regenning}>
                                    {regenning ? (
                                        <>
                                            <RefreshCw size={11} className="animate-spin" /> Đang queue...
                                        </>
                                    ) : (
                                        <>
                                            <Film size={11} /> Regen scene video
                                        </>
                                    )}
                                </ActionButton>

                                <ActionButton
                                    variant="primary"
                                    size="sm"
                                    onClick={patchAndRegen}
                                    disabled={patching || regenning || !fixDraft.trim()}
                                >
                                    <Sparkles size={11} /> Áp fix + Regen
                                </ActionButton>
                            </div>
                        </div>
                    </>
                )}

                <div className="flex justify-end pt-1">
                    <ActionButton variant="ghost" onClick={onClose}>Đóng</ActionButton>
                </div>
            </div>
        </Modal>
    )
}
