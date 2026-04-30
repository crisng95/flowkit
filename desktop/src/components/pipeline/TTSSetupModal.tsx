import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, Mic, Upload } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface VoiceTemplate {
    name: string
    audio_path: string
    voice_id?: string
    model_id?: string
    duration?: number
}

interface TTSSettings {
    provider: 'elevenlabs' | 'omnivoice'
    elevenlabs_api_base: string
    elevenlabs_model_id: string
    elevenlabs_default_voice_id: string
    elevenlabs_timeout_sec: number
    elevenlabs_max_retries: number
    elevenlabs_api_key_set: boolean
    elevenlabs_api_key_masked: string
}

interface TTSModelOption {
    model_id: string
    name: string
    description: string
    language_count: number
}

interface TTSVoiceOption {
    voice_id: string
    name: string
    category: string
    labels: Record<string, string>
}

interface TTSCatalog {
    provider: 'elevenlabs' | 'omnivoice'
    source: 'api' | 'fallback' | 'mixed'
    models: TTSModelOption[]
    voices: TTSVoiceOption[]
    warnings: string[]
}

interface SceneForNarration {
    id: string
    display_order: number
    narrator_text?: string | null
}

interface NarrateSceneResult {
    scene_id: string
    display_order: number
    status: 'COMPLETED' | 'FAILED' | 'SKIPPED'
    error?: string | null
}

interface NarrateResult {
    video_id: string
    project_id: string
    scenes: NarrateSceneResult[]
    scenes_narrated: number
    scenes_skipped: number
    scenes_failed: number
    total_narration_duration?: number | null
}

interface Props {
    videoId: string
    projectId: string
    orientation: string
    onClose: () => void
}

