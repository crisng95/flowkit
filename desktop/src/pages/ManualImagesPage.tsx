import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Download, ImagePlus, Play, RefreshCw, Trash2, Wand2 } from 'lucide-react'
import { fetchAPI } from '../api/client'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Textarea } from '../components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'

interface MaterialOption {
    id: string
    name: string
}

interface ManualContextResponse {
    project_id: string
    user_paygate_tier: string
}

interface ManualImageResultItem {
    index: number
    status: 'COMPLETED' | 'FAILED'
    error: string | null
    full_prompt: string
    aspect_ratio: string
    media_id: string | null
    url: string | null
}

interface ManualImageBatchResponse {
    project_id: string
    user_paygate_tier: string
    items: ManualImageResultItem[]
}

interface ModelsPayload {
    image_models?: Record<string, string>
}

interface ModelOption {
    key: string
    value: string
    label: string
}

type RowStatus = 'IDLE' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

interface ImageRow {
    id: string
    prompt: string
    style: string
    aspectRatio: string
    status: RowStatus
    mediaId: string | null
    url: string | null
    error: string | null
}

const MATERIAL_NONE = '__none__'

const IMAGE_ASPECT_OPTIONS = [
    { value: 'IMAGE_ASPECT_RATIO_PORTRAIT', label: '9:16 — Dọc' },
    { value: 'IMAGE_ASPECT_RATIO_LANDSCAPE', label: '16:9 — Ngang' },
]

function buildImageModelLabel(alias: string, modelKey: string) {
    const key = modelKey.toLowerCase()
    if (key.includes('gem') || key.includes('imagen') || key.includes('pix')) {
        return `Google Imagen • ${alias} (${modelKey})`
    }
    return `${alias} (${modelKey})`
}

function newId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID()
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function createRow(prompt = '', aspectRatio = IMAGE_ASPECT_OPTIONS[0].value): ImageRow {
    return {
        id: newId(),
        prompt,
        style: '',
        aspectRatio,
        status: 'IDLE',
        mediaId: null,
        url: null,
        error: null,
    }
}

function aspectCss(value: string) {
    if (value.includes('LANDSCAPE') || value.includes('16:9')) return '16 / 9'
    if (value.includes('SQUARE') || value.includes('1:1')) return '1 / 1'
    if (value.includes('4:3')) return '4 / 3'
    return '9 / 16'
}

function safeFileName(name: string) {
    return name.replace(/[^\w.-]+/g, '_')
}

async function downloadFromUrl(url: string, fileName: string) {
    try {
        const resp = await fetch(url)
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const blob = await resp.blob()
        const objectUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objectUrl
        a.download = fileName
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(objectUrl)
        return
    } catch {
        // Fallback: still provide a direct download/open action.
        const a = document.createElement('a')
        a.href = url
        a.download = fileName
        a.target = '_blank'
        a.rel = 'noreferrer'
        document.body.appendChild(a)
        a.click()
        a.remove()
    }
}

function explainContextError(e: unknown): string {
    const msg = e instanceof Error ? e.message : String(e ?? '')
    if (msg.includes('API 404') || msg.includes('Not Found')) {
        return 'Agent đang chạy không có endpoint context (khả năng tiến trình cũ). Hãy khởi động lại FlowKit để sidecar thay tiến trình đúng phiên bản.'
    }
    if (msg.includes('Extension not connected')) {
        return 'Google Flow extension chưa kết nối. Mở tab Google Flow trong app rồi bấm "Lấy context" lại.'
    }
    return msg || 'Không lấy được Flow context'
}

function StatusBadge({ status }: { status: RowStatus }) {
    if (status === 'COMPLETED') return <Badge variant="success">HOÀN TẤT</Badge>
    if (status === 'FAILED') return <Badge variant="destructive">THẤT BẠI</Badge>
    if (status === 'PROCESSING') return <Badge variant="warning">ĐANG XỬ LÝ</Badge>
    return <Badge variant="secondary">CHỜ</Badge>
}

