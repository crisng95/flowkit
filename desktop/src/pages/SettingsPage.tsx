import { useState, useEffect } from 'react'
import { Plus, Trash2, RefreshCw, Eye, EyeOff, AlertTriangle, CheckCircle, Clock, Save, Copy, FolderOpen, X } from 'lucide-react'
import {
    loadKeys, saveKeys, loadGeneralSettings, saveGeneralSettings,
    type APIKey, type ProviderType, type GeneralSettings,
} from '../api/ai-service'
import { fetchAPI } from '../api/client'
import type { FlowAccount, FlowAccountsPayload, LicenseCheckResult, LicenseStatus } from '../electron'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Label } from '../components/ui/label'
import { Separator } from '../components/ui/separator'
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select'

type Tab = 'gemini' | 'claude' | 'openai' | 'general' | 'flow' | 'models' | 'materials' | 'tts' | 'license'

const PROVIDERS: { id: ProviderType; label: string; color: string; docUrl: string; placeholder: string }[] = [
    { id: 'gemini', label: 'Gemini', color: '#4285f4', docUrl: 'https://aistudio.google.com/apikey', placeholder: 'AIzaSy...' },
    { id: 'claude', label: 'Claude', color: '#d97706', docUrl: 'https://console.anthropic.com/keys', placeholder: 'sk-ant-...' },
    { id: 'openai', label: 'OpenAI', color: '#10b981', docUrl: 'https://platform.openai.com/api-keys', placeholder: 'sk-proj-...' },
]

const FALLBACK_MATERIALS = ['realistic', '3d_pixar', 'anime', 'watercolor', 'cinematic']
const LANGUAGES = [
    { code: 'vi', label: 'Tiếng Việt' }, { code: 'en', label: 'Tiếng Anh' },
    { code: 'es', label: 'Tiếng Tây Ban Nha' },
    { code: 'zh', label: 'Tiếng Trung' }, { code: 'ja', label: 'Tiếng Nhật' }, { code: 'ko', label: 'Tiếng Hàn' },
]

const LICENSE_STATUS_LABEL: Record<LicenseStatus, string> = {
    ACTIVE: 'Đã kích hoạt',
    EXPIRED: 'Đã hết hạn',
    REVOKED: 'Đã thu hồi',
    PENDING: 'Chưa kích hoạt',
    ERROR: 'Lỗi kết nối',
}

function formatDateTime(value: string | null): string {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('vi-VN')
}

function licenseStatusVariant(status: LicenseStatus): 'success' | 'destructive' | 'secondary' {
    if (status === 'ACTIVE') return 'success'
    if (status === 'ERROR') return 'secondary'
    return 'destructive'
}

function normalizeMaterialId(raw: string): string {
    let slug = raw.trim().toLowerCase()
        .replace(/[^a-z0-9_]+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '')
    if (!slug) slug = 'material'
    if (!/^[a-z]/.test(slug)) slug = `m_${slug}`
    if (slug.length < 2) slug = `${slug}1`
    if (slug.length > 64) slug = slug.slice(0, 64)
    return slug
}

function looksLikeProviderKey(provider: ProviderType, key: string): boolean {
    const value = key.trim()
    if (!value || /^\d+$/.test(value) || value.length < 12) return false
    if (provider === 'gemini') return value.startsWith('AIza')
    if (provider === 'claude') return value.startsWith('sk-ant-')
    // OpenAI keys are usually sk-... or sk-proj-...
    return value.startsWith('sk-')
}

function keyFormatHint(provider: ProviderType): string {
    if (provider === 'gemini') return 'AIza...'
    if (provider === 'claude') return 'sk-ant-...'
    return 'sk-proj-... / sk-...'
}

interface MaterialItem {
    id: string; name: string; style_instruction: string
    negative_prompt?: string | null; scene_prefix?: string | null
    lighting?: string | null; is_builtin?: boolean
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
    preview_url?: string | null
    labels: Record<string, string>
}

interface TTSCatalog {
    provider: 'elevenlabs' | 'omnivoice'
    source: 'api' | 'fallback' | 'mixed'
    models: TTSModelOption[]
    voices: TTSVoiceOption[]
    warnings: string[]
}

interface ModelsPayload {
    video_models: Record<string, Record<string, Record<string, string>>>
    image_models: Record<string, string>
    upscale_models: Record<string, string>
}

function generateId() { return Math.random().toString(36).slice(2, 10) }

function StatusIcon({ status }: { status: APIKey['status'] }) {
    if (status === 'active') return <CheckCircle size={13} className="text-green-500" />
    if (status === 'limited') return <Clock size={13} className="text-amber-500" />
    return <AlertTriangle size={13} className="text-red-500" />
}

function formatLimited(ts?: number) {
    if (!ts) return ''
    const mins = Math.round((Date.now() - ts) / 60000)
    return `Giới hạn ${mins} phút trước`
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-[hsl(var(--muted-foreground))]">{label}</Label>
            {children}
        </div>
    )
}

function modelOptionLabel(item: TTSModelOption): string {
    const chunks = [item.name]
    if (item.language_count > 0) chunks.push(`${item.language_count} ngôn ngữ`)
    return chunks.join(' • ')
}

function voiceOptionLabel(item: TTSVoiceOption): string {
    const tags: string[] = []
    if (item.category) tags.push(item.category)
    const accent = item.labels?.accent
    if (accent) tags.push(accent)
    return tags.length ? `${item.name} • ${tags.join(' • ')}` : item.name
}