export default function TTSSetupModal({ videoId, projectId, orientation, onClose }: Props) {
    const [templates, setTemplates] = useState<VoiceTemplate[]>([])
    const [ttsSettings, setTtsSettings] = useState<TTSSettings | null>(null)
    const [ttsCatalog, setTtsCatalog] = useState<TTSCatalog | null>(null)
    const [selectedTemplate, setSelectedTemplate] = useState('')
    const [voiceId, setVoiceId] = useState('')
    const [modelId, setModelId] = useState('')
    const [newName, setNewName] = useState('')
    const [sampleText, setSampleText] = useState('')
    const [instruct, setInstruct] = useState('')
    const [showCreate, setShowCreate] = useState(false)

    const [importName, setImportName] = useState('')
    const [importPath, setImportPath] = useState('')
    const [importText, setImportText] = useState('')
    const [importInstruct, setImportInstruct] = useState('')

    const [result, setResult] = useState<NarrateResult | null>(null)
    const [error, setError] = useState('')
    const [settingsLoading, setSettingsLoading] = useState(false)
    const [savingDefaults, setSavingDefaults] = useState(false)
    const [catalogLoading, setCatalogLoading] = useState(false)
    const [narrating, setNarrating] = useState(false)
    const [sceneStatsLoading, setSceneStatsLoading] = useState(false)
    const [sceneStatsError, setSceneStatsError] = useState('')
    const [sceneStats, setSceneStats] = useState({ total: 0, withNarrator: 0, withoutNarrator: 0 })
    const modelOptions = ttsCatalog?.models ?? []
    const voiceOptions = ttsCatalog?.voices ?? []
    const isElevenLabs = (ttsSettings?.provider ?? 'elevenlabs') === 'elevenlabs'
    const hasNarratorScenes = sceneStats.withNarrator > 0
    const failedScenes = result?.scenes.filter((scene) => scene.status === 'FAILED') ?? []

    const loadTemplates = useCallback(() => {
        fetchAPI<VoiceTemplate[]>('/api/tts/templates')
            .then(setTemplates)
            .catch(() => setTemplates([]))
    }, [])

    const loadSettings = useCallback(() => {
        setSettingsLoading(true)
        fetchAPI<TTSSettings>('/api/tts/settings')
            .then((settings) => {
                setTtsSettings(settings)
                setVoiceId(prev => prev || settings.elevenlabs_default_voice_id || '')
                setModelId(prev => prev || settings.elevenlabs_model_id || '')
            })
            .catch((e: any) => {
                setTtsSettings(null)
                setError(e.message ?? 'Không tải được cấu hình TTS')
            })
            .finally(() => setSettingsLoading(false))
    }, [])

    const loadCatalog = useCallback((refresh = false) => {
        setCatalogLoading(true)
        fetchAPI<TTSCatalog>(`/api/tts/catalog${refresh ? '?refresh=true' : ''}`)
            .then((catalog) => {
                setTtsCatalog(catalog)
                setModelId((prev) => prev || catalog.models[0]?.model_id || '')
            })
            .catch((e: any) => {
                setTtsCatalog(null)
                setError(e.message ?? 'Không tải được model/voice từ ElevenLabs')
            })
            .finally(() => setCatalogLoading(false))
    }, [])

    const loadSceneStats = useCallback(() => {
        setSceneStatsLoading(true)
        setSceneStatsError('')
        fetchAPI<SceneForNarration[]>(`/api/scenes?video_id=${videoId}`)
            .then((scenes) => {
                const withNarrator = scenes.filter((scene) => (scene.narrator_text ?? '').trim().length > 0).length
                setSceneStats({
                    total: scenes.length,
                    withNarrator,
                    withoutNarrator: Math.max(0, scenes.length - withNarrator),
                })
            })
            .catch((e: any) => {
                setSceneStats({ total: 0, withNarrator: 0, withoutNarrator: 0 })
                setSceneStatsError(e.message ?? 'Không tải được scene của video')
            })
            .finally(() => setSceneStatsLoading(false))
    }, [videoId])

    useEffect(() => {
        loadTemplates()
        loadSettings()
        loadCatalog(false)
        loadSceneStats()
    }, [loadTemplates, loadSettings, loadCatalog, loadSceneStats])

    useEffect(() => {
        if (!ttsCatalog) return

        if (ttsCatalog.models.length > 0) {
            const preferredModel = ttsSettings?.elevenlabs_model_id || ttsCatalog.models[0].model_id
            setModelId((prev) => {
                if (prev && ttsCatalog.models.some((model) => model.model_id === prev)) return prev
                if (preferredModel && ttsCatalog.models.some((model) => model.model_id === preferredModel)) return preferredModel
                return ttsCatalog.models[0].model_id
            })
        }

        if (ttsCatalog.voices.length > 0) {
            const preferredVoice = ttsSettings?.elevenlabs_default_voice_id || ttsCatalog.voices[0].voice_id
            setVoiceId((prev) => {
                if (prev && ttsCatalog.voices.some((voice) => voice.voice_id === prev)) return prev
                if (preferredVoice && ttsCatalog.voices.some((voice) => voice.voice_id === preferredVoice)) return preferredVoice
                return ttsCatalog.voices[0].voice_id
            })
        }
    }, [ttsCatalog, ttsSettings])

    const voiceLabel = (voice: TTSVoiceOption) => {
        const tags: string[] = []
        if (voice.category) tags.push(voice.category)
        const accent = voice.labels?.accent
        if (accent) tags.push(accent)
        return tags.length ? `${voice.name} • ${tags.join(' • ')}` : voice.name
    }

    const modelLabel = (model: TTSModelOption) => {
        const suffix = model.language_count > 0 ? ` • ${model.language_count} ngôn ngữ` : ''
        return `${model.name}${suffix}`
    }

    const ensureModelVoice = () => {
        if (!isElevenLabs) return true
        if (!ttsSettings?.elevenlabs_api_key_set) {
            setError('Chưa cấu hình ElevenLabs API key trong Cài đặt.')
            return false
        }
        if (voiceOptions.length === 0) {
            setError('Chưa tải được danh sách voice từ ElevenLabs. Bấm "Tải lại model/voice" để tải lại.')
            return false
        }
        if (modelOptions.length === 0) {
            setError('Chưa tải được danh sách model từ ElevenLabs. Bấm "Tải lại model/voice" để tải lại.')
            return false
        }
        if (!modelId.trim()) {
            setError('Vui lòng chọn model TTS trước khi thực hiện.')
            return false
        }
        if (!voiceId.trim()) {
            setError('Vui lòng chọn voice TTS trước khi thực hiện.')
            return false
        }
        if (!voiceOptions.some((voice) => voice.voice_id === voiceId.trim())) {
            setError('Voice đã chọn không còn trong catalog ElevenLabs. Hãy tải lại danh sách và chọn lại.')
            return false
        }
        if (!modelOptions.some((model) => model.model_id === modelId.trim())) {
            setError('Model đã chọn không còn trong catalog ElevenLabs. Hãy tải lại danh sách và chọn lại.')
            return false
        }
        return true
    }

    const saveDefaults = async () => {
        if (!ensureModelVoice()) return
        setSavingDefaults(true)
        setError('')
        try {
            const updated = await fetchAPI<TTSSettings>('/api/tts/settings', {
                method: 'PATCH',
                body: JSON.stringify({
                    provider: 'elevenlabs',
                    elevenlabs_default_voice_id: voiceId.trim(),
                    elevenlabs_model_id: modelId.trim(),
                }),
            })
            setTtsSettings(updated)
        } catch (e: any) {
            setError(e.message ?? 'Không lưu được cấu hình TTS')
        } finally {
            setSavingDefaults(false)
        }
    }

    const createTemplate = async () => {
        if (!newName.trim() || !sampleText.trim() || !instruct.trim()) return
        if (!ensureModelVoice()) return
        try {
            const t = await fetchAPI<VoiceTemplate>('/api/tts/templates', {
                method: 'POST',
                body: JSON.stringify({
                    name: newName.trim(),
                    text: sampleText.trim(),
                    instruct: instruct.trim(),
                    voice_id: voiceId.trim() || undefined,
                    model_id: modelId.trim() || undefined,
                }),
            })
            setSelectedTemplate(t.name)
            setShowCreate(false)
            setNewName('')
            setSampleText('')
            setInstruct('')
            loadTemplates()
        } catch (e: any) {
            setError(e.message)
        }
    }

    const importTemplate = async () => {
        if (!importName.trim() || !importPath.trim() || !importText.trim()) return
        if (!ensureModelVoice()) return
        setError('')
        try {
            const t = await fetchAPI<VoiceTemplate>('/api/tts/templates/import', {
                method: 'POST',
                body: JSON.stringify({
                    name: importName.trim(),
                    audio_path: importPath.trim(),
                    text: importText.trim(),
                    instruct: importInstruct.trim(),
                    voice_id: voiceId.trim() || undefined,
                    model_id: modelId.trim() || undefined,
                }),
            })
            setSelectedTemplate(t.name)
            setImportName('')
            setImportPath('')
            setImportText('')
            setImportInstruct('')
            loadTemplates()
        } catch (e: any) {
            setError(e.message ?? 'Import voice template thất bại')
        }
    }

    const chooseImportFile = async () => {
        const picked = await window.electron?.pickFile?.('audio')
        if (picked) {
            setImportPath(picked)
            if (!importName.trim()) {
                const base = picked.split(/[\\/]/).pop()?.replace(/\.[^.]+$/, '') ?? 'voice_template'
                setImportName(base.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 64))
            }
        }
    }

    const deleteTemplate = async (name: string) => {
        await fetchAPI(`/api/tts/templates/${name}`, { method: 'DELETE' })
        setTemplates(prev => prev.filter(t => t.name !== name))
        if (selectedTemplate === name) setSelectedTemplate('')
    }

    const narrate = async () => {
        setError('')
        setResult(null)
        if (!hasNarratorScenes) {
            setError('Video chưa có scene nào chứa narrator_text. Hãy tạo script lời trước khi tạo TTS.')
            return
        }
        if (!ensureModelVoice()) return
        setNarrating(true)
        try {
            const r = await fetchAPI<NarrateResult>(`/api/videos/${videoId}/narrate`, {
                method: 'POST',
                body: JSON.stringify({
                    project_id: projectId,
                    template: selectedTemplate || undefined,
                    orientation,
                    mix: true,
                    voice_id: voiceId.trim() || undefined,
                    model_id: modelId.trim() || undefined,
                }),
            })
            setResult(r)
            if (r.scenes_failed > 0) {
                setError(`Có ${r.scenes_failed} cảnh TTS bị lỗi. Xem chi tiết phía dưới rồi generate lại.`)
            }
        } catch (e: any) {
            setError(e.message)
        } finally {
            setNarrating(false)
        }
    }

    return (
        <Modal title="Thiết Lập Giọng Đọc TTS" onClose={onClose} width={620}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Chọn voice/model từ ElevenLabs, sau đó <strong>Tạo giọng đọc</strong> để render tự động cho toàn bộ scene có <code>narrator_text</code>.
                </div>

                <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Phạm Vi Giọng Đọc</div>
                    {sceneStatsLoading ? (
                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Đang tải scene...</div>
                    ) : (
                        <>
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                                <span className="rounded px-2 py-1" style={{ border: '1px solid var(--border)', background: 'var(--background)' }}>
                                    Tổng cảnh: <strong>{sceneStats.total}</strong>
                                </span>
                                <span className="rounded px-2 py-1" style={{ border: '1px solid rgba(34,197,94,0.35)', background: 'rgba(34,197,94,0.08)', color: '#166534' }}>
                                    Có narrator: <strong>{sceneStats.withNarrator}</strong>
                                </span>
                                <span className="rounded px-2 py-1" style={{ border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.08)', color: '#a16207' }}>
                                    Chưa có narrator: <strong>{sceneStats.withoutNarrator}</strong>
                                </span>
                            </div>
                            <div className="text-xs" style={{ color: 'var(--muted)' }}>
                                Khi bấm tạo, hệ thống sẽ render voice cho <strong>{sceneStats.withNarrator}</strong> scene có narrator_text trong toàn bộ video.
                            </div>
                            {sceneStatsError && (
                                <div className="text-xs rounded p-2" style={{ border: '1px solid rgba(239,68,68,0.25)', background: 'rgba(239,68,68,0.08)', color: '#b91c1c' }}>
                                    {sceneStatsError}
                                </div>
                            )}
                            {sceneStats.withNarrator === 0 && !sceneStatsError && (
                                <div className="text-xs rounded p-2" style={{ border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.10)', color: '#a16207' }}>
                                    Chưa có scene nào có narrator_text. Vui lòng tạo script lời trước.
                                </div>
                            )}
                        </>
                    )}
                </div>

                <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Động Cơ</div>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>
                        Nhà cung cấp: <strong>{ttsSettings?.provider ?? 'đang tải...'}</strong>
                        {ttsSettings && (
                            <>
                                {' '}· Key: <strong>{ttsSettings.elevenlabs_api_key_set ? `đã lưu (${ttsSettings.elevenlabs_api_key_masked || 'ẩn'})` : 'chưa có'}</strong>
                            </>
                        )}
                        {ttsCatalog && (
                            <>
                                {' '}· Danh mục: <strong>{ttsCatalog.source}</strong>
                            </>
                        )}
                    </div>
                    {!!ttsCatalog?.warnings?.length && (
                        <div
                            className="text-xs rounded p-2"
                            style={{ border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.10)', color: '#a16207' }}
                        >
                            {ttsCatalog.warnings.join(' · ')}
                        </div>
                    )}
                    <div className="grid grid-cols-2 gap-2">
                        <select
                            value={voiceId}
                            onChange={(e) => setVoiceId(e.target.value)}
                            className="input"
                            disabled={catalogLoading || voiceOptions.length === 0}
                        >
                            <option value="">
                                {catalogLoading
                                    ? 'Đang tải voice...'
                                    : voiceOptions.length > 0
                                        ? 'Chọn voice từ ElevenLabs...'
                                        : 'Chưa có voice từ ElevenLabs'}
                            </option>
                            {voiceOptions.map((voice) => (
                                <option key={voice.voice_id} value={voice.voice_id}>
                                    {voiceLabel(voice)}
                                </option>
                            ))}
                        </select>
                        <select
                            value={modelId}
                            onChange={(e) => setModelId(e.target.value)}
                            className="input"
                            disabled={catalogLoading || modelOptions.length === 0}
                        >
                            <option value="">
                                {catalogLoading
                                    ? 'Đang tải model...'
                                    : modelOptions.length > 0
                                        ? 'Chọn model từ ElevenLabs...'
                                        : 'Chưa có model từ ElevenLabs'}
                            </option>
                            {modelOptions.map((model) => (
                                <option key={model.model_id} value={model.model_id}>
                                    {modelLabel(model)}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="flex justify-end gap-2">
                        <ActionButton variant="ghost" size="sm" onClick={loadSceneStats} disabled={sceneStatsLoading}>
                            {sceneStatsLoading ? 'Đang tải cảnh...' : 'Tải lại số lượng cảnh'}
                        </ActionButton>
                        <ActionButton variant="ghost" size="sm" onClick={() => loadCatalog(true)} disabled={catalogLoading || settingsLoading}>
                            {catalogLoading ? 'Đang tải...' : 'Tải lại model/voice'}
                        </ActionButton>
                        <ActionButton variant="secondary" size="sm" onClick={saveDefaults} disabled={savingDefaults || settingsLoading}>
                            {savingDefaults ? 'Đang lưu...' : 'Lưu mặc định TTS'}
                        </ActionButton>
                    </div>
                </div>

                <div className="flex flex-col gap-2">
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Mẫu Giọng</div>
                    {templates.length === 0 ? (
                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Chưa có template. Tạo hoặc import ở bên dưới.</div>
                    ) : (
                        <div className="flex flex-col gap-1.5">
                            {templates.map(t => (
                                <div
                                    key={t.name}
                                    className="flex items-center gap-2 rounded px-3 py-2 cursor-pointer"
                                    style={{ background: selectedTemplate === t.name ? 'var(--accent)' : 'var(--card)', border: '1px solid var(--border)' }}
                                    onClick={() => {
                                        setSelectedTemplate(t.name)
                                        if (t.voice_id) setVoiceId(t.voice_id)
                                        if (t.model_id) setModelId(t.model_id)
                                    }}
                                >
                                    <Mic size={12} style={{ color: selectedTemplate === t.name ? '#fff' : 'var(--muted)' }} />
                                    <span className="flex-1 text-xs font-semibold" style={{ color: selectedTemplate === t.name ? '#fff' : 'var(--text)' }}>{t.name}</span>
                                    <span className="text-xs" style={{ color: selectedTemplate === t.name ? 'rgba(255,255,255,0.7)' : 'var(--muted)' }}>
                                        {t.duration ? `${t.duration.toFixed(1)}s` : 'template'}
                                    </span>
                                    <button
                                        onClick={e => { e.stopPropagation(); deleteTemplate(t.name) }}
                                        className="hover:opacity-60"
                                        style={{ color: selectedTemplate === t.name ? '#fff' : 'var(--muted)' }}
                                    >
                                        <Trash2 size={11} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {!showCreate ? (
                        <button onClick={() => setShowCreate(true)} className="text-xs flex items-center gap-1 hover:opacity-70" style={{ color: 'var(--accent)' }}>
                            <Plus size={12} /> Tạo template mới
                        </button>
                    ) : (
                        <div className="flex flex-col gap-2 rounded p-3" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Tên template (vd: main_narrator)" className="input" />
                            <textarea value={sampleText} onChange={e => setSampleText(e.target.value)} rows={3} placeholder="Đoạn văn mẫu để tạo giọng..." className="input resize-none" />
                            <input value={instruct} onChange={e => setInstruct(e.target.value)} placeholder="Mô tả giọng (vd: nam trầm, chậm, giọng tài liệu)" className="input" />
                            <div className="flex gap-2">
                                <ActionButton variant="primary" size="sm" onClick={createTemplate}>Tạo</ActionButton>
                                <ActionButton variant="ghost" size="sm" onClick={() => setShowCreate(false)}>Hủy</ActionButton>
                            </div>
                        </div>
                    )}
                </div>

                <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Import Giọng Có Sẵn (fk:import-voice)</div>
                    <div className="flex gap-2">
                        <input value={importPath} onChange={e => setImportPath(e.target.value)} placeholder="/absolute/path/to/voice.wav" className="input" />
                        <ActionButton variant="secondary" size="sm" onClick={chooseImportFile}><Upload size={11} /> Chọn</ActionButton>
                    </div>
                    <input value={importName} onChange={e => setImportName(e.target.value)} placeholder="Tên template" className="input" />
                    <textarea value={importText} onChange={e => setImportText(e.target.value)} rows={2} placeholder="Nội dung transcript của audio tham chiếu (quan trọng cho chất lượng clone giọng)" className="input resize-none" />
                    <input value={importInstruct} onChange={e => setImportInstruct(e.target.value)} placeholder="Mô tả giọng (tùy chọn)" className="input" />
                    <div className="flex justify-end">
                        <ActionButton variant="ghost" size="sm" onClick={importTemplate}>
                            <Upload size={11} /> Import template
                        </ActionButton>
                    </div>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {result && (
                    <div
                        className="text-xs p-3 rounded flex flex-col gap-1.5"
                        style={result.scenes_failed > 0
                            ? { background: 'rgba(245,158,11,0.12)', color: '#92400e', border: '1px solid rgba(245,158,11,0.3)' }
                            : { background: 'rgba(34,197,94,0.1)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}
                    >
                        <div>
                            {result.scenes_failed > 0
                                ? '⚠ TTS đã chạy xong nhưng còn cảnh lỗi.'
                                : '✓ Đã tạo narration cho toàn bộ video.'}
                        </div>
                        <div>
                            Thành công: <strong>{result.scenes_narrated}</strong> · Bỏ qua: <strong>{result.scenes_skipped}</strong> · Lỗi: <strong>{result.scenes_failed}</strong>
                            {typeof result.total_narration_duration === 'number' && (
                                <> · Tổng thời lượng voice: <strong>{result.total_narration_duration.toFixed(1)}s</strong></>
                            )}
                        </div>
                        {failedScenes.length > 0 && (
                            <div>
                                Cảnh lỗi: {failedScenes.slice(0, 8).map((scene) => `#${scene.display_order + 1}`).join(', ')}
                                {failedScenes.length > 8 ? ` (+${failedScenes.length - 8})` : ''}
                            </div>
                        )}
                    </div>
                )}

                <div className="flex justify-end gap-2 pt-2">
                    <ActionButton variant="ghost" onClick={onClose}>Hủy</ActionButton>
                    <ActionButton
                        variant="primary"
                        onClick={narrate}
                        icon={<Mic size={12} />}
                        loading={narrating}
                        disabled={narrating || sceneStatsLoading || !hasNarratorScenes}
                    >
                        {narrating ? 'Đang tạo...' : `Tạo giọng đọc (${sceneStats.withNarrator})`}
                    </ActionButton>
                </div>
            </div>
        </Modal>
    )
}