export default function ManualImagesPage() {
    const [projectId, setProjectId] = useState('')
    const [tier, setTier] = useState('PAYGATE_TIER_ONE')
    const [materials, setMaterials] = useState<MaterialOption[]>([])
    const [imageModelOptions, setImageModelOptions] = useState<ModelOption[]>([])
    const [selectedImageModel, setSelectedImageModel] = useState('')
    const [material, setMaterial] = useState(MATERIAL_NONE)
    const [customStyle, setCustomStyle] = useState('')
    const [showAdvanced, setShowAdvanced] = useState(false)
    const [defaultAspectRatio, setDefaultAspectRatio] = useState(IMAGE_ASPECT_OPTIONS[0].value)
    const [inputMode, setInputMode] = useState<'single' | 'multiple'>('multiple')
    const [singlePrompt, setSinglePrompt] = useState('')
    const [singleStyle, setSingleStyle] = useState('')
    const [singleAspectRatio, setSingleAspectRatio] = useState(IMAGE_ASPECT_OPTIONS[0].value)
    const [bulkPrompts, setBulkPrompts] = useState('')
    const [rows, setRows] = useState<ImageRow[]>([])
    const [resolvingContext, setResolvingContext] = useState(false)
    const [runningAll, setRunningAll] = useState(false)
    const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({})
    const [error, setError] = useState('')

    const materialOptions = useMemo(
        () => [{ id: MATERIAL_NONE, name: 'Không áp style material' }, ...materials],
        [materials],
    )

    const refreshContext = async (createIfMissing: boolean): Promise<ManualContextResponse | null> => {
        setResolvingContext(true)
        try {
            const ctx = await fetchAPI<ManualContextResponse>('/api/flow/manual/context', {
                method: 'POST',
                body: JSON.stringify({
                    project_id: projectId.trim() || undefined,
                    create_if_missing: createIfMissing,
                }),
            })
            setProjectId(ctx.project_id ?? '')
            setTier(ctx.user_paygate_tier ?? 'PAYGATE_TIER_ONE')
            return ctx
        } catch (e: any) {
            if (createIfMissing) {
                setError(explainContextError(e))
            }
            return null
        } finally {
            setResolvingContext(false)
        }
    }

    useEffect(() => {
        fetchAPI<MaterialOption[]>('/api/materials')
            .then((mats) => {
                setMaterials(mats)
                if (mats.length > 0) {
                    setMaterial(mats[0].id)
                }
            })
            .catch(() => { })

        fetchAPI<ModelsPayload>('/api/models')
            .then((models) => {
                const imageModels = models.image_models ?? {}
                const options = Object.entries(imageModels).map(([alias, modelKey]) => ({
                    key: alias,
                    value: modelKey,
                    label: buildImageModelLabel(alias, modelKey),
                }))
                setImageModelOptions(options)
                if (options[0]) {
                    setSelectedImageModel(options[0].value)
                }
            })
            .catch(() => { })

        refreshContext(false).catch(() => { })
    }, [])

    const appendBulkRows = () => {
        const prompts = bulkPrompts
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean)
        if (prompts.length === 0) return
        setRows((prev) => [...prev, ...prompts.map((prompt) => createRow(prompt, defaultAspectRatio))])
        setBulkPrompts('')
    }

    const appendSingleRow = () => {
        const prompt = singlePrompt.trim()
        if (!prompt) return
        const row = createRow(prompt, singleAspectRatio || defaultAspectRatio)
        row.style = singleStyle.trim()
        setRows((prev) => [...prev, row])
        setSinglePrompt('')
        setSingleStyle('')
    }

    const updateRow = (id: string, patch: Partial<ImageRow>) => {
        setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)))
    }

    const toggleRowExpanded = (id: string) => {
        setExpandedRows((prev) => ({ ...prev, [id]: !prev[id] }))
    }

    const generateRow = async (id: string) => {
        const row = rows.find((item) => item.id === id)
        if (!row) return
        if (!row.prompt.trim()) {
            updateRow(id, { status: 'FAILED', error: 'Prompt không được để trống' })
            return
        }

        setError('')
        updateRow(id, { status: 'PROCESSING', error: null })
        const ctx = await refreshContext(true)
        if (!ctx) {
            updateRow(id, { status: 'FAILED', error: 'Không resolve được Flow project context' })
            return
        }

        try {
            const response = await fetchAPI<ManualImageBatchResponse>('/api/flow/manual/images', {
                method: 'POST',
                body: JSON.stringify({
                    project_id: ctx.project_id,
                    user_paygate_tier: tier,
                    material: material === MATERIAL_NONE ? null : material,
                    custom_style: customStyle.trim() || null,
                    image_model_key: selectedImageModel || null,
                    aspect_ratio: defaultAspectRatio,
                    items: [{
                        prompt: row.prompt,
                        style: row.style.trim() || null,
                        aspect_ratio: row.aspectRatio || defaultAspectRatio,
                    }],
                }),
            })

            const item = response.items?.[0]
            if (!item) {
                updateRow(id, { status: 'FAILED', error: 'Không nhận được kết quả từ API' })
                return
            }
            updateRow(id, {
                status: item.status === 'COMPLETED' ? 'COMPLETED' : 'FAILED',
                mediaId: item.media_id,
                url: item.url,
                error: item.error,
            })
        } catch (e: any) {
            updateRow(id, { status: 'FAILED', error: e.message ?? 'Generate ảnh thất bại' })
        }
    }

    const generateAll = async () => {
        const ids = rows.map((row) => row.id)
        if (ids.length === 0) return
        setRunningAll(true)
        for (const id of ids) {
            // tuần tự để tránh spam Flow endpoint/captcha
            // eslint-disable-next-line no-await-in-loop
            await generateRow(id)
        }
        setRunningAll(false)
    }

    const downloadRowImage = async (row: ImageRow, index: number) => {
        if (!row.url) return
        const mediaSlug = row.mediaId ? row.mediaId.slice(0, 8) : `row_${index + 1}`
        const fileName = safeFileName(`manual-image-${index + 1}-${mediaSlug}.png`)
        await downloadFromUrl(row.url, fileName)
    }

    const downloadAllImages = async () => {
        const downloadable = rows
            .map((row, index) => ({ row, index }))
            .filter((entry) => entry.row.status === 'COMPLETED' && !!entry.row.url)
        if (downloadable.length === 0) return
        for (const entry of downloadable) {
            // eslint-disable-next-line no-await-in-loop
            await downloadRowImage(entry.row, entry.index)
            // eslint-disable-next-line no-await-in-loop
            await new Promise((resolve) => setTimeout(resolve, 120))
        }
    }

    return (
        <div className="flex flex-col gap-3 h-full">
            <Card>
                <CardContent className="p-3 flex flex-col gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                        <ImagePlus size={13} className="text-[hsl(var(--muted-foreground))]" />
                        <span className="text-xs font-semibold">Tạo Ảnh</span>
                        <Badge variant="outline">Flow sẵn sàng</Badge>
                        <Badge variant="secondary">{selectedImageModel || 'Model tự động'}</Badge>
                        <Badge variant="secondary">{tier}</Badge>
                        <Badge variant="secondary">{rows.length} dòng</Badge>
                        <div className="flex-1" />
                        <Button variant="outline" size="sm" onClick={() => { refreshContext(true).catch(() => { }) }} disabled={resolvingContext}>
                            <RefreshCw size={11} className={resolvingContext ? 'animate-spin' : ''} />
                            {resolvingContext ? 'Đang đồng bộ...' : 'Lấy context'}
                        </Button>
                    </div>
                    <Input value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="Flow Project ID (để trống để app tự lấy)" className="text-xs" />
                    {error && <div className="text-xs rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-red-600">{error}</div>}
                </CardContent>
            </Card>

            <Card>
                <CardContent className="p-3 flex flex-col gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Phong Cách & Model</span>
                        <Badge variant="outline">Chất liệu: {material === MATERIAL_NONE ? 'không' : material}</Badge>
                        <Badge variant="secondary">Model: {selectedImageModel || 'tự động'}</Badge>
                        <Badge variant="secondary">{IMAGE_ASPECT_OPTIONS.find((item) => item.value === defaultAspectRatio)?.label ?? defaultAspectRatio}</Badge>
                        <Button variant="ghost" size="sm" onClick={() => setShowAdvanced((prev) => !prev)} className="ml-auto gap-1">
                            {showAdvanced ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                            {showAdvanced ? 'Ẩn' : 'Nâng cao'}
                        </Button>
                    </div>
                    {showAdvanced && (
                        <div className="grid gap-2 md:grid-cols-3 border border-[hsl(var(--border))] rounded-md p-2.5">
                            <div className="flex flex-col gap-1">
                                <Label>Chất liệu</Label>
                                <Select value={material} onValueChange={setMaterial}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{materialOptions.map((item) => <SelectItem key={item.id} value={item.id}>{item.name} ({item.id})</SelectItem>)}</SelectContent></Select>
                            </div>
                            <div className="flex flex-col gap-1">
                                <Label>Model ảnh</Label>
                                <Select value={selectedImageModel} onValueChange={setSelectedImageModel}><SelectTrigger><SelectValue placeholder="Chọn model..." /></SelectTrigger><SelectContent>{imageModelOptions.map((item) => <SelectItem key={`${item.key}:${item.value}`} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
                            </div>
                            <div className="flex flex-col gap-1">
                                <Label>Aspect mặc định</Label>
                                <Select value={defaultAspectRatio} onValueChange={setDefaultAspectRatio}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{IMAGE_ASPECT_OPTIONS.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
                            </div>
                            <div className="flex flex-col gap-1 md:col-span-3">
                                <Label>Phong cách tùy chỉnh</Label>
                                <Textarea value={customStyle} onChange={(e) => setCustomStyle(e.target.value)} rows={2} placeholder="ví dụ: cinematic lighting, shallow depth of field..." />
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                        <div>
                            <CardTitle className="text-sm">Nhập Prompt</CardTitle>
                            <CardDescription className="text-xs mt-0.5">Tách riêng chế độ Đơn và Hàng loạt để nhập nhanh.</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button size="sm" onClick={generateAll} disabled={runningAll || rows.length === 0}>
                                <Play size={11} /> {runningAll ? 'Đang chạy...' : 'Tạo tất cả'}
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => { void downloadAllImages() }} disabled={rows.every((row) => !row.url)}>
                                <Download size={11} /> Tải tất cả
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="pt-0 flex flex-col gap-3">
                    <Tabs value={inputMode} onValueChange={(v) => setInputMode(v as 'single' | 'multiple')}>
                        <TabsList>
                            <TabsTrigger value="single" className="text-sm font-medium">Đơn (Single)</TabsTrigger>
                            <TabsTrigger value="multiple" className="text-sm font-medium">Hàng loạt (Multiple)</TabsTrigger>
                        </TabsList>

                        <TabsContent value="single">
                            <div className="grid gap-2 md:grid-cols-3">
                                <div className="flex flex-col gap-1.5 md:col-span-2">
                                    <Label>Nội dung prompt</Label>
                                    <Textarea
                                        rows={4}
                                        value={singlePrompt}
                                        onChange={(e) => setSinglePrompt(e.target.value)}
                                        placeholder="Nhập một prompt duy nhất..."
                                    />
                                </div>
                                <div className="flex flex-col gap-3">
                                    <div className="flex flex-col gap-1.5">
                                        <Label>Aspect</Label>
                                        <Select value={singleAspectRatio} onValueChange={setSingleAspectRatio}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {IMAGE_ASPECT_OPTIONS.map((item) => (
                                                    <SelectItem key={item.value} value={item.value}>
                                                        {item.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="flex flex-col gap-1.5">
                                        <Label>Ghi đè phong cách</Label>
                                        <Input
                                            value={singleStyle}
                                            onChange={(e) => setSingleStyle(e.target.value)}
                                            placeholder="tùy chọn"
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                <Button onClick={appendSingleRow} disabled={!singlePrompt.trim()}>
                                    + Thêm vào danh sách
                                </Button>
                                <Button
                                    variant="secondary"
                                    onClick={() => { setSinglePrompt(''); setSingleStyle('') }}
                                    disabled={!singlePrompt && !singleStyle}
                                >
                                    Xóa
                                </Button>
                            </div>
                        </TabsContent>

                        <TabsContent value="multiple">
                            <Textarea
                                rows={5}
                                value={bulkPrompts}
                                onChange={(e) => setBulkPrompts(e.target.value)}
                                placeholder={'Prompt video 1...\nPrompt video 2...\nPrompt video 3...'}
                            />
                            <div className="mt-3 flex flex-wrap gap-2">
                                <Button variant="outline" onClick={appendBulkRows}>
                                    + Thêm vào danh sách
                                </Button>
                                <Button variant="secondary" onClick={() => setRows((prev) => [...prev, createRow('', defaultAspectRatio)])}>
                                    + Thêm 1 dòng trống
                                </Button>
                            </div>
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>

            {/* Row list */}
            <div className="flex flex-col gap-2 overflow-y-auto">
                {rows.length === 0 && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Chưa có mục nào. Thêm prompt ở tab Đơn hoặc Hàng loạt.</p>
                )}
                {rows.map((row, idx) => (
                    <Card key={row.id}>
                        <CardContent className="p-3 flex flex-col gap-2">
                            {/* Row header */}
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))] w-5">#{idx + 1}</span>
                                <StatusBadge status={row.status} />
                                <span className="text-xs text-[hsl(var(--muted-foreground))] truncate flex-1">{row.prompt.trim() || 'Chưa có prompt'}</span>
                                <Button variant="ghost" size="sm" onClick={() => toggleRowExpanded(row.id)}>
                                    {expandedRows[row.id] ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => generateRow(row.id)} disabled={row.status === 'PROCESSING'}>
                                    <Wand2 size={11} /> Tạo
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => setRows((prev) => prev.filter((item) => item.id !== row.id))}>
                                    <Trash2 size={11} className="text-[hsl(var(--destructive))]" />
                                </Button>
                            </div>

                            {/* Expanded editor */}
                            {expandedRows[row.id] && (
                                <div className="grid gap-2.5 md:grid-cols-3 border border-[hsl(var(--border))] rounded-md p-2.5">
                                    <div className="flex flex-col gap-1 md:col-span-2">
                                        <Label>Nội dung prompt</Label>
                                        <Textarea value={row.prompt} onChange={(e) => updateRow(row.id, { prompt: e.target.value, status: 'IDLE' })} rows={3} />
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <div className="flex flex-col gap-1">
                                            <Label>Aspect</Label>
                                            <Select value={row.aspectRatio} onValueChange={(value) => updateRow(row.id, { aspectRatio: value, status: 'IDLE' })}>
                                                <SelectTrigger><SelectValue /></SelectTrigger>
                                                <SelectContent>{IMAGE_ASPECT_OPTIONS.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent>
                                            </Select>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <Label>Ghi đè phong cách</Label>
                                            <Input value={row.style} onChange={(e) => updateRow(row.id, { style: e.target.value, status: 'IDLE' })} placeholder="tùy chọn" />
                                        </div>
                                    </div>
                                </div>
                            )}

                            {row.error && <div className="text-xs rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-red-600">{row.error}</div>}

                            {row.mediaId && <p className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">media_id: {row.mediaId}</p>}

                            {row.url && (
                                <div className="flex flex-col gap-2">
                                    <div className="flex gap-2">
                                        <Button variant="outline" size="sm" asChild>
                                            <a href={row.url} target="_blank" rel="noreferrer">Mở ảnh gốc</a>
                                        </Button>
                                        <Button variant="ghost" size="sm" onClick={() => { void downloadRowImage(row, idx) }}>
                                            <Download size={11} /> Tải ảnh
                                        </Button>
                                    </div>
                                    <div className="rounded-md border border-[hsl(var(--border))] overflow-hidden bg-[hsl(var(--muted))]" style={{ aspectRatio: aspectCss(row.aspectRatio), maxHeight: '320px' }}>
                                        <img src={row.url} alt={`manual-image-${idx + 1}`} className="h-full w-full object-contain" />
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