// ─── Per-Provider Keys Panel ──────────────────────────────────
function ProviderKeysPanel({ provider, color, docUrl, placeholder }: {
    provider: ProviderType; color: string; docUrl: string; placeholder: string
}) {
    const [keys, setKeys] = useState<APIKey[]>([])
    const [newLabel, setNewLabel] = useState('')
    const [newKey, setNewKey] = useState('')
    const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
    const [formError, setFormError] = useState('')

    useEffect(() => { setKeys(loadKeys(provider)) }, [provider])

    function persist(updated: APIKey[]) { setKeys(updated); saveKeys(provider, updated) }
    function addKey() {
        const key = newKey.trim()
        if (!key) return
        if (!looksLikeProviderKey(provider, key)) {
            setFormError(`Key không đúng định dạng cho ${provider.toUpperCase()}. Ví dụ: ${keyFormatHint(provider)}`)
            return
        }
        setFormError('')
        const label = newLabel.trim()
        const existing = keys.find(k => k.key.trim() === key)
        if (existing) {
            persist(keys.map(k => k.id === existing.id
                ? { ...k, key, status: 'active', limitedAt: undefined, label: label || k.label }
                : k))
        } else {
            persist([...keys, { id: generateId(), label: label || `Key ${keys.length + 1}`, key, status: 'active' }])
        }
        setNewLabel(''); setNewKey('')
    }
    function removeKey(id: string) { persist(keys.filter(k => k.id !== id)) }
    function resetKey(id: string) { persist(keys.map(k => k.id === id ? { ...k, status: 'active', limitedAt: undefined } : k)) }
    function toggleShow(id: string) { setShowKeys(prev => ({ ...prev, [id]: !prev[id] })) }

    const activeCount = keys.filter(k => k.status === 'active').length

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
                <Badge variant="outline" style={{ color }}>{activeCount} keys hoạt động</Badge>
                {keys.length > activeCount && (
                    <Badge variant="secondary">{keys.length - activeCount} bị giới hạn/lỗi</Badge>
                )}
            </div>

            {keys.map(k => (
                <Card key={k.id}>
                    <CardContent className="p-3 flex items-start gap-3">
                        <StatusIcon status={k.status} />
                        <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                            <div className="text-xs font-semibold">{k.label}</div>
                            <div className="text-xs font-mono truncate text-[hsl(var(--muted-foreground))]">
                                {showKeys[k.id] ? k.key : `${k.key.slice(0, 10)}${'•'.repeat(16)}${k.key.slice(-4)}`}
                            </div>
                            {k.status === 'limited' && (
                                <div className="text-xs text-amber-500">{formatLimited(k.limitedAt)}</div>
                            )}
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                            <Button variant="ghost" size="icon" onClick={() => toggleShow(k.id)} className="h-7 w-7">
                                {showKeys[k.id] ? <EyeOff size={12} /> : <Eye size={12} />}
                            </Button>
                            {k.status !== 'active' && (
                                <Button variant="ghost" size="icon" onClick={() => resetKey(k.id)} className="h-7 w-7">
                                    <RefreshCw size={12} />
                                </Button>
                            )}
                            <Button variant="destructive" size="icon" onClick={() => removeKey(k.id)} className="h-7 w-7">
                                <Trash2 size={12} />
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            ))}

            <Card className="border-dashed">
                <CardContent className="p-4 flex flex-col gap-3">
                    <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Thêm API Key</div>
                    <div className="flex gap-2">
                        <Input value={newLabel} onChange={e => setNewLabel(e.target.value)} placeholder="Nhãn (tùy chọn)" className="max-w-[140px] text-xs" />
                        <Input value={newKey} onChange={e => { setNewKey(e.target.value); if (formError) setFormError('') }} placeholder={placeholder} type="password"
                            className="flex-1 text-xs" onKeyDown={e => { if (e.key === 'Enter') addKey() }} />
                        <Button size="sm" onClick={addKey}><Plus size={12} /> Thêm</Button>
                    </div>
                    {formError && <p className="text-xs text-red-500">{formError}</p>}
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Lấy API key:{' '}
                        <a href={docUrl} target="_blank" rel="noreferrer" style={{ color }} className="underline">
                            {new URL(docUrl).hostname} →
                        </a>
                    </p>
                </CardContent>
            </Card>
        </div>
    )
}

