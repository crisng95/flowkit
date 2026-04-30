import { useEffect, useState } from 'react'
import { Sparkles, Search, ChevronDown, ChevronUp, Plus, Trash2, AlertCircle } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import {
    researchTopic, analyzeStory, aiGenerate, loadKeys, loadGeneralSettings,
    type ExtractedProject, type ProviderType
} from '../../api/ai-service'
import { fetchAPI } from '../../api/client'

type Step = 'research' | 'story' | 'analyzing' | 'review' | 'creating'

const PROVIDERS: { id: ProviderType; label: string }[] = [
    { id: 'gemini', label: 'Gemini' },
    { id: 'claude', label: 'Claude' },
    { id: 'openai', label: 'OpenAI' },
]
const FALLBACK_MATERIALS = ['realistic', '3d_pixar', 'anime', 'watercolor', 'cinematic']
const SCENE_COUNTS = [4, 6, 8, 10, 12, 16, 20, 24, 30, 40]

const ENTITY_TYPES = ['character', 'location', 'creature', 'visual_asset', 'generic_troop', 'faction'] as const

interface Props {
    onClose: () => void
    onCreated: (projectId: string) => void
}

function normalizeInlineText(value: string): string {
    return value.replace(/\s+/g, ' ').trim()
}

function projectNameFromTopic(topic: string): string {
    const clean = normalizeInlineText(topic).replace(/^["'“”‘’]+|["'“”‘’]+$/g, '')
    if (!clean) return ''
    return clean.slice(0, 120)
}

type YouTubeMode = 'content' | 'style'

interface YouTubeReferencePayload {
    url: string
    video_id: string
    title: string
    channel?: string | null
    duration_sec?: number | null
    upload_date?: string | null
    transcript_language: string
    caption_type: 'subtitles' | 'automatic_captions'
    transcript_chars: number
    transcript_truncated: boolean
    transcript: string
}

function keyStats(provider: ProviderType) {
    const keys = loadKeys(provider)
    const active = keys.filter(k => k.status === 'active').length
    return { active, total: keys.length }
}

function formatEstimatedDuration(sceneCount: number): string {
    const totalSeconds = Math.max(0, Math.floor(sceneCount * 8))
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60

    if (hours > 0) return `${hours} giờ ${minutes} phút`
    if (minutes > 0) return `${minutes} phút ${seconds} giây`
    return `${seconds} giây`
}

// ─── Step 0: Research ─────────────────────────────────────────
function ResearchStep({
    provider,
    setProvider,
    language,
    setLanguage,
    material,
    setMaterial,
    materials,
    orientation,
    setOrientation,
    sceneCount,
    setSceneCount,
    initialTopic,
    onTopicChange,
    onSkip,
    onNext,
}: {
    provider: ProviderType; setProvider: (p: ProviderType) => void
    language: string; setLanguage: (l: string) => void
    material: string; setMaterial: (m: string) => void
    materials: string[]
    orientation: string; setOrientation: (o: string) => void
    sceneCount: number; setSceneCount: (n: number) => void
    initialTopic: string
    onTopicChange: (topic: string) => void
    onSkip: () => void; onNext: (summary: string) => void
}) {
    const [topic, setTopic] = useState(initialTopic || '')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [error, setError] = useState('')
    const stats = keyStats(provider)
    const hasKeys = stats.active > 0

    const research = async () => {
        if (!topic.trim()) return
        onTopicChange(topic.trim())
        setLoading(true); setError(''); setResult(null)
        try {
            try {
                const r = await fetchAPI<any>('/api/workflows/research', {
                    method: 'POST',
                    body: JSON.stringify({ topic: topic.trim(), language }),
                })
                setResult({
                    summary: r.summary ?? '',
                    key_facts: Array.isArray(r.key_facts) ? r.key_facts : [],
                    suggested_story_angle: r.suggested_story_angle ?? '',
                    sources: Array.isArray(r.sources) ? r.sources : [],
                    output_path: r.output_path ?? null,
                })
            } catch {
                // Fallback: AI-only research (legacy behavior)
                const r = await researchTopic(topic, language, provider)
                setResult(r)
            }
        } catch (e: any) { setError(e.message) }
        finally { setLoading(false) }
    }

    const useAsStory = () => {
        if (!result) return
        onTopicChange(topic.trim())
        const story = `${result.summary}\n\nKey Facts:\n${result.key_facts.map((f: string) => `• ${f}`).join('\n')}\n\nAngle: ${result.suggested_story_angle}`
        onNext(story)
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="flex gap-2">
                <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Chủ đề nghiên cứu</label>
                    <input
                        value={topic}
                        onChange={e => {
                            const next = e.target.value
                            setTopic(next)
                            onTopicChange(next)
                        }}
                        placeholder="VD: Trận Điện Biên Phủ 1954"
                        className="input"
                        onKeyDown={e => { if (e.key === 'Enter') research() }} />
                </div>
            </div>

            <SettingsGrid
                provider={provider}
                setProvider={setProvider}
                material={material}
                setMaterial={setMaterial}
                materials={materials}
                orientation={orientation}
                setOrientation={setOrientation}
                language={language}
                setLanguage={setLanguage}
                sceneCount={sceneCount}
                setSceneCount={setSceneCount}
            />

            {!hasKeys && (
                <div className="flex items-start gap-2 rounded p-3 text-xs" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', color: 'var(--yellow)' }}>
                    <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                    {stats.total > 0
                        ? <>Có {stats.total} key nhưng chưa key nào khả dụng cho {provider}. Bước nghiên cứu web vẫn chạy được; bước <strong>Phân tích AI</strong> cần key hợp lệ ở <strong>Cài đặt → {provider.charAt(0).toUpperCase() + provider.slice(1)}</strong>.</>
                        : <>Chưa có API key khả dụng cho {provider}. Bước nghiên cứu web vẫn chạy được; để phân tích AI hãy vào <strong>Cài đặt → {provider.charAt(0).toUpperCase() + provider.slice(1)}</strong>.</>
                    }
                </div>
            )}

            <div className="flex gap-2">
                <ActionButton variant="primary" onClick={research} disabled={!topic.trim() || loading}>
                    <Search size={12} /> Nghiên cứu
                </ActionButton>
                <ActionButton variant="ghost" onClick={onSkip}>Bỏ qua → Tự viết kịch bản</ActionButton>
            </div>

            {loading && <div className="text-xs" style={{ color: 'var(--muted)' }}>Đang nghiên cứu chủ đề từ web sources...</div>}
            {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

            {result && (
                <div className="flex flex-col gap-3 rounded-lg p-4" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Kết quả nghiên cứu</div>
                    <div className="text-xs" style={{ color: 'var(--text)', lineHeight: 1.6 }}>{result.summary}</div>
                    <div className="flex flex-col gap-1">
                        {result.key_facts.map((f: string, i: number) => (
                            <div key={i} className="text-xs flex gap-1.5" style={{ color: 'var(--muted)' }}>
                                <span>•</span><span>{f}</span>
                            </div>
                        ))}
                    </div>
                    {result.suggested_story_angle && (
                        <div className="text-xs rounded p-2" style={{ background: 'rgba(59,130,246,0.08)', color: 'var(--accent)', border: '1px solid rgba(59,130,246,0.2)' }}>
                            📐 Góc kể: {result.suggested_story_angle}
                        </div>
                    )}
                    {Array.isArray(result.sources) && result.sources.length > 0 && (
                        <div className="flex flex-col gap-1 text-xs" style={{ color: 'var(--muted)' }}>
                            <div className="font-semibold">Nguồn tham chiếu</div>
                            {result.sources.slice(0, 5).map((s: any, i: number) => (
                                <a key={i} href={s.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                                    {i + 1}. {s.title}
                                </a>
                            ))}
                            {result.output_path && (
                                <div className="font-mono" style={{ fontSize: 10 }}>Saved: {result.output_path}</div>
                            )}
                        </div>
                    )}
                    <ActionButton variant="primary" onClick={useAsStory}>
                        <Sparkles size={12} /> Dùng làm nội dung →
                    </ActionButton>
                </div>
            )}
        </div>
    )
}

// ─── Step 1: Story Input ──────────────────────────────────────
function StoryStep({
    projectName, setProjectName, projectDescription, setProjectDescription,
    projectStory, setProjectStory,
    videoTitle, setVideoTitle,
    youtubeUrl, setYoutubeUrl,
    youtubeStatus, youtubeError, youtubeMeta, youtubeLoadingMode, onAnalyzeYouTube,
    story, setStory, material, setMaterial,
    materials,
    language, setLanguage, orientation, setOrientation, sceneCount, setSceneCount,
    provider, setProvider, onAnalyze, error, onBack
}: any) {
    const stats = keyStats(provider)
    const hasKeys = stats.active > 0
    return (
        <div className="flex flex-col gap-4">
            {!hasKeys && (
                <div className="flex items-start gap-2 rounded p-3 text-xs" style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', color: 'var(--yellow)' }}>
                    <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                    {stats.total > 0
                        ? <>Có {stats.total} key nhưng chưa key nào khả dụng cho {provider}. Vào <strong>Cài đặt → {provider.charAt(0).toUpperCase() + provider.slice(1)}</strong></>
                        : <>Chưa có API key cho {provider}. Vào <strong>Cài đặt → {provider.charAt(0).toUpperCase() + provider.slice(1)}</strong></>
                    }
                </div>
            )}
            <Field label="Tên dự án">
                <input value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="FlowKit Workspace" className="input" />
            </Field>
            <Field label="Mô tả dự án (tùy chọn)">
                <textarea
                    value={projectDescription}
                    onChange={e => setProjectDescription(e.target.value)}
                    rows={2}
                    placeholder="Mô tả ngắn về mục tiêu chung của project (không phải kịch bản cụ thể của từng video)"
                    className="input resize-y"
                    style={{ minHeight: 72 }}
                />
            </Field>
            <Field label="Bối cảnh / mạch truyện xuyên suốt project *">
                <textarea
                    value={projectStory}
                    onChange={e => setProjectStory(e.target.value)}
                    rows={6}
                    placeholder="Mô tả thế giới, timeline, tone, nhân vật trung tâm và trục truyện chính cho toàn bộ project..."
                    className="input resize-y"
                    style={{ minHeight: 130 }}
                />
            </Field>
            <Field label="Tên video đầu tiên">
                <input value={videoTitle} onChange={e => setVideoTitle(e.target.value)} placeholder="Episode 1" className="input" />
            </Field>
            <Field label="Ý tưởng / Kịch bản video đầu tiên (tùy chọn)">
                <textarea value={story} onChange={e => setStory(e.target.value)} rows={8}
                    placeholder="Mô tả focus của tập đầu tiên. Để trống nếu muốn AI dùng trực tiếp mạch truyện project."
                    className="input resize-y" style={{ minHeight: 160 }} />
            </Field>
            <Field label="Tham chiếu từ YouTube (tùy chọn)">
                <div className="flex flex-col gap-2">
                    <input
                        value={youtubeUrl}
                        onChange={e => setYoutubeUrl(e.target.value)}
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="input"
                    />
                    <div className="flex flex-wrap gap-2">
                        <ActionButton
                            variant="secondary"
                            onClick={() => onAnalyzeYouTube('content')}
                            disabled={!youtubeUrl.trim() || !hasKeys || !!youtubeLoadingMode}
                        >
                            <Sparkles size={12} />
                            {youtubeLoadingMode === 'content' ? 'Đang lấy nội dung...' : 'Lấy nội dung'}
                        </ActionButton>
                        <ActionButton
                            variant="ghost"
                            onClick={() => onAnalyzeYouTube('style')}
                            disabled={!youtubeUrl.trim() || !hasKeys || !!youtubeLoadingMode}
                        >
                            <Sparkles size={12} />
                            {youtubeLoadingMode === 'style' ? 'Đang lấy cấu trúc...' : 'Lấy cấu trúc/phong cách'}
                        </ActionButton>
                    </div>
                    {youtubeMeta && (
                        <div className="text-xs rounded p-2" style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', color: 'var(--accent)' }}>
                            <div className="font-semibold">{youtubeMeta.title}</div>
                            <div style={{ color: 'var(--muted)' }}>
                                {youtubeMeta.channel ? `${youtubeMeta.channel} · ` : ''}
                                caption: {youtubeMeta.transcript_language} ({youtubeMeta.caption_type})
                                {typeof youtubeMeta.duration_sec === 'number' ? ` · ${youtubeMeta.duration_sec}s` : ''}
                            </div>
                        </div>
                    )}
                    {youtubeStatus && (
                        <div className="text-xs rounded p-2" style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', color: 'var(--green)' }}>
                            {youtubeStatus}
                        </div>
                    )}
                    {youtubeError && (
                        <div className="text-xs rounded p-2" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--red)' }}>
                            {youtubeError}
                        </div>
                    )}
                </div>
            </Field>
            <SettingsGrid
                provider={provider}
                setProvider={setProvider}
                material={material}
                setMaterial={setMaterial}
                materials={materials}
                orientation={orientation}
                setOrientation={setOrientation}
                language={language}
                setLanguage={setLanguage}
                sceneCount={sceneCount}
                setSceneCount={setSceneCount}
            />
            {error && <div className="text-xs rounded p-2" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)', border: '1px solid rgba(239,68,68,0.3)' }}>{error}</div>}
            <div className="flex justify-end gap-2 pt-2">
                <ActionButton variant="ghost" onClick={onBack}>← Nghiên cứu</ActionButton>
                <ActionButton variant="primary" onClick={onAnalyze} disabled={!projectStory.trim() || !hasKeys}>
                    <Sparkles size={13} /> Phân tích với {provider.charAt(0).toUpperCase() + provider.slice(1)}
                </ActionButton>
            </div>
        </div>
    )
}

// ─── Step 2: Analyzing ────────────────────────────────────────
function AnalyzingStep({ provider }: { provider: ProviderType }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="w-10 h-10 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
            <div className="text-sm font-semibold" style={{ color: 'var(--text)' }}>Đang phân tích kịch bản...</div>
            <div className="text-xs" style={{ color: 'var(--muted)' }}>Giao tiếp với {provider} API</div>
        </div>
    )
}

// ─── Step 3: Review ───────────────────────────────────────────
function ReviewStep({ extracted, setExtracted, name, setName, videoTitle, setVideoTitle, material, setMaterial, materials, language, onCreate, onBack }: {
    extracted: ExtractedProject; setExtracted: (e: ExtractedProject) => void
    name: string; setName: (n: string) => void
    videoTitle: string; setVideoTitle: (n: string) => void
    materials: string[]
    material: string; setMaterial: (m: string) => void
    language: string; onCreate: () => Promise<void>; onBack: () => void
}) {
    const [expandedChars, setExpandedChars] = useState(true)
    const [expandedScenes, setExpandedScenes] = useState(true)

    const updateChar = (idx: number, field: string, value: string) => {
        const chars = [...extracted.characters]
        chars[idx] = { ...chars[idx], [field]: value }
        setExtracted({ ...extracted, characters: chars })
    }
    const removeChar = (idx: number) => setExtracted({ ...extracted, characters: extracted.characters.filter((_, i) => i !== idx) })
    const addChar = () => setExtracted({ ...extracted, characters: [...extracted.characters, { name: 'Mới', entity_type: 'character' as const, description: '' }] })

    const updateScene = (idx: number, field: string, value: string) => {
        const scenes = [...extracted.scenes]
        scenes[idx] = { ...scenes[idx], [field]: value }
        setExtracted({ ...extracted, scenes })
    }
    const removeScene = (idx: number) => setExtracted({ ...extracted, scenes: extracted.scenes.filter((_, i) => i !== idx) })
    const addScene = () => setExtracted({ ...extracted, scenes: [...extracted.scenes, { prompt: '', video_prompt: '', narrator_text: '', character_names: [] }] })

    return (
        <div className="flex flex-col gap-4">
            {/* Editable project meta */}
            <div className="rounded p-3 flex flex-wrap gap-3 items-center" style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)' }}>
                <span className="text-xs" style={{ color: 'var(--accent)' }}>📽</span>
                <input
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Tên dự án"
                    className="input text-xs font-semibold"
                    style={{ maxWidth: 200, background: 'rgba(59,130,246,0.05)', borderColor: 'rgba(59,130,246,0.3)' }}
                />
                <input
                    value={videoTitle}
                    onChange={e => setVideoTitle(e.target.value)}
                    placeholder="Tên video"
                    className="input text-xs"
                    style={{ maxWidth: 220, background: 'rgba(59,130,246,0.05)', borderColor: 'rgba(59,130,246,0.3)' }}
                />
                <select value={material} onChange={e => setMaterial(e.target.value)} className="input text-xs"
                    style={{ maxWidth: 130, background: 'rgba(59,130,246,0.05)', borderColor: 'rgba(59,130,246,0.3)' }}>
                    {(materials.length > 0 ? materials : FALLBACK_MATERIALS).map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{language}</span>
                <span className="text-xs" style={{ color: 'var(--green)' }}>✓ {extracted.characters.length} thực thể</span>
                <span className="text-xs" style={{ color: 'var(--green)' }}>✓ {extracted.scenes.length} cảnh</span>
            </div>

            {/* Characters */}
            <div className="flex flex-col gap-2">
                <button onClick={() => setExpandedChars(!expandedChars)} className="flex items-center gap-1.5 text-xs font-bold" style={{ color: 'var(--text)' }}>
                    {expandedChars ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    THỰC THỂ ({extracted.characters.length})
                </button>
                {expandedChars && (
                    <div className="flex flex-col gap-2">
                        {extracted.characters.map((ch, i) => (
                            <div key={i} className="rounded p-3 flex gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                <div className="flex flex-col gap-2 flex-1">
                                    <div className="flex gap-2">
                                        <input value={ch.name} onChange={e => updateChar(i, 'name', e.target.value)} className="input font-semibold" style={{ maxWidth: 180 }} placeholder="Tên" />
                                        <select value={ch.entity_type} onChange={e => updateChar(i, 'entity_type', e.target.value)} className="input" style={{ maxWidth: 160 }}>
                                            {ENTITY_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                                        </select>
                                    </div>
                                    <textarea value={ch.description} onChange={e => updateChar(i, 'description', e.target.value)} className="input resize-none text-xs" rows={2} placeholder="Mô tả ngoại hình..." />
                                </div>
                                <button onClick={() => removeChar(i)} style={{ color: 'var(--muted)' }} className="hover:opacity-60 flex-shrink-0"><Trash2 size={13} /></button>
                            </div>
                        ))}
                        <button onClick={addChar} className="text-xs flex items-center gap-1 hover:opacity-70" style={{ color: 'var(--accent)' }}><Plus size={12} /> Thêm thực thể</button>
                    </div>
                )}
            </div>

            {/* Scenes */}
            <div className="flex flex-col gap-2">
                <button onClick={() => setExpandedScenes(!expandedScenes)} className="flex items-center gap-1.5 text-xs font-bold" style={{ color: 'var(--text)' }}>
                    {expandedScenes ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    PHÂN CẢNH ({extracted.scenes.length})
                </button>
                {expandedScenes && (
                    <div className="flex flex-col gap-2">
                        {extracted.scenes.map((sc, i) => (
                            <div key={i} className="rounded p-3 flex gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                <span className="text-xs font-bold w-5 flex-shrink-0 text-right pt-1" style={{ color: 'var(--muted)' }}>#{i + 1}</span>
                                <div className="flex flex-col gap-1.5 flex-1">
                                    <textarea value={sc.prompt} onChange={e => updateScene(i, 'prompt', e.target.value)} className="input resize-none text-xs" rows={2} placeholder="Image prompt (English, action + setting)..." />
                                    <textarea value={sc.video_prompt} onChange={e => updateScene(i, 'video_prompt', e.target.value)} className="input resize-none text-xs" rows={2} placeholder="Video motion: 0-3s: ... 3-6s: ... 6-8s: ..." />
                                    <textarea value={sc.narrator_text} onChange={e => updateScene(i, 'narrator_text', e.target.value)} className="input resize-none text-xs" rows={2} placeholder="Lời dẫn..." />
                                    {sc.character_names.length > 0 && (
                                        <div className="flex flex-wrap gap-1">
                                            {sc.character_names.map(n => <span key={n} className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface)', color: 'var(--accent)' }}>{n}</span>)}
                                        </div>
                                    )}
                                </div>
                                <button onClick={() => removeScene(i)} style={{ color: 'var(--muted)' }} className="hover:opacity-60 flex-shrink-0"><Trash2 size={13} /></button>
                            </div>
                        ))}
                        <button onClick={addScene} className="text-xs flex items-center gap-1 hover:opacity-70" style={{ color: 'var(--accent)' }}><Plus size={12} /> Thêm cảnh</button>
                    </div>
                )}
            </div>

            <div className="flex justify-end gap-2 pt-2 flex-shrink-0">
                <ActionButton variant="ghost" onClick={onBack}>← Phân tích lại</ActionButton>
                <ActionButton variant="primary" onClick={onCreate}>✓ Tạo dự án & Thiết lập</ActionButton>
            </div>
        </div>
    )
}

// ─── Step 4: Creating ─────────────────────────────────────────
function CreatingStep({ status, error }: { status: string; error: string }) {
    return (
        <div className="flex flex-col items-center justify-center py-12 gap-4">
            <div className="w-10 h-10 rounded-full border-2 animate-spin" style={{ borderColor: 'var(--green)', borderTopColor: 'transparent' }} />
            <div className="text-sm font-semibold" style={{ color: 'var(--text)' }}>Setting up project...</div>
            <div className="text-xs" style={{ color: 'var(--muted)' }}>{status}</div>
            {error && (
                <div className="text-xs rounded p-2 max-w-xs text-center" style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--yellow)', border: '1px solid rgba(245,158,11,0.3)' }}>
                    ⚠ {error}
                </div>
            )}
        </div>
    )
}


// ─── Main ─────────────────────────────────────────────────────
export default function AISetupModal({ onClose, onCreated }: Props) {
    const defaults = loadGeneralSettings()
    const [step, setStep] = useState<Step>('research')
    const [provider, setProvider] = useState<ProviderType>(defaults.defaultProvider)
    const [materials, setMaterials] = useState<string[]>([])
    const [name, setName] = useState('')
    const [researchKeyword, setResearchKeyword] = useState('')
    const [projectDescription, setProjectDescription] = useState('')
    const [projectStory, setProjectStory] = useState('')
    const [videoTitle, setVideoTitle] = useState('')
    const [story, setStory] = useState('')
    const [youtubeUrl, setYoutubeUrl] = useState('')
    const [youtubeMeta, setYoutubeMeta] = useState<YouTubeReferencePayload | null>(null)
    const [youtubeLoadingMode, setYoutubeLoadingMode] = useState<YouTubeMode | null>(null)
    const [youtubeError, setYoutubeError] = useState('')
    const [youtubeStatus, setYoutubeStatus] = useState('')
    const [material, setMaterial] = useState(defaults.defaultMaterial)
    const [language, setLanguage] = useState(defaults.defaultLanguage)
    const [orientation, setOrientation] = useState('VERTICAL')
    const [sceneCount, setSceneCount] = useState(8)
    const [error, setError] = useState('')
    const [statusMsg, setStatusMsg] = useState('')
    const [extracted, setExtracted] = useState<ExtractedProject | null>(null)

    const applyResearchKeyword = (raw: string) => {
        const nextKeyword = raw
        const nextAutoName = projectNameFromTopic(nextKeyword)
        const prevAutoName = projectNameFromTopic(researchKeyword)
        setResearchKeyword(nextKeyword)
        if (!nextAutoName) return
        setName(prev => {
            const trimmed = prev.trim()
            if (!trimmed) return nextAutoName
            if (trimmed === prevAutoName) return nextAutoName
            return prev
        })
    }

    useEffect(() => {
        fetchAPI<{ id: string }[]>('/api/materials')
            .then(list => {
                const ids = list.map(m => m.id)
                if (ids.length === 0) return
                setMaterials(ids)
                if (!ids.includes(material)) setMaterial(ids[0])
            })
            .catch(() => {
                setMaterials(FALLBACK_MATERIALS)
                if (!FALLBACK_MATERIALS.includes(material)) setMaterial(FALLBACK_MATERIALS[0])
            })
    }, [])

    const analyze = async () => {
        setError(''); setStep('analyzing')
        try {
            const projectCtx = projectStory.trim()
            const episodeCtx = story.trim()
            const analysisInput = episodeCtx
                ? `PROJECT CONTEXT (global, must stay consistent across all videos):\n${projectCtx}\n\nEPISODE FOCUS (this video only):\n${episodeCtx}`
                : projectCtx
            const result = await analyzeStory(analysisInput, language, sceneCount, provider)
            if (!result.characters || !result.scenes) throw new Error('Invalid AI response')
            setExtracted(result)
            setStep('review')
        } catch (err: any) { setError(err.message ?? 'Analysis failed'); setStep('story') }
    }

    const analyzeYouTube = async (mode: YouTubeMode) => {
        if (!youtubeUrl.trim()) return
        setYoutubeLoadingMode(mode)
        setYoutubeError('')
        setYoutubeStatus('Đang lấy transcript từ YouTube...')
        try {
            const yt = await fetchAPI<YouTubeReferencePayload>('/api/workflows/youtube-reference', {
                method: 'POST',
                body: JSON.stringify({
                    url: youtubeUrl.trim(),
                    language,
                    max_chars: 12000,
                }),
            })
            setYoutubeMeta(yt)
            setYoutubeStatus(`Đã lấy transcript (${yt.transcript_chars} ký tự). Đang phân tích...`)

            const lang = language === 'vi'
                ? 'Vietnamese'
                : language === 'en'
                    ? 'English'
                    : language === 'es'
                        ? 'Spanish'
                        : language
            const systemPrompt = `You are a senior documentary script analyst.
Always return valid JSON only, no markdown.`
            const commonContext = `Language output: ${lang}
Source title: ${yt.title}
Source channel: ${yt.channel ?? 'unknown'}
Source duration: ${yt.duration_sec ?? 'unknown'} seconds
Source upload_date: ${yt.upload_date ?? 'unknown'}
Transcript language: ${yt.transcript_language}
Caption type: ${yt.caption_type}

CURRENT PROJECT CONTEXT (user draft):
${projectStory || '(empty)'}

CURRENT EPISODE FOCUS (user draft):
${story || '(empty)'}

TRANSCRIPT:
${yt.transcript}`

            const prompt = mode === 'content'
                ? `${commonContext}

TASK:
- Preserve core facts/timeline from the source.
- Build a coherent project-wide context and episode-1 script.
- Keep character and setting continuity suitable for multi-video project.

Return JSON:
{
  "project_context": "Global context/storyline for whole project in ${lang}",
  "episode_story": "Detailed script/focus for episode 1 in ${lang}",
  "suggested_video_title": "Episode title in ${lang}",
  "key_points": ["point 1", "point 2", "point 3", "point 4"]
}`
                : `${commonContext}

TASK:
- Extract ONLY structure and storytelling style (hook pattern, pacing, tension curve, scene rhythm).
- Do NOT copy specific names/events/numbers from source transcript.
- Produce a new original context/story while mimicking structure/style quality.

Return JSON:
{
  "project_context": "Original global context based on style only, in ${lang}",
  "episode_story": "Original episode-1 script based on style only, in ${lang}",
  "suggested_video_title": "Episode title in ${lang}",
  "style_blueprint": ["Hook pattern", "Act structure", "Scene pacing", "Narration tone"]
}`

            const parsed = await aiGenerate<{
                project_context?: string
                episode_story?: string
                suggested_video_title?: string
            }>(prompt, systemPrompt, provider)

            const nextProject = (parsed.project_context || '').trim()
            const nextEpisode = (parsed.episode_story || '').trim()
            const nextTitle = (parsed.suggested_video_title || '').trim()

            if (nextProject) {
                setProjectStory(prev => prev ? `${prev}\n\n---\n${nextProject}` : nextProject)
            }
            if (nextEpisode) {
                setStory(prev => prev ? `${prev}\n\n---\n${nextEpisode}` : nextEpisode)
            }
            if (!videoTitle.trim() && nextTitle) setVideoTitle(nextTitle)
            if (!name.trim() && yt.title) setName(yt.title.slice(0, 120))

            setYoutubeStatus(mode === 'content'
                ? `Đã áp dụng nội dung từ video: ${yt.title}`
                : `Đã áp dụng cấu trúc/phong cách từ video: ${yt.title}`)
        } catch (err: any) {
            setYoutubeError(err.message ?? 'YouTube analyze failed')
            setYoutubeStatus('')
        } finally {
            setYoutubeLoadingMode(null)
        }
    }

    const createAll = async () => {
        if (!extracted) return
        setStep('creating')
        let projId: string | null = null

        try {
            // ─── Step 1: Create project (CRITICAL — abort if fails) ──────
            setStatusMsg('Đang tạo dự án...')
            const defaultProjectName =
                projectNameFromTopic(researchKeyword)
                || (youtubeMeta?.title ? normalizeInlineText(youtubeMeta.title).slice(0, 120) : '')
            const finalProjectName = name.trim() || defaultProjectName || 'Dự án chưa đặt tên'
            const proj = await fetchAPI<{ id: string }>('/api/projects', {
                method: 'POST',
                body: JSON.stringify({
                    name: finalProjectName,
                    description: projectDescription.trim() || null,
                    story: projectStory.trim() || null,
                    material, language, orientation,
                    characters: extracted.characters.map(c => ({
                        name: c.name,
                        entity_type: c.entity_type,
                        description: c.description ?? '',
                        voice_description: c.voice_description ?? null,
                    })),
                }),
            })
            projId = proj.id

            // ─── Step 2: Create video (CRITICAL) ─────────────────────────
            setStatusMsg('Creating video...')
            const video = await fetchAPI<{ id: string }>('/api/videos', {
                method: 'POST',
                body: JSON.stringify({
                    project_id: proj.id,
                    title: videoTitle.trim() || `${finalProjectName} — Episode 1`,
                    description: story.trim() || extracted.description || projectStory.trim() || null,
                    display_order: 0,
                    orientation,
                }),
            })

            // ─── Step 3: Create scenes strictly (must match exact count) ──
            const scenes = extracted.scenes
            const MAX_RETRIES = 6
            const RETRY_DELAY = 500 // ms

            const createScene = async (sc: typeof extracted.scenes[0], order: number) => {
                let lastError: any = null
                for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
                    try {
                        await fetchAPI('/api/scenes', {
                            method: 'POST',
                            body: JSON.stringify({
                                video_id: video.id,
                                display_order: order,
                                chain_type: 'ROOT',
                                prompt: sc.prompt || '',
                                video_prompt: sc.video_prompt || null,
                                narrator_text: sc.narrator_text || null,
                                character_names: sc.character_names?.length > 0
                                    ? sc.character_names
                                    : null,
                            }),
                        })
                        return
                    } catch (err: any) {
                        lastError = err
                        if (attempt < MAX_RETRIES - 1) {
                            await new Promise(r => setTimeout(r, RETRY_DELAY * (attempt + 1)))
                        }
                    }
                }
                throw new Error(`Không thể tạo cảnh #${order + 1}: ${lastError?.message ?? 'Unknown error'}`)
            }

            for (let order = 0; order < scenes.length; order++) {
                setStatusMsg(`Đang tạo cảnh... ${order + 1}/${scenes.length}`)
                await createScene(scenes[order], order)
            }

            // Self-heal once if DB returns fewer rows than expected.
            let createdScenes = await fetchAPI<any[]>(`/api/scenes?video_id=${video.id}`).catch(() => [])
            if (createdScenes.length !== scenes.length) {
                const existingOrders = new Set(
                    createdScenes
                        .map(s => Number(s?.display_order))
                        .filter((n: number) => Number.isFinite(n))
                )
                for (let order = 0; order < scenes.length; order++) {
                    if (!existingOrders.has(order)) {
                        setStatusMsg(`Đang bổ sung cảnh thiếu... #${order + 1}`)
                        await createScene(scenes[order], order)
                    }
                }
                createdScenes = await fetchAPI<any[]>(`/api/scenes?video_id=${video.id}`).catch(() => [])
            }

            if (createdScenes.length !== scenes.length) {
                throw new Error(`Lệch số cảnh: yêu cầu ${scenes.length}, đã tạo ${createdScenes.length}`)
            }

            setStatusMsg(`Đã tạo đủ ${createdScenes.length}/${scenes.length} cảnh.`)
            onCreated(proj.id)


        } catch (err: any) {
            // Only revert to review if project itself wasn't created
            if (!projId) {
                setError(err.message ?? 'Creation failed')
                setStep('review')
            } else {
                // Project was created — navigate anyway, show error as banner
                setError(`Project created but hit error: ${err.message}`)
                await new Promise(r => setTimeout(r, 2000))
                onCreated(projId)
            }
        }
    }


    const titles: Record<Step, string> = {
        research: '🔍 Nghiên cứu chủ đề',
        story: '🪄 Tạo project + video với AI',
        analyzing: `⚙️ Đang phân tích với ${provider}...`,
        review: '✏️ Xem & Chỉnh sửa',
        creating: '⚙️ Đang tạo...',
    }

    return (
        <Modal title={titles[step]} onClose={onClose} width={660}>
            {step === 'research' && (
                <ResearchStep provider={provider} setProvider={setProvider} language={language} setLanguage={setLanguage}
                    material={material} setMaterial={setMaterial} materials={materials}
                    orientation={orientation} setOrientation={setOrientation}
                    sceneCount={sceneCount} setSceneCount={setSceneCount}
                    initialTopic={researchKeyword}
                    onTopicChange={applyResearchKeyword}
                    onSkip={() => setStep('story')}
                    onNext={researchSummary => {
                        setProjectStory(prev => prev ? `${prev}\n\n---\n${researchSummary}` : researchSummary)
                        setStory(prev => prev || researchSummary)
                        setStep('story')
                    }}
                />
            )}
            {step === 'story' && (
                <StoryStep
                    projectName={name}
                    setProjectName={setName}
                    projectDescription={projectDescription}
                    setProjectDescription={setProjectDescription}
                    projectStory={projectStory}
                    setProjectStory={setProjectStory}
                    videoTitle={videoTitle}
                    setVideoTitle={setVideoTitle}
                    youtubeUrl={youtubeUrl}
                    setYoutubeUrl={setYoutubeUrl}
                    youtubeMeta={youtubeMeta}
                    youtubeLoadingMode={youtubeLoadingMode}
                    youtubeError={youtubeError}
                    youtubeStatus={youtubeStatus}
                    onAnalyzeYouTube={analyzeYouTube}
                    story={story}
                    setStory={setStory}
                    material={material} setMaterial={setMaterial} materials={materials} language={language} setLanguage={setLanguage}
                    orientation={orientation} setOrientation={setOrientation}
                    sceneCount={sceneCount} setSceneCount={setSceneCount}
                    provider={provider} setProvider={setProvider}
                    onAnalyze={analyze} error={error} onBack={() => setStep('research')} />
            )}
            {step === 'analyzing' && <AnalyzingStep provider={provider} />}
            {step === 'review' && extracted && (
                <ReviewStep extracted={extracted} setExtracted={setExtracted}
                    name={name}
                    setName={setName}
                    videoTitle={videoTitle}
                    setVideoTitle={setVideoTitle}
                    material={material}
                    setMaterial={setMaterial}
                    materials={materials}
                    language={language}
                    onCreate={createAll} onBack={() => setStep('story')} />
            )}
            {step === 'creating' && <CreatingStep status={statusMsg} error={error} />}

        </Modal>
    )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>{label}</label>
            {children}
        </div>
    )
}

function SettingsGrid({
    provider,
    setProvider,
    material,
    setMaterial,
    materials,
    orientation,
    setOrientation,
    language,
    setLanguage,
    sceneCount,
    setSceneCount,
}: {
    provider: ProviderType
    setProvider: (p: ProviderType) => void
    material: string
    setMaterial: (m: string) => void
    materials?: string[]
    orientation: string
    setOrientation: (o: string) => void
    language: string
    setLanguage: (l: string) => void
    sceneCount: number
    setSceneCount: (n: number) => void
}) {
    const estimatedDuration = formatEstimatedDuration(sceneCount)

    return (
        <div className="grid grid-cols-2 gap-3">
            <Field label="Nhà cung cấp AI">
                <select value={provider} onChange={e => setProvider(e.target.value as ProviderType)} className="input">
                    {PROVIDERS.map(p => {
                        const stats = keyStats(p.id)
                        return <option key={p.id} value={p.id}>{p.label} ({stats.active}/{stats.total} active)</option>
                    })}
                </select>
            </Field>
            <Field label="Phong cách hình ảnh">
                <select value={material} onChange={e => setMaterial(e.target.value)} className="input">
                    {(materials?.length ? materials : FALLBACK_MATERIALS).map((m: string) => <option key={m} value={m}>{m}</option>)}
                </select>
            </Field>
            <Field label="Tỉ lệ khung hình">
                <select value={orientation} onChange={e => setOrientation(e.target.value)} className="input">
                    <option value="VERTICAL">9:16 — Dọc (Short)</option>
                    <option value="HORIZONTAL">16:9 — Ngang (YouTube)</option>
                </select>
            </Field>
            <Field label="Ngôn ngữ">
                <select value={language} onChange={e => setLanguage(e.target.value)} className="input">
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                    <option value="es">Español</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                </select>
            </Field>
            <Field label="Số phân cảnh (2–999)">
                <div className="flex flex-col gap-1.5">
                    <input
                        type="number"
                        value={sceneCount}
                        onChange={e => setSceneCount(Math.max(2, Math.min(999, Number(e.target.value) || 2)))}
                        min={2}
                        max={999}
                        className="input"
                        style={{ maxWidth: 90 }}
                    />
                    <div className="flex flex-wrap gap-1">
                        {SCENE_COUNTS.map(n => (
                            <button
                                key={n}
                                type="button"
                                onClick={() => setSceneCount(n)}
                                className="text-xs px-1.5 py-0.5 rounded hover:opacity-80 transition-opacity"
                                style={{
                                    background: sceneCount === n ? 'var(--accent)' : 'var(--surface)',
                                    color: sceneCount === n ? '#fff' : 'var(--muted)',
                                    border: '1px solid var(--border)',
                                }}
                            >
                                {n}
                            </button>
                        ))}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>
                        Thời lượng ước tính: ~ {estimatedDuration} (8 giây/cảnh)
                    </div>
                </div>
            </Field>
        </div>
    )
}