// ─── General Panel ────────────────────────────────────────────
function GeneralPanel({ materials }: { materials: string[] }) {
    const [settings, setSettings] = useState<GeneralSettings>(loadGeneralSettings())
    const hasDirectoryPicker = Boolean(window.electron?.pickDirectory)

    useEffect(() => {
        if (materials.length === 0) return
        if (!materials.includes(settings.defaultMaterial)) {
            const next = { ...settings, defaultMaterial: materials[0] }
            setSettings(next); saveGeneralSettings(next)
        }
    }, [materials, settings])

    function update(field: keyof GeneralSettings, value: string) {
        const next = { ...settings, [field]: value }
        setSettings(next); saveGeneralSettings(next)
    }

    const pickExportFolder = async () => {
        if (!window.electron?.pickDirectory) return
        const selected = await window.electron.pickDirectory()
        if (!selected) return
        update('exportRootDir', selected)
    }

    const openExportFolder = async () => {
        if (!settings.exportRootDir || !window.electron?.openPath) return
        await window.electron.openPath(settings.exportRootDir)
    }

    const options = materials.length > 0 ? materials : FALLBACK_MATERIALS

    return (
        <div className="flex flex-col gap-4 max-w-2xl">
            <Field label="AI Provider mặc định">
                <Select value={settings.defaultProvider} onValueChange={(v: string) => update('defaultProvider', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        {PROVIDERS.map(p => <SelectItem key={p.id} value={p.id}>{p.label}</SelectItem>)}
                    </SelectContent>
                </Select>
            </Field>
            <Field label="Ngôn ngữ mặc định">
                <Select value={settings.defaultLanguage} onValueChange={(v: string) => update('defaultLanguage', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        {LANGUAGES.map(l => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}
                    </SelectContent>
                </Select>
            </Field>
            <Field label="Chất liệu mặc định">
                <Select value={settings.defaultMaterial} onValueChange={(v: string) => update('defaultMaterial', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        {options.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                    </SelectContent>
                </Select>
            </Field>
            <Field label="Thư mục export media (ảnh + video)">
                <div className="flex flex-col gap-2">
                    <div className="flex gap-2">
                        <Input
                            value={settings.exportRootDir}
                            readOnly
                            placeholder="Chưa chọn thư mục (mặc định lưu theo output nội bộ)"
                            className="text-xs font-mono"
                        />
                        <Button
                            variant="secondary"
                            onClick={() => void pickExportFolder()}
                            disabled={!hasDirectoryPicker}
                            className="gap-1.5"
                        >
                            <FolderOpen size={12} /> Chọn
                        </Button>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void openExportFolder()}
                            disabled={!settings.exportRootDir || !window.electron?.openPath}
                            className="gap-1.5"
                        >
                            <FolderOpen size={12} /> Mở thư mục
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => update('exportRootDir', '')}
                            disabled={!settings.exportRootDir}
                            className="gap-1.5"
                        >
                            <X size={12} /> Bỏ chọn
                        </Button>
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Khi export, app sẽ tạo thư mục con theo project và video, rồi lưu ảnh/video theo thứ tự scene.
                    </p>
                </div>
            </Field>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Các mặc định này áp dụng cho dự án mới. Mỗi dự án có thể thay đổi riêng.
            </p>
        </div>
    )
}

// ─── Models Panel ─────────────────────────────────────────────
function ModelsPanel() {
    const [models, setModels] = useState<ModelsPayload | null>(null)
    const [videoDrafts, setVideoDrafts] = useState<Record<string, { landscape: string; portrait: string }>>({})
    const [imageDrafts, setImageDrafts] = useState<Record<string, string>>({})
    const [upscaleDrafts, setUpscaleDrafts] = useState<Record<string, string>>({})
    const [savingKey, setSavingKey] = useState('')
    const [error, setError] = useState('')

    const loadModels = async () => {
        try {
            setError('')
            const data = await fetchAPI<ModelsPayload>('/api/models')
            setModels(data)
            const nextVideo: Record<string, { landscape: string; portrait: string }> = {}
            Object.entries(data.video_models ?? {}).forEach(([tier, genTypes]) => {
                Object.entries(genTypes ?? {}).forEach(([genType, ratios]) => {
                    const k = `${tier}:${genType}`
                    nextVideo[k] = { landscape: ratios?.VIDEO_ASPECT_RATIO_LANDSCAPE ?? '', portrait: ratios?.VIDEO_ASPECT_RATIO_PORTRAIT ?? '' }
                })
            })
            setVideoDrafts(nextVideo)
            setImageDrafts({ ...(data.image_models ?? {}) })
            setUpscaleDrafts({ ...(data.upscale_models ?? {}) })
        } catch (e: any) { setError(e.message ?? 'Không tải được models') }
    }

    useEffect(() => { loadModels() }, [])

    const saveVideoRow = async (tier: string, genType: string) => {
        const k = `${tier}:${genType}`; const draft = videoDrafts[k]; if (!draft) return
        setSavingKey(`video:${k}`); setError('')
        try {
            await fetchAPI('/api/models', { method: 'PATCH', body: JSON.stringify({ video_models: { [tier]: { [genType]: { VIDEO_ASPECT_RATIO_LANDSCAPE: draft.landscape, VIDEO_ASPECT_RATIO_PORTRAIT: draft.portrait } } } }) })
            await loadModels()
        } catch (e: any) { setError(e.message ?? 'Lỗi lưu video model') } finally { setSavingKey('') }
    }

    const saveImageKey = async (key: string) => {
        setSavingKey(`image:${key}`); setError('')
        try {
            await fetchAPI('/api/models', { method: 'PATCH', body: JSON.stringify({ image_models: { [key]: imageDrafts[key] } }) })
            await loadModels()
        } catch (e: any) { setError(e.message ?? 'Lỗi lưu image model') } finally { setSavingKey('') }
    }

    const saveUpscaleKey = async (key: string) => {
        setSavingKey(`upscale:${key}`); setError('')
        try {
            await fetchAPI('/api/models', { method: 'PATCH', body: JSON.stringify({ upscale_models: { [key]: upscaleDrafts[key] } }) })
            await loadModels()
        } catch (e: any) { setError(e.message ?? 'Lỗi lưu upscale model') } finally { setSavingKey('') }
    }

    if (!models) return <div className="text-sm text-[hsl(var(--muted-foreground))]">Đang tải cấu hình model...</div>

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={loadModels}><RefreshCw size={12} /> Tải lại</Button>
                <span className="text-xs text-[hsl(var(--muted-foreground))]">Thay đổi được áp dụng ngay lập tức trên agent.</span>
            </div>

            {error && <div className="text-xs p-2 rounded bg-red-50 text-red-600">{error}</div>}

            <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Model Video</div>
            <div className="flex flex-col gap-2">
                {Object.entries(models.video_models ?? {}).map(([tier, genTypes]) =>
                    Object.keys(genTypes ?? {}).map(genType => {
                        const k = `${tier}:${genType}`
                        const draft = videoDrafts[k] ?? { landscape: '', portrait: '' }
                        return (
                            <Card key={k}>
                                <CardContent className="p-3 flex flex-col gap-2">
                                    <div className="text-xs font-semibold">{tier} · {genType}</div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <Input value={draft.landscape} onChange={e => setVideoDrafts(prev => ({ ...prev, [k]: { ...draft, landscape: e.target.value } }))} className="text-xs" placeholder="Model ngang (16:9)" />
                                        <Input value={draft.portrait} onChange={e => setVideoDrafts(prev => ({ ...prev, [k]: { ...draft, portrait: e.target.value } }))} className="text-xs" placeholder="Model dọc (9:16)" />
                                    </div>
                                    <Button size="sm" onClick={() => saveVideoRow(tier, genType)} disabled={savingKey === `video:${k}`}>
                                        <Save size={11} /> {savingKey === `video:${k}` ? 'Đang lưu...' : 'Lưu'}
                                    </Button>
                                </CardContent>
                            </Card>
                        )
                    })
                )}
            </div>

            <Separator />
            <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Model Ảnh</div>
            <div className="flex flex-col gap-2">
                {Object.keys(models.image_models ?? {}).map(key => (
                    <Card key={key}>
                        <CardContent className="p-3 flex items-center gap-2">
                            <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))] min-w-[150px]">{key}</span>
                            <Input value={imageDrafts[key] ?? ''} onChange={e => setImageDrafts(prev => ({ ...prev, [key]: e.target.value }))} className="flex-1 text-xs" />
                            <Button size="icon" onClick={() => saveImageKey(key)} disabled={savingKey === `image:${key}`} className="h-8 w-8"><Save size={11} /></Button>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Separator />
            <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Model Upscale</div>
            <div className="flex flex-col gap-2">
                {Object.keys(models.upscale_models ?? {}).map(key => (
                    <Card key={key}>
                        <CardContent className="p-3 flex items-center gap-2">
                            <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))] min-w-[150px]">{key}</span>
                            <Input value={upscaleDrafts[key] ?? ''} onChange={e => setUpscaleDrafts(prev => ({ ...prev, [key]: e.target.value }))} className="flex-1 text-xs" />
                            <Button size="icon" onClick={() => saveUpscaleKey(key)} disabled={savingKey === `upscale:${key}`} className="h-8 w-8"><Save size={11} /></Button>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}

// ─── Materials Panel ──────────────────────────────────────────
function MaterialsPanel({ onChanged }: { onChanged: () => void }) {
    const [materials, setMaterials] = useState<MaterialItem[]>([])
    const [error, setError] = useState('')
    const [creating, setCreating] = useState(false)
    const [form, setForm] = useState({ id: '', name: '', style_instruction: '', negative_prompt: '', scene_prefix: '', lighting: '' })

    const loadMaterials = async () => {
        try {
            setError('')
            const list = await fetchAPI<MaterialItem[]>('/api/materials')
            setMaterials(list); onChanged()
        } catch (e: any) { setError(e.message ?? 'Không tải được chất liệu') }
    }

    useEffect(() => { loadMaterials() }, [])

    const createMaterial = async () => {
        if (!form.id.trim() || !form.name.trim() || !form.style_instruction.trim()) {
            setError('id, name, style_instruction là bắt buộc'); return
        }
        if (form.style_instruction.trim().length < 10) {
            setError('style_instruction tối thiểu 10 ký tự'); return
        }
        const normalizedId = normalizeMaterialId(form.id)
        if (!/^[a-z][a-z0-9_]{1,63}$/.test(normalizedId)) {
            setError("id không hợp lệ. Định dạng đúng: ^[a-z][a-z0-9_]{1,63}$")
            return
        }

        const negativePrompt = form.negative_prompt.trim()
        const scenePrefix = form.scene_prefix.trim()
        const lighting = form.lighting.trim()
        const payload: Record<string, string> = {
            id: normalizedId,
            name: form.name.trim(),
            style_instruction: form.style_instruction.trim(),
        }
        if (negativePrompt) payload.negative_prompt = negativePrompt
        if (scenePrefix) payload.scene_prefix = scenePrefix
        if (lighting) payload.lighting = lighting

        setCreating(true); setError('')
        try {
            await fetchAPI('/api/materials', { method: 'POST', body: JSON.stringify(payload) })
            setForm({ id: '', name: '', style_instruction: '', negative_prompt: '', scene_prefix: '', lighting: '' })
            await loadMaterials()
        } catch (e: any) { setError(e.message ?? 'Lỗi tạo chất liệu') } finally { setCreating(false) }
    }

    const deleteMaterial = async (id: string) => {
        if (!confirm(`Xóa chất liệu '${id}'?`)) return
        try { await fetchAPI(`/api/materials/${id}`, { method: 'DELETE' }); await loadMaterials() }
        catch (e: any) { setError(e.message ?? 'Lỗi xóa chất liệu') }
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={loadMaterials}><RefreshCw size={12} /> Tải lại</Button>
                <Badge variant="secondary">{materials.length} chất liệu</Badge>
            </div>
            {error && <div className="text-xs p-2 rounded bg-red-50 text-red-600">{error}</div>}

            <div className="flex flex-col gap-2">
                {materials.map(m => (
                    <Card key={m.id}>
                        <CardContent className="p-3 flex items-start gap-3">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-xs font-semibold">{m.name}</span>
                                    <Badge variant="outline" className="text-xs">{m.id}</Badge>
                                    <Badge variant={m.is_builtin ? 'secondary' : 'success'} className="text-xs">
                                        {m.is_builtin ? 'có sẵn' : 'tùy chỉnh'}
                                    </Badge>
                                </div>
                                <div className="text-xs mt-1 text-[hsl(var(--muted-foreground))]">
                                    {m.style_instruction?.slice(0, 220)}{(m.style_instruction?.length ?? 0) > 220 ? '…' : ''}
                                </div>
                            </div>
                            {!m.is_builtin && (
                                <Button variant="destructive" size="icon" onClick={() => deleteMaterial(m.id)} className="h-7 w-7 flex-shrink-0">
                                    <Trash2 size={11} />
                                </Button>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Card className="border-dashed">
                <CardContent className="p-4 flex flex-col gap-3">
                    <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Tạo Chất Liệu Mới</div>
                    <div className="grid grid-cols-2 gap-2">
                        <Input className="text-xs" placeholder="id (vd. retro_vhs)" value={form.id} onChange={e => setForm(p => ({ ...p, id: e.target.value }))} />
                        <Input className="text-xs" placeholder="Tên hiển thị" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
                    </div>
                    <Textarea className="text-xs resize-y" rows={3} placeholder="style_instruction (bắt buộc)" value={form.style_instruction} onChange={e => setForm(p => ({ ...p, style_instruction: e.target.value }))} />
                    <Textarea className="text-xs resize-y" rows={2} placeholder="negative_prompt (tùy chọn)" value={form.negative_prompt} onChange={e => setForm(p => ({ ...p, negative_prompt: e.target.value }))} />
                    <Textarea className="text-xs resize-y" rows={2} placeholder="scene_prefix (tùy chọn)" value={form.scene_prefix} onChange={e => setForm(p => ({ ...p, scene_prefix: e.target.value }))} />
                    <Input className="text-xs" placeholder="lighting (tùy chọn)" value={form.lighting} onChange={e => setForm(p => ({ ...p, lighting: e.target.value }))} />
                    <Button size="sm" onClick={createMaterial} disabled={creating}>
                        <Plus size={11} /> {creating ? 'Đang tạo...' : 'Tạo Chất Liệu'}
                    </Button>
                </CardContent>
            </Card>
        </div>
    )
}

// ─── TTS Panel ───────────────────────────────────────────────
function TTSPanel() {
    const [settings, setSettings] = useState<TTSSettings | null>(null)
    const [catalog, setCatalog] = useState<TTSCatalog | null>(null)
    const [provider, setProvider] = useState<'elevenlabs' | 'omnivoice'>('elevenlabs')
    const [apiBase, setApiBase] = useState('https://api.elevenlabs.io')
    const [apiKey, setApiKey] = useState('')
    const [modelId, setModelId] = useState('eleven_multilingual_v2')
    const [voiceId, setVoiceId] = useState('')
    const [timeoutSec, setTimeoutSec] = useState('60')
    const [maxRetries, setMaxRetries] = useState('2')
    const [clearKey, setClearKey] = useState(false)
    const [saving, setSaving] = useState(false)
    const [catalogLoading, setCatalogLoading] = useState(false)
    const [error, setError] = useState('')
    const [info, setInfo] = useState('')
    const modelOptions = catalog?.models ?? []
    const voiceOptions = catalog?.voices ?? []
    const modelInOptions = modelOptions.some((item) => item.model_id === modelId)
    const voiceInOptions = voiceOptions.some((item) => item.voice_id === voiceId)

    const hydrate = (s: TTSSettings) => {
        setSettings(s)
        setProvider(s.provider)
        setApiBase(s.elevenlabs_api_base || 'https://api.elevenlabs.io')
        setModelId(s.elevenlabs_model_id || 'eleven_multilingual_v2')
        setVoiceId(s.elevenlabs_default_voice_id || '')
        setTimeoutSec(String(s.elevenlabs_timeout_sec || 60))
        setMaxRetries(String(s.elevenlabs_max_retries || 2))
    }

    const loadSettings = async () => {
        try {
            setError('')
            const data = await fetchAPI<TTSSettings>('/api/tts/settings')
            hydrate(data)
        } catch (e: any) {
            setError(e.message ?? 'Không tải được cấu hình TTS')
        }
    }

    const loadCatalog = async (refresh = false) => {
        setCatalogLoading(true)
        try {
            const data = await fetchAPI<TTSCatalog>(`/api/tts/catalog${refresh ? '?refresh=true' : ''}`)
            setCatalog(data)
            if (!modelId && data.models[0]) setModelId(data.models[0].model_id)
        } catch (e: any) {
            setCatalog(null)
            setError(e.message ?? 'Không tải được catalog TTS')
        } finally {
            setCatalogLoading(false)
        }
    }

    useEffect(() => {
        loadSettings()
        loadCatalog(false)
    }, [])

    const save = async () => {
        setSaving(true)
        setError('')
        setInfo('')
        try {
            const payload: Record<string, unknown> = {
                provider,
                elevenlabs_api_base: apiBase.trim(),
                elevenlabs_model_id: modelId.trim(),
                elevenlabs_default_voice_id: voiceId.trim(),
                elevenlabs_timeout_sec: Number(timeoutSec || '60'),
                elevenlabs_max_retries: Number(maxRetries || '2'),
                clear_elevenlabs_api_key: clearKey,
            }
            if (apiKey.trim()) payload.elevenlabs_api_key = apiKey.trim()
            const data = await fetchAPI<TTSSettings>('/api/tts/settings', {
                method: 'PATCH',
                body: JSON.stringify(payload),
            })
            hydrate(data)
            setApiKey('')
            setClearKey(false)
            setInfo('Đã lưu cấu hình TTS.')
        } catch (e: any) {
            setError(e.message ?? 'Lỗi lưu cấu hình TTS')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="flex flex-col gap-4 max-w-2xl">
            <div className="text-xs text-[hsl(var(--muted-foreground))]">
                TTS engine chạy ở backend agent. Khuyến nghị dùng ElevenLabs cho chất lượng giọng ổn định.
            </div>

            {error && <div className="text-xs p-2 rounded bg-red-50 text-red-600">{error}</div>}
            {info && <div className="text-xs p-2 rounded bg-green-50 text-green-700">{info}</div>}
            {!!catalog?.warnings?.length && (
                <div className="text-xs p-2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                    {catalog.warnings.join(' · ')}
                </div>
            )}

            <Card>
                <CardContent className="p-4 flex flex-col gap-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <Field label="Nhà cung cấp TTS">
                            <Select value={provider} onValueChange={(v: string) => setProvider(v as 'elevenlabs' | 'omnivoice')}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="elevenlabs">ElevenLabs</SelectItem>
                                    <SelectItem value="omnivoice">OmniVoice (legacy/local)</SelectItem>
                                </SelectContent>
                            </Select>
                        </Field>
                        <Field label="API Base">
                            <Input value={apiBase} onChange={e => setApiBase(e.target.value)} className="text-xs" />
                        </Field>
                        <Field label="Mã model">
                            <Select
                                value={modelId || '__none__'}
                                onValueChange={(v: string) => setModelId(v === '__none__' ? '' : v)}
                                disabled={provider !== 'elevenlabs' || modelOptions.length === 0}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={catalogLoading ? 'Đang tải models...' : 'Chọn model'} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__none__">Chọn model...</SelectItem>
                                    {!modelInOptions && !!modelId && (
                                        <SelectItem value={modelId}>{`Custom: ${modelId}`}</SelectItem>
                                    )}
                                    {modelOptions.map((item) => (
                                        <SelectItem key={item.model_id} value={item.model_id}>
                                            {modelOptionLabel(item)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </Field>
                        <Field label="Voice mặc định">
                            {(catalog?.voices?.length ?? 0) > 0 ? (
                                <Select
                                    value={voiceId || '__none__'}
                                    onValueChange={(v: string) => setVoiceId(v === '__none__' ? '' : v)}
                                    disabled={provider !== 'elevenlabs'}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder={catalogLoading ? 'Đang tải voices...' : 'Chọn voice'} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="__none__">Chọn voice...</SelectItem>
                                        {!voiceInOptions && !!voiceId && (
                                            <SelectItem value={voiceId}>{`Custom: ${voiceId}`}</SelectItem>
                                        )}
                                        {voiceOptions.map((item) => (
                                            <SelectItem key={item.voice_id} value={item.voice_id}>
                                                {voiceOptionLabel(item)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            ) : (
                                <Input
                                    value={voiceId}
                                    onChange={e => setVoiceId(e.target.value)}
                                    className="text-xs"
                                    placeholder="Bắt buộc khi dùng ElevenLabs"
                                />
                            )}
                        </Field>
                        <Field label="Timeout (giây)">
                            <Input value={timeoutSec} onChange={e => setTimeoutSec(e.target.value)} className="text-xs" />
                        </Field>
                        <Field label="Số lần thử lại">
                            <Input value={maxRetries} onChange={e => setMaxRetries(e.target.value)} className="text-xs" />
                        </Field>
                    </div>

                    <Separator />

                    <div className="flex flex-col gap-2">
                        <Field label="API key ElevenLabs">
                            <Input
                                type="password"
                                value={apiKey}
                                onChange={e => setApiKey(e.target.value)}
                                className="text-xs"
                                placeholder={settings?.elevenlabs_api_key_set ? `Đang lưu: ${settings.elevenlabs_api_key_masked || 'hidden'} (nhập key mới để thay)` : 'Nhập API key ElevenLabs'}
                            />
                        </Field>
                        <label className="inline-flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))] cursor-pointer">
                            <input type="checkbox" checked={clearKey} onChange={e => setClearKey(e.target.checked)} />
                            Xóa API key hiện tại
                        </label>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button onClick={save} disabled={saving}>
                            <Save size={12} /> {saving ? 'Đang lưu...' : 'Lưu TTS'}
                        </Button>
                        <Button variant="ghost" onClick={loadSettings}>
                            <RefreshCw size={12} /> Tải lại
                        </Button>
                        <Button variant="ghost" onClick={() => loadCatalog(true)} disabled={catalogLoading}>
                            <RefreshCw size={12} className={catalogLoading ? 'animate-spin' : ''} /> Tải model/voice
                        </Button>
                        {settings?.elevenlabs_api_key_set && (
                            <Badge variant="success">Đã lưu key</Badge>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

// ─── Flow Accounts Panel ─────────────────────────────────────
function FlowAccountsPanel() {
    const hasBridge = Boolean(
        window.electron?.flowAccountsList
        && window.electron?.flowAccountsCreate
        && window.electron?.flowAccountsSetActive
        && window.electron?.flowAccountsLogout
    )

    const [payload, setPayload] = useState<FlowAccountsPayload | null>(null)
    const [drafts, setDrafts] = useState<Record<string, { label: string; email: string }>>({})
    const [newLabel, setNewLabel] = useState('')
    const [newEmail, setNewEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [busyId, setBusyId] = useState('')
    const [panelVisible, setPanelVisible] = useState(true)
    const [error, setError] = useState('')
    const [info, setInfo] = useState('')

    const hydrate = (next: FlowAccountsPayload) => {
        setPayload(next)
        setDrafts(() => {
            const mapped: Record<string, { label: string; email: string }> = {}
            next.accounts.forEach((item) => {
                mapped[item.id] = { label: item.label, email: item.email }
            })
            return mapped
        })
    }

    const loadAccounts = async () => {
        if (!window.electron?.flowAccountsList) return
        setLoading(true)
        setError('')
        try {
            const next = await window.electron.flowAccountsList()
            hydrate(next)
        } catch (e: any) {
            setError(e?.message ?? 'Không tải được danh sách tài khoản Flow')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (!hasBridge) return
        void loadAccounts()
    }, [hasBridge])

    useEffect(() => {
        window.electron?.getFlowPanelState?.()
            .then((state) => setPanelVisible(Boolean(state?.visible)))
            .catch(() => { })
        return window.electron?.onFlowPanelStateChanged?.((state) => {
            setPanelVisible(Boolean(state?.visible))
        })
    }, [])

    const runAction = async (id: string, action: () => Promise<FlowAccountsPayload>, successMessage: string) => {
        setBusyId(id)
        setError('')
        setInfo('')
        try {
            const next = await action()
            hydrate(next)
            setInfo(successMessage)
        } catch (e: any) {
            setError(e?.message ?? 'Thao tác thất bại')
        } finally {
            setBusyId('')
        }
    }

    const createAccount = async () => {
        if (!window.electron?.flowAccountsCreate) return
        const label = newLabel.trim()
        if (!label) {
            setError('Nhập tên tài khoản trước khi thêm.')
            return
        }
        setBusyId('__create__')
        setError('')
        setInfo('')
        try {
            const next = await window.electron.flowAccountsCreate({
                label,
                email: newEmail.trim(),
                setActive: true,
            })
            hydrate(next)
            setNewLabel('')
            setNewEmail('')
            setInfo('Đã thêm tài khoản và chuyển sang profile mới.')
        } catch (e: any) {
            setError(e?.message ?? 'Không tạo được tài khoản Flow')
        } finally {
            setBusyId('')
        }
    }

    const saveAccount = async (account: FlowAccount) => {
        if (!window.electron?.flowAccountsUpdate) return
        const draft = drafts[account.id] ?? { label: account.label, email: account.email }
        await runAction(
            account.id,
            () => window.electron!.flowAccountsUpdate({
                id: account.id,
                label: draft.label.trim() || account.label,
                email: draft.email.trim(),
            }),
            'Đã cập nhật thông tin tài khoản.',
        )
    }

    const openFlow = async (accountId: string) => {
        try {
            await window.electron?.openFlowTab?.({ focus: true, reveal: true, accountId })
            setInfo('Đã mở Google Flow theo tài khoản đã chọn.')
        } catch (e: any) {
            setError(e?.message ?? 'Không mở được Google Flow')
        }
    }

    if (!hasBridge) {
        return (
            <Card>
                <CardContent className="p-4">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        Tính năng quản lý tài khoản Flow chỉ hỗ trợ trong bản Electron app.
                    </p>
                </CardContent>
            </Card>
        )
    }

    return (
        <div className="flex flex-col gap-4 max-w-3xl">
            <Card>
                <CardContent className="p-4 flex flex-col gap-3">
                    <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Hồ Sơ Tài Khoản Google Flow</div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Mỗi tài khoản dùng một session riêng (cookie/cache riêng). App không lưu mật khẩu Google; chỉ lưu profile để chuyển nhanh.
                    </p>
                    {error && <div className="text-xs p-2 rounded bg-red-50 text-red-600">{error}</div>}
                    {info && <div className="text-xs p-2 rounded bg-green-50 text-green-700">{info}</div>}
                    <div className="grid grid-cols-1 md:grid-cols-[1fr,1fr,auto] gap-2">
                        <Input
                            value={newLabel}
                            onChange={(e) => setNewLabel(e.target.value)}
                            placeholder="Tên tài khoản (ví dụ: Team A)"
                            className="text-xs"
                        />
                        <Input
                            value={newEmail}
                            onChange={(e) => setNewEmail(e.target.value)}
                            placeholder="Email Google (tuỳ chọn)"
                            className="text-xs"
                        />
                        <Button onClick={() => void createAccount()} disabled={busyId === '__create__'} className="gap-1.5">
                            <Plus size={12} /> {busyId === '__create__' ? 'Đang thêm...' : 'Thêm tài khoản'}
                        </Button>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" onClick={() => void loadAccounts()} disabled={loading}>
                            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Tải lại
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={async () => {
                                try {
                                    const next = await window.electron?.toggleFlowPanel?.()
                                    if (next) setPanelVisible(Boolean(next.visible))
                                } catch {
                                    // no-op
                                }
                            }}
                        >
                            {panelVisible ? 'Ẩn Extension Panel' : 'Hiện Extension Panel'}
                        </Button>
                        <Badge variant="secondary">{payload?.accounts.length ?? 0} profiles</Badge>
                        <Badge variant={panelVisible ? 'success' : 'outline'}>
                            {panelVisible ? 'Panel đang hiển thị' : 'Panel đang ẩn'}
                        </Badge>
                    </div>
                </CardContent>
            </Card>

            <div className="flex flex-col gap-2">
                {(payload?.accounts ?? []).map((account) => {
                    const isActive = payload?.activeAccountId === account.id
                    const draft = drafts[account.id] ?? { label: account.label, email: account.email }
                    return (
                        <Card key={account.id} className={isActive ? 'border-[hsl(var(--primary))]' : ''}>
                            <CardContent className="p-3 flex flex-col gap-2">
                                <div className="flex items-center gap-2">
                                    <Badge variant={isActive ? 'success' : 'outline'}>
                                        {isActive ? 'Đang dùng' : 'Chưa dùng'}
                                    </Badge>
                                    <span className="text-xs text-[hsl(var(--muted-foreground))] font-mono">{account.id}</span>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                    <Input
                                        value={draft.label}
                                        onChange={(e) => setDrafts((prev) => ({ ...prev, [account.id]: { ...draft, label: e.target.value } }))}
                                        className="text-xs"
                                        placeholder="Tên tài khoản"
                                    />
                                    <Input
                                        value={draft.email}
                                        onChange={(e) => setDrafts((prev) => ({ ...prev, [account.id]: { ...draft, email: e.target.value } }))}
                                        className="text-xs"
                                        placeholder="Email (tuỳ chọn)"
                                    />
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <Button
                                        size="sm"
                                        variant={isActive ? 'secondary' : 'default'}
                                        disabled={busyId === account.id}
                                        onClick={() => void runAction(
                                            account.id,
                                            () => window.electron!.flowAccountsSetActive({ id: account.id, openFlow: true, focus: true }),
                                            'Đã chuyển tài khoản Flow đang hoạt động.',
                                        )}
                                    >
                                        {isActive ? 'Đang hoạt động' : 'Dùng tài khoản này'}
                                    </Button>
                                    {!isActive && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            disabled={busyId === account.id}
                                            onClick={() => void runAction(
                                                account.id,
                                                () => window.electron!.flowAccountsSetActive({ id: account.id, openFlow: false, focus: false }),
                                                'Đã đặt tài khoản mặc định cho toàn ứng dụng.',
                                            )}
                                        >
                                            Đặt mặc định
                                        </Button>
                                    )}
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={busyId === account.id}
                                        onClick={() => void saveAccount(account)}
                                        className="gap-1.5"
                                    >
                                        <Save size={11} /> Lưu thông tin
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={busyId === account.id}
                                        onClick={() => void openFlow(account.id)}
                                    >
                                        Mở Flow
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={busyId === account.id}
                                        onClick={() => void runAction(
                                            account.id,
                                            () => window.electron!.flowAccountsLogout({ id: account.id, reopenFlow: true, focus: true }),
                                            'Đã đăng xuất profile. Flow sẽ mở màn hình đăng nhập lại.',
                                        )}
                                    >
                                        Đăng xuất
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        disabled={busyId === account.id || (payload?.accounts.length ?? 0) <= 1}
                                        onClick={() => {
                                            if (!confirm(`Xóa profile '${draft.label || account.id}'?`)) return
                                            void runAction(
                                                account.id,
                                                () => window.electron!.flowAccountsDelete(account.id),
                                                'Đã xóa profile tài khoản.',
                                            )
                                        }}
                                    >
                                        <Trash2 size={11} /> Xóa
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    )
                })}
            </div>
        </div>
    )
}

// ─── License Panel ───────────────────────────────────────────
function LicensePanel() {
    const hasLicenseBridge = Boolean(
        window.electron
        && 'getMachineId' in window.electron
        && 'getLicenseStatus' in window.electron
    )

    const [machineId, setMachineId] = useState('')
    const [license, setLicense] = useState<LicenseCheckResult | null>(null)
    const [checking, setChecking] = useState(false)
    const [feedback, setFeedback] = useState('')

    const runLicenseCheck = async (force: boolean) => {
        if (!window.electron?.getLicenseStatus) return
        setChecking(true)
        try {
            const data = await window.electron.getLicenseStatus(force)
            setLicense(data)
            setFeedback(data.message || '')
        } catch (error) {
            setFeedback(error instanceof Error ? error.message : 'Không kiểm tra được license.')
        } finally {
            setChecking(false)
        }
    }

    const copyMachineId = async () => {
        if (!machineId) return
        try {
            await navigator.clipboard.writeText(machineId)
            setFeedback('Đã copy Machine ID.')
        } catch {
            setFeedback(`Machine ID: ${machineId}`)
        }
    }

    useEffect(() => {
        if (!hasLicenseBridge) return
        let cancelled = false

        const init = async () => {
            try {
                const resolvedMachineId = await window.electron!.getMachineId()
                if (cancelled) return
                setMachineId(resolvedMachineId)
                await runLicenseCheck(true)
            } catch (error) {
                if (!cancelled) {
                    setFeedback(error instanceof Error ? error.message : 'Không tải được dữ liệu license.')
                }
            }
        }

        void init()

        return () => {
            cancelled = true
        }
    }, [hasLicenseBridge])

    if (!hasLicenseBridge) {
        return (
            <Card>
                <CardContent className="p-4">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        License bridge chỉ khả dụng trong bản Electron app (không áp dụng khi chạy web preview).
                    </p>
                </CardContent>
            </Card>
        )
    }

    const isRevoked = license?.status === 'REVOKED'
    const isExpired = license?.status === 'EXPIRED'

    return (
        <div className="flex flex-col gap-4">
            <Card>
                <CardContent className="p-4 flex flex-col gap-3">
                    <div className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">License Thiết Bị</div>
                    <div className="grid gap-3">
                        <Field label="Machine ID">
                            <div className="flex gap-2">
                                <Input value={machineId} readOnly className="text-xs font-mono" />
                                <Button variant="secondary" onClick={copyMachineId} className="gap-1.5">
                                    <Copy size={12} /> Copy
                                </Button>
                            </div>
                        </Field>
                    </div>

                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] p-3 text-xs space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="text-[hsl(var(--muted-foreground))]">Trạng thái:</span>
                            <Badge variant={license ? licenseStatusVariant(license.status) : 'secondary'}>
                                {license ? LICENSE_STATUS_LABEL[license.status] : 'Chưa kiểm tra'}
                            </Badge>
                            {license?.planLabel && <Badge variant="outline">Gói: {license.planLabel}</Badge>}
                            {license?.source === 'cache' && <Badge variant="outline">Bản lưu ngoại tuyến</Badge>}
                        </div>
                        <div className="text-[hsl(var(--muted-foreground))]">
                            {license?.message || 'Bấm kiểm tra lại sau khi admin active máy trong CMS.'}
                        </div>
                        <div className="text-[hsl(var(--muted-foreground))]">
                            Kích hoạt: {formatDateTime(license?.activatedAt ?? null)} · Hết hạn: {formatDateTime(license?.expiresAt ?? null)}
                        </div>
                        <div className="text-[hsl(var(--muted-foreground))]">
                            Lần kiểm tra gần nhất: {formatDateTime(license?.checkedAt ?? null)}
                        </div>
                    </div>

                    {isRevoked && (
                        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 space-y-1.5">
                            <div className="font-semibold">Thiết bị đang ở trạng thái REVOKED</div>
                            <div>Lý do: {license?.revokedReason || 'Không có lý do cụ thể từ quản trị viên.'}</div>
                            <div>Machine ID: <code className="font-mono">{machineId}</code></div>
                        </div>
                    )}

                    {isExpired && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
                            License đã hết hạn. Vui lòng gia hạn lại trong CMS rồi bấm “Kiểm tra lại license”.
                        </div>
                    )}

                    <div className="flex flex-wrap items-center gap-2">
                        <Button onClick={() => void runLicenseCheck(true)} disabled={checking} className="gap-1.5">
                            <RefreshCw size={12} className={checking ? 'animate-spin' : ''} />
                            {checking ? 'Đang kiểm tra...' : 'Kiểm tra lại license'}
                        </Button>
                    </div>

                    {feedback && (
                        <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-xs text-[hsl(var(--muted-foreground))]">
                            {feedback}
                        </div>
                    )}
                </CardContent>
            </Card>

        </div>
    )
}

// ─── Main Settings Page ───────────────────────────────────────
export default function SettingsPage() {
    const [materials, setMaterials] = useState<string[]>(FALLBACK_MATERIALS)
    const settingsTabTriggerClass = 'text-sm font-medium'

    const loadMaterialIds = async () => {
        try {
            const list = await fetchAPI<MaterialItem[]>('/api/materials')
            const ids = list.map(m => m.id)
            if (ids.length > 0) setMaterials(ids)
        } catch { /* keep fallback */ }
    }

    useEffect(() => { loadMaterialIds() }, [])

    const activeProviders = PROVIDERS.map(p => p.id)

    return (
        <div className="flex flex-col gap-5 max-w-4xl">
            <div>
                <h2 className="text-sm font-bold mb-0.5">Cài đặt</h2>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Quản lý nhà cung cấp AI, API key, model, chất liệu và cấu hình mặc định.</p>
            </div>

            <Tabs defaultValue="gemini">
                <TabsList className="mb-4">
                    {PROVIDERS.map(p => (
                        <TabsTrigger key={p.id} value={p.id} className={settingsTabTriggerClass}>
                            {p.label}
                        </TabsTrigger>
                    ))}
                    <TabsTrigger value="general" className={settingsTabTriggerClass}>
                        Chung
                    </TabsTrigger>
                    <TabsTrigger value="flow" className={settingsTabTriggerClass}>
                        Flow
                    </TabsTrigger>
                    <TabsTrigger value="models" className={settingsTabTriggerClass}>
                        Model
                    </TabsTrigger>
                    <TabsTrigger value="materials" className={settingsTabTriggerClass}>
                        Chất liệu
                    </TabsTrigger>
                    <TabsTrigger value="tts" className={settingsTabTriggerClass}>
                        TTS
                    </TabsTrigger>
                    <TabsTrigger value="license" className={settingsTabTriggerClass}>
                        Giấy phép
                    </TabsTrigger>
                </TabsList>

                {activeProviders.map(pid => {
                    const p = PROVIDERS.find(x => x.id === pid)!
                    return (
                        <TabsContent key={pid} value={pid}>
                            <ProviderKeysPanel provider={p.id} color={p.color} docUrl={p.docUrl} placeholder={p.placeholder} />
                        </TabsContent>
                    )
                })}
                <TabsContent value="general"><GeneralPanel materials={materials} /></TabsContent>
                <TabsContent value="flow"><FlowAccountsPanel /></TabsContent>
                <TabsContent value="models"><ModelsPanel /></TabsContent>
                <TabsContent value="materials"><MaterialsPanel onChanged={loadMaterialIds} /></TabsContent>
                <TabsContent value="tts"><TTSPanel /></TabsContent>
                <TabsContent value="license"><LicensePanel /></TabsContent>
            </Tabs>
        </div>
    )
}
