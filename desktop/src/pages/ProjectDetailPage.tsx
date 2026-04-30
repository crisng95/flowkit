import { useState, useEffect, useRef, useCallback } from 'react'
import { Plus, Trash2, RefreshCw, Film, Image, Save, ChevronDown, ChevronUp, Upload, Play } from 'lucide-react'
import { fetchAPI, patchAPI } from '../api/client'
import type { Project, Character, Video, ChainType, StatusType } from '../types'
import EditableText from '../components/projects/EditableText'
import AddCharacterModal from '../components/projects/AddCharacterModal'
import CreateVideoModal from '../components/projects/CreateVideoModal'
import VideoDetailPage from './VideoDetailPage'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs'
import { Label } from '../components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Separator } from '../components/ui/separator'
import { Dialog, DialogContent } from '../components/ui/dialog'
import { normalizeOrientation, orientationAspect, orientationPrefix, resolveMediaUrl, sceneStatus, sceneUrl } from '../lib/orientation'
import { cn } from '../lib/utils'

function formatDate(iso: string) { return new Date(iso).toLocaleString('vi-VN') }

function orientationToAspect(orientation?: string | null): string {
  if (!orientation) return 'N/A'
  const upper = orientation.toUpperCase()
  if (upper.includes('4_3') || upper.includes('4:3')) return '4:3'
  if (upper.includes('1_1') || upper.includes('1:1') || upper.includes('SQUARE')) return '1:1'
  return orientationAspect(orientation)
}

function parseSignedUrlExpiresAt(url: string | null | undefined): number | null {
  if (!url) return null
  if (!/^https?:\/\//i.test(url)) return null
  try {
    const parsed = new URL(url)
    const raw = parsed.searchParams.get('Expires') ?? parsed.searchParams.get('expires')
    if (raw) {
      const ts = Number.parseInt(raw, 10)
      if (Number.isFinite(ts) && ts > 0) return ts * 1000
    }

    const xGoogExpires = parsed.searchParams.get('X-Goog-Expires') ?? parsed.searchParams.get('x-goog-expires')
    const xGoogDate = parsed.searchParams.get('X-Goog-Date') ?? parsed.searchParams.get('x-goog-date')
    if (!xGoogExpires || !xGoogDate) return null

    const secs = Number.parseInt(xGoogExpires, 10)
    if (!Number.isFinite(secs) || secs <= 0) return null
    const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(xGoogDate)
    if (!m) return null
    const baseMs = Date.UTC(
      Number(m[1]),
      Number(m[2]) - 1,
      Number(m[3]),
      Number(m[4]),
      Number(m[5]),
      Number(m[6]),
    )
    if (!Number.isFinite(baseMs) || baseMs <= 0) return null
    return baseMs + secs * 1000
  } catch {
    return null
  }
}

function isExpiredSignedUrl(url: string | null | undefined, nowMs = Date.now()): boolean {
  const expiresAt = parseSignedUrlExpiresAt(url)
  if (!expiresAt) return false
  return expiresAt <= nowMs
}

function isFlowRedirectMediaUrl(url: string | null | undefined): boolean {
  if (!url) return false
  return /media\.getMediaUrlRedirect/i.test(url)
}

function needsMediaUrlRefresh(url: string | null | undefined, nowMs = Date.now()): boolean {
  if (!url) return true
  if (!/^https?:\/\//i.test(url)) return false
  if (isFlowRedirectMediaUrl(url)) return true
  return isExpiredSignedUrl(url, nowMs)
}

function pickDirectMediaUrl(payload: any): string | null {
  const candidates = [
    payload?.url,
    payload?.servingUri,
    payload?.fifeUrl,
    payload?.imageUri,
    payload?.videoUri,
    payload?.data?.url,
    payload?.data?.servingUri,
    payload?.data?.fifeUrl,
    payload?.data?.imageUri,
    payload?.data?.videoUri,
  ]
  for (const value of candidates) {
    if (typeof value !== 'string') continue
    if (!/^https?:\/\//i.test(value)) continue
    if (isFlowRedirectMediaUrl(value)) continue
    return value
  }
  return null
}

function StatusDot({ status }: { status: StatusType }) {
  const colors: Record<StatusType, string> = {
    COMPLETED: '#16a34a', PROCESSING: '#d97706', PENDING: 'hsl(var(--muted-foreground))', FAILED: '#dc2626',
  }
  return <span className="inline-block w-2 h-2 rounded-full flex-shrink-0" style={{ background: colors[status] ?? 'hsl(var(--muted-foreground))' }} title={status} />
}

function ChainBadge({ type }: { type: ChainType }) {
  const variantMap: Record<ChainType, 'default' | 'secondary' | 'warning'> = {
    ROOT: 'default', CONTINUATION: 'secondary', INSERT: 'warning',
  }
  return <Badge variant={variantMap[type] ?? 'secondary'}>{type}</Badge>
}

function SectionCard({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4', className)}>
      {children}
    </div>
  )
}

// ─── Overview Tab ─────────────────────────────────────────────
function OverviewTab({ project, sceneCount, aspectLabels, onPatch, onDelete }: {
  project: Project
  sceneCount: number
  aspectLabels: string[]
  onPatch: (field: string, value: string) => void
  onDelete: () => void
}) {
  async function patchProject(field: string, value: string) {
    onPatch(field, value)
    await patchAPI(`/api/projects/${project.id}`, { [field]: value })
  }

  const archive = async () => {
    const next = project.status === 'ARCHIVED' ? 'ACTIVE' : 'ARCHIVED'
    onPatch('status', next)
    await patchAPI(`/api/projects/${project.id}`, { status: next })
  }

  const deleteProject = async () => {
    if (!confirm(`Xóa vĩnh viễn "${project.name}"? Hành động này không thể hoàn tác.`)) return
    await fetchAPI(`/api/projects/${project.id}`, { method: 'DELETE' })
    onDelete()
  }

  return (
    <div className="flex flex-col gap-3 max-w-2xl">
      <SectionCard>
        <div className="flex flex-col gap-3">
          <div>
            <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Tên</Label>
            <EditableText value={project.name} onSave={v => patchProject('name', v)} className="font-semibold text-sm mt-0.5" />
          </div>
          <Separator />
          <div>
            <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Mô tả</Label>
            <EditableText value={project.description ?? ''} onSave={v => patchProject('description', v)} multiline className="text-xs mt-0.5" placeholder="Thêm mô tả..." />
          </div>
          <Separator />
          <div>
            <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Bối cảnh / mạch truyện xuyên suốt</Label>
            <EditableText
              value={project.story ?? ''}
              onSave={v => patchProject('story', v)}
              multiline
              className="text-xs mt-0.5"
              placeholder="Mạch truyện global cho toàn bộ video trong project..."
            />
          </div>
          <Separator />
        </div>
      </SectionCard>

      <SectionCard>
        <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Thông tin</Label>
        <div className="flex flex-wrap gap-1.5 mt-2">
          <Badge variant="secondary">{project.material}</Badge>
          {project.user_paygate_tier && (
            <Badge variant={project.user_paygate_tier.includes('TWO') ? 'warning' : 'default'}>
              {project.user_paygate_tier.includes('TWO') ? 'TIER 2' : 'TIER 1'}
            </Badge>
          )}
          <Badge variant="success">{sceneCount} phân cảnh</Badge>
          <Badge variant="outline">{aspectLabels.join(', ') || 'N/A'}</Badge>
          <Badge variant="secondary">{project.status}</Badge>
        </div>
        <div className="flex flex-col gap-0.5 mt-3 text-xs text-[hsl(var(--muted-foreground))]">
          <span>Tỉ lệ hỗ trợ: 16:9, 9:16, 4:3, 1:1</span>
          <span>Tạo lúc: {formatDate(project.created_at)}</span>
          <span>Cập nhật: {formatDate(project.updated_at)}</span>
        </div>
      </SectionCard>

      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={archive}>
          {project.status === 'ARCHIVED' ? 'Khôi phục' : 'Lưu trữ'}
        </Button>
        <Button variant="destructive" size="sm" onClick={deleteProject}>
          <Trash2 size={11} /> Xóa dự án
        </Button>
      </div>
    </div>
  )
}

// ─── Characters Tab ───────────────────────────────────────────
function CharactersTab({ projectId, orientation, characters, onRefresh }: {
  projectId: string; orientation: string; characters: Character[]; onRefresh: () => void
}) {
  type CharReqStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  type CharReqState = { status: CharReqStatus; error?: string | null; retryCount?: number }

  const [showAdd, setShowAdd] = useState(false)
  const [uploadingCharacterId, setUploadingCharacterId] = useState<string | null>(null)
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({})
  const [previewImage, setPreviewImage] = useState<{ url: string; name: string } | null>(null)
  const [charReqState, setCharReqState] = useState<Record<string, CharReqState>>({})
  const [refBatch, setRefBatch] = useState<{
    pending: number
    processing: number
    completed: number
    failed: number
    total: number
    status_hint?: string | null
  } | null>(null)
  const previewResolving = useRef<Set<string>>(new Set())
  const previewRefreshFailedAt = useRef<Map<string, number>>(new Map())
  const autoRefreshTriggeredRef = useRef<Set<string>>(new Set())
  const PREVIEW_RETRY_DELAY_MS = 45_000
  const normalizedOrientation = normalizeOrientation(orientation)
  const busyCharacterIds = new Set(
    Object.entries(charReqState)
      .filter(([, s]) => s.status === 'PENDING' || s.status === 'PROCESSING')
      .map(([cid]) => cid),
  )
  const activeRefCount = (refBatch?.pending ?? 0) + (refBatch?.processing ?? 0)

  const ensureFlowTabReadyForMedia = useCallback(async () => {
    const hasFlowTab = async () => {
      try {
        const runtime = await fetchAPI<{
          runtime_connected?: boolean
          agent_connected?: boolean
          connected?: boolean
          state?: string
          flow_tab_id?: number | null
          flow_tab_url?: string | null
        }>('/api/flow/status')
        const connected = Boolean(
          runtime.runtime_connected
          ?? runtime.agent_connected
          ?? runtime.connected,
        )
        const hasTab = (
          (runtime.flow_tab_id !== null && runtime.flow_tab_id !== undefined)
          || !!runtime.flow_tab_url
        )
        const stateReady = String(runtime.state || '').toLowerCase() !== 'off'
        return connected && hasTab && stateReady
      } catch {
        return false
      }
    }
    if (await hasFlowTab()) return true
    await window.electron?.openFlowTab?.({ focus: false, reveal: false })
    await window.electron?.reconnectExtension?.()
    for (let i = 0; i < 8; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise(r => setTimeout(r, 650))
      // eslint-disable-next-line no-await-in-loop
      if (await hasFlowTab()) return true
    }
    return false
  }, [])

  const loadRefRequestState = useCallback(async () => {
    try {
      const [summary, allRequests] = await Promise.all([
        fetchAPI<{ pending: number; processing: number; completed: number; failed: number; total: number; status_hint?: string | null }>(
          `/api/requests/batch-status?project_id=${projectId}&type=GENERATE_CHARACTER_IMAGE`,
        ),
        fetchAPI<Array<{
          id: string
          character_id: string | null
          type: string
          status: CharReqStatus
          error_message: string | null
          retry_count: number
          updated_at?: string | null
          created_at?: string | null
        }>>(`/api/requests?project_id=${projectId}`),
      ])

      setRefBatch(summary)
      const byChar: Record<string, CharReqState> = {}
      const refs = allRequests
        .filter(r =>
          !!r.character_id
          && ['GENERATE_CHARACTER_IMAGE', 'REGENERATE_CHARACTER_IMAGE', 'EDIT_CHARACTER_IMAGE'].includes(r.type),
        )
        .sort((a, b) => {
          const ta = Date.parse((a.updated_at || a.created_at || '').toString()) || 0
          const tb = Date.parse((b.updated_at || b.created_at || '').toString()) || 0
          return tb - ta
        })
      for (const row of refs) {
        const cid = row.character_id as string
        if (byChar[cid]) continue
        byChar[cid] = {
          status: row.status,
          error: row.error_message,
          retryCount: row.retry_count,
        }
      }
      setCharReqState(byChar)

      // Auto-refresh character list when ref generation has just completed,
      // so thumbnail/media_id appears immediately without manual reload.
      const waitingIds = characters
        .filter(ch => !ch.media_id)
        .map(ch => ch.id)
      const completedNow = waitingIds.filter(cid => byChar[cid]?.status === 'COMPLETED')
      let shouldRefresh = false
      for (const cid of completedNow) {
        if (autoRefreshTriggeredRef.current.has(cid)) continue
        autoRefreshTriggeredRef.current.add(cid)
        shouldRefresh = true
      }
      for (const ch of characters) {
        if (ch.media_id) autoRefreshTriggeredRef.current.delete(ch.id)
      }
      if (shouldRefresh) {
        onRefresh()
        // Safety re-check: some backends commit request status before media_id patch.
        setTimeout(() => { onRefresh() }, 900)
      }
    } catch {
      // Non-blocking; keep last known UI state.
    }
  }, [characters, onRefresh, projectId])

  const genRefs = async () => {
    const missing = characters.filter(c => !c.media_id && !busyCharacterIds.has(c.id))
    const requests = missing.map(c => ({
      type: 'GENERATE_CHARACTER_IMAGE', project_id: projectId, character_id: c.id, orientation: normalizedOrientation,
    }))
    if (!requests.length) { alert('Tất cả thực thể đã có ảnh ref. Dùng nút regen cho từng thực thể nếu muốn tạo lại.'); return }
    await fetchAPI('/api/requests/batch', { method: 'POST', body: JSON.stringify({ requests }) })
    void loadRefRequestState()
    alert(`Đã gửi ${requests.length} yêu cầu tạo ảnh tham chiếu cho thực thể còn thiếu.`)
  }

  const regenChar = async (cid: string) => {
    if (busyCharacterIds.has(cid)) return
    await fetchAPI('/api/requests/batch', {
      method: 'POST',
      body: JSON.stringify({ requests: [{ type: 'REGENERATE_CHARACTER_IMAGE', project_id: projectId, character_id: cid, orientation: normalizedOrientation }] }),
    })
    void loadRefRequestState()
  }

  const removeChar = async (cid: string) => {
    if (!confirm('Xóa thực thể này khỏi dự án?')) return
    await fetchAPI(`/api/projects/${projectId}/characters/${cid}`, { method: 'DELETE' })
    onRefresh()
  }

  const patchChar = async (cid: string, field: string, value: string) => {
    await patchAPI(`/api/characters/${cid}`, { [field]: value })
    onRefresh()
  }

  const uploadReference = async (ch: Character) => {
    const pickWithKind = window.electron?.pickFile
    const pickImageOnly = window.electron?.pickImageFile
    if (!pickWithKind && !pickImageOnly) { alert('Chỉ hỗ trợ trong ứng dụng desktop.'); return }

    const filePath = pickWithKind ? await pickWithKind('image') : await pickImageOnly?.()
    if (!filePath) return

    const fileName = filePath.split(/[\\\/]/).pop() || `${ch.name}.png`
    setUploadingCharacterId(ch.id)
    try {
      const uploaded = await fetchAPI<{ media_id?: string; url?: string | null }>('/api/flow/upload-image', {
        method: 'POST',
        body: JSON.stringify({ file_path: filePath, project_id: projectId, file_name: fileName }),
      })
      if (!uploaded.media_id) throw new Error('Upload thành công nhưng không có media_id')

      let referenceUrl = uploaded.url ?? null
      if (!referenceUrl) {
        try {
          await ensureFlowTabReadyForMedia()
          const refreshed = await fetchAPI<{ fifeUrl?: string; servingUri?: string; url?: string | null }>(
            `/api/flow/media/${uploaded.media_id}?project_id=${encodeURIComponent(projectId)}`,
          )
          referenceUrl = pickDirectMediaUrl(refreshed)
        } catch {
          // Keep null URL, media_id is enough to use as reference.
        }
      }

      const persistableReferenceUrl =
        typeof referenceUrl === 'string' && /\/api\/flow\/local-media\?path=/.test(referenceUrl)
          ? referenceUrl
          : null

      await patchAPI(`/api/characters/${ch.id}`, {
        media_id: uploaded.media_id,
        reference_image_url: persistableReferenceUrl,
      })
      if (referenceUrl) {
        setPreviewUrls(prev => ({ ...prev, [ch.id]: referenceUrl as string }))
      } else {
        setPreviewUrls(prev => {
          const next = { ...prev }
          delete next[ch.id]
          return next
        })
      }
      onRefresh()
      alert(`Đã cập nhật ảnh ref cho "${ch.name}" (${uploaded.media_id.slice(0, 8)}...)`)
    } catch (err) {
      alert(`Lỗi upload: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setUploadingCharacterId(null)
    }
  }

  const refreshCharacterPreview = useCallback(async (ch: Character) => {
    if (!ch.media_id || previewResolving.current.has(ch.id)) return null
    const failedAt = previewRefreshFailedAt.current.get(ch.id)
    if (failedAt && Date.now() - failedAt < PREVIEW_RETRY_DELAY_MS) return null
    if (!(await ensureFlowTabReadyForMedia())) return null
    previewResolving.current.add(ch.id)
    try {
      const refreshed = await fetchAPI<{ fifeUrl?: string; servingUri?: string; url?: string | null }>(
        `/api/flow/media/${ch.media_id}?project_id=${encodeURIComponent(projectId)}`,
      )
      const url = pickDirectMediaUrl(refreshed)
      if (url) {
        setPreviewUrls(prev => ({ ...prev, [ch.id]: url }))
        previewRefreshFailedAt.current.delete(ch.id)
        if (/\/api\/flow\/local-media\?path=/.test(url)) {
          // Persist only stable local URLs (avoid storing expiring signed URLs).
          void patchAPI(`/api/characters/${ch.id}`, { reference_image_url: url }).catch(() => { })
        }
      }
      return url
    } catch {
      previewRefreshFailedAt.current.set(ch.id, Date.now())
      return null
    } finally {
      previewResolving.current.delete(ch.id)
    }
  }, [ensureFlowTabReadyForMedia, projectId])

  useEffect(() => {
    void loadRefRequestState()
    const timer = setInterval(() => { void loadRefRequestState() }, activeRefCount > 0 ? 1500 : 3500)
    return () => clearInterval(timer)
  }, [loadRefRequestState, activeRefCount])

  useEffect(() => {
    previewRefreshFailedAt.current.clear()
  }, [projectId])

  useEffect(() => {
    if (!characters.length) return
    let cancelled = false
    const now = Date.now()
    const candidates = characters
      .filter((ch) => {
        if (!ch.media_id) return false
        const current = resolveMediaUrl(previewUrls[ch.id] || ch.reference_image_url)
        if (!current) return true
        return needsMediaUrlRefresh(current, now)
      })
      .slice(0, 6)
    if (!candidates.length) return

    const run = async () => {
      const queue = [...candidates]
      const workers = new Array(Math.min(2, queue.length)).fill(0).map(async () => {
        while (queue.length && !cancelled) {
          const next = queue.shift()
          if (!next) break
          // eslint-disable-next-line no-await-in-loop
          await refreshCharacterPreview(next)
          // eslint-disable-next-line no-await-in-loop
          await new Promise(r => setTimeout(r, 220))
        }
      })
      await Promise.all(workers)
    }
    void run()

    return () => { cancelled = true }
  }, [characters, previewUrls, refreshCharacterPreview])

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-[hsl(var(--muted-foreground))]">{characters.length} thực thể</span>
        {activeRefCount > 0 && (
          <Badge variant="warning" className="text-[10px]">
            Ref đang chạy: {(refBatch?.processing ?? 0)} xử lý • {(refBatch?.pending ?? 0)} chờ
          </Badge>
        )}
        {(refBatch?.failed ?? 0) > 0 && (
          <Badge variant="destructive" className="text-[10px]">
            Ref lỗi: {refBatch?.failed}
          </Badge>
        )}
        <div className="flex-1" />
        {characters.length > 0 && (
          <Button variant="outline" size="sm" onClick={genRefs} disabled={activeRefCount > 0}>
            <RefreshCw size={11} className={activeRefCount > 0 ? 'animate-spin' : ''} />
            {activeRefCount > 0 ? 'Đang tạo ref...' : 'Tạo ảnh TN'}
          </Button>
        )}
        <Button size="sm" onClick={() => setShowAdd(true)}>
          <Plus size={11} /> Thêm thực thể
        </Button>
      </div>

      {characters.length === 0 ? (
        <div className="flex flex-col gap-2 py-6">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Chưa có thực thể nào. Thêm nhân vật, địa điểm, sinh vật...</p>
          <div><Button size="sm" onClick={() => setShowAdd(true)}><Plus size={11} /> Thêm thực thể đầu tiên</Button></div>
        </div>
      ) : (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1040px] text-xs">
              <thead className="bg-[hsl(var(--muted)/0.35)] text-[hsl(var(--muted-foreground))]">
                <tr>
                  <th className="text-left font-semibold px-3 py-2 w-[150px]">Ảnh ref</th>
                  <th className="text-left font-semibold px-3 py-2 w-[180px]">Tên</th>
                  <th className="text-left font-semibold px-3 py-2 w-[120px]">Loại</th>
                  <th className="text-left font-semibold px-3 py-2">Mô tả (gọn)</th>
                  <th className="text-left font-semibold px-3 py-2 w-[200px]">Trạng thái</th>
                  <th className="text-left font-semibold px-3 py-2 w-[220px]">Tác vụ</th>
                </tr>
              </thead>
              <tbody>
                {characters.map(ch => {
                  const preview = resolveMediaUrl(previewUrls[ch.id] || ch.reference_image_url)
                  const req = charReqState[ch.id]
                  const busy = busyCharacterIds.has(ch.id)
                  return (
                    <tr key={ch.id} className="border-t border-[hsl(var(--border))] align-top">
                      <td className="px-3 py-2">
                        <div className="w-[128px] h-[84px] rounded border bg-[hsl(var(--muted)/0.45)] overflow-hidden flex items-center justify-center">
                          {preview ? (
                            <img
                              src={preview}
                              alt={ch.name}
                              className="max-w-full max-h-full object-contain cursor-zoom-in"
                              onClick={() => setPreviewImage({ url: preview, name: ch.name })}
                              onError={() => { void refreshCharacterPreview(ch) }}
                            />
                          ) : (
                            <div className="text-[10px] text-[hsl(var(--muted-foreground))]">{ch.entity_type}</div>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 font-semibold text-[hsl(var(--foreground))]">{ch.name}</td>
                      <td className="px-3 py-2">
                        <Badge variant="outline">{ch.entity_type}</Badge>
                      </td>
                      <td className="px-3 py-2">
                        <EditableText
                          value={ch.description ?? ''}
                          onSave={v => patchChar(ch.id, 'description', v)}
                          className="block max-w-[460px] truncate text-[hsl(var(--muted-foreground))]"
                          placeholder="Mô tả..."
                        />
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-1.5">
                            <span className={cn('inline-block w-2 h-2 rounded-full', ch.media_id ? 'bg-green-500' : 'bg-red-500')} />
                            <span className={ch.media_id ? 'text-green-600' : 'text-red-500'}>
                              {ch.media_id ? 'Sẵn sàng' : 'Thiếu'}
                            </span>
                          </div>
                          {req && (req.status === 'PENDING' || req.status === 'PROCESSING' || req.status === 'FAILED') && (
                            <div className={cn('text-[10px]', req.status === 'FAILED' ? 'text-red-600' : 'text-amber-600')}>
                              {req.status === 'PROCESSING' && 'Đang tạo ảnh ref...'}
                              {req.status === 'PENDING' && 'Đang xếp hàng tạo ảnh ref...'}
                              {req.status === 'FAILED' && `Ref lỗi: ${req.error || 'Lỗi không xác định'}`}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          <Button variant="outline" size="sm" onClick={() => uploadReference(ch)} disabled={uploadingCharacterId === ch.id}>
                            {uploadingCharacterId === ch.id ? <RefreshCw size={10} className="animate-spin" /> : <Upload size={10} />}
                            {uploadingCharacterId === ch.id ? 'Đang upload...' : 'Ref'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => regenChar(ch.id)}
                            disabled={busy}
                            title={busy ? 'Đang xử lý ảnh ref, vui lòng chờ...' : 'Tạo lại ảnh ref'}
                          >
                            <RefreshCw size={10} className={busy ? 'animate-spin' : ''} />
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => removeChar(ch.id)}>
                            <Trash2 size={10} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {previewImage && (
        <Dialog open onOpenChange={() => setPreviewImage(null)}>
          <DialogContent className="max-w-4xl p-0 overflow-hidden bg-black border-0">
            <div className="flex flex-col gap-2 p-3">
              <div className="text-xs text-white/80">{previewImage.name}</div>
              <div className="flex items-center justify-center min-h-[55vh] max-h-[86vh]">
                <img src={previewImage.url} alt={previewImage.name} className="max-w-full max-h-[82vh] object-contain" />
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {showAdd && (
        <AddCharacterModal
          projectId={projectId}
          onClose={() => setShowAdd(false)}
          onCreated={() => { setShowAdd(false); onRefresh() }}
        />
      )}
    </div>
  )
}

// ─── Videos Tab ───────────────────────────────────────────────
function VideosTab({ projectId, project, videos, sceneCountByVideo, onRefresh, onOpenVideo }: {
  projectId: string; project: Project; videos: Video[]; sceneCountByVideo: Record<string, number>; onRefresh: () => void; onOpenVideo: (v: Video) => void
}) {
  const [showCreate, setShowCreate] = useState(false)
  const normalizedVideoStatus = (raw?: string | null) => (raw || '').trim().toUpperCase()

  const renderVideoStatus = (raw?: string | null) => {
    const status = normalizedVideoStatus(raw)
    if (!status || status === 'DRAFT') return null
    if (status === 'PROCESSING') return <Badge variant="warning">Đang xử lý</Badge>
    if (status === 'COMPLETED') return <Badge variant="success">Hoàn tất</Badge>
    if (status === 'FAILED') return <Badge variant="destructive">Lỗi</Badge>
    return <Badge variant="secondary">{status}</Badge>
  }

  const patchVideo = async (vid: string, field: string, value: string) => {
    const trimmed = value.trim()
    if (field === 'title' && !trimmed) { alert('Tiêu đề không được để trống.'); return }
    try {
      await patchAPI(`/api/videos/${vid}`, { [field]: trimmed || null })
      onRefresh()
    } catch (err) {
      alert(`Lỗi cập nhật: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  const deleteVideo = async (vid: string) => {
    if (!confirm('Xóa video và tất cả phân cảnh?')) return
    await fetchAPI(`/api/videos/${vid}`, { method: 'DELETE' })
    onRefresh()
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-[hsl(var(--muted-foreground))]">{videos.length} video</span>
        <div className="flex-1" />
        <Button size="sm" onClick={() => setShowCreate(true)}><Plus size={11} /> Video mới</Button>
      </div>

      {videos.length === 0 ? (
        <div className="flex flex-col gap-2 py-6">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Chưa có video nào.</p>
          <div><Button size="sm" onClick={() => setShowCreate(true)}><Plus size={11} /> Tạo video đầu tiên</Button></div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {videos.map(v => (
            <Card key={v.id} className="group border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.35)] transition-colors">
              <CardContent className="flex items-center gap-3 px-4 py-3">
                <div className="flex flex-col gap-1 flex-1 min-w-0">
                  <EditableText value={v.title} onSave={value => patchVideo(v.id, 'title', value)} className="font-semibold text-sm" placeholder="Tiêu đề video..." />
                  <EditableText value={v.description ?? ''} onSave={value => patchVideo(v.id, 'description', value)} className="text-xs" placeholder="Mô tả..." />
                  <div className="flex flex-wrap items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                    <span>#{v.display_order}</span>
                    <span>•</span>
                    <span>{sceneCountByVideo[v.id] ?? 0} cảnh</span>
                    <span>•</span>
                    <span>{orientationToAspect(v.orientation ?? project.orientation)}</span>
                    {renderVideoStatus(v.status)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    className="gap-1.5 shadow-none"
                    onClick={() => onOpenVideo(v)}
                  >
                    <Play size={11} />
                    Mở video
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => deleteVideo(v.id)}><Trash2 size={10} /></Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateVideoModal
          projectId={projectId}
          defaultOrientation={project.orientation}
          displayOrder={videos.length}
          onClose={() => setShowCreate(false)}
          onCreated={(vid) => {
            setShowCreate(false); onRefresh()
            const newVideo = { id: vid, project_id: projectId, title: 'Video mới', description: null, display_order: videos.length, status: 'PENDING', orientation: project.orientation, vertical_url: null, horizontal_url: null, thumbnail_url: null, duration: null, resolution: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() } as Video
            onOpenVideo(newVideo)
          }}
        />
      )}
    </div>
  )
}

// ─── Scenes Tab ───────────────────────────────────────────────
function ScenesTab({ projectId, videos, defaultOrientation }: { projectId: string; videos: Video[]; defaultOrientation: string }) {
  const [selectedVideoId, setSelectedVideoId] = useState(videos[0]?.id ?? '')
  const [scenes, setScenes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, any>>({})

  const selectedVideo = videos.find(v => v.id === selectedVideoId)
  const currentOrientation = normalizeOrientation(selectedVideo?.orientation ?? defaultOrientation)

  const loadScenes = () => {
    if (!selectedVideoId) return
    setLoading(true)
    fetchAPI<any[]>(`/api/scenes?video_id=${selectedVideoId}`)
      .then(s => {
        const sorted = [...s].sort((a, b) => a.display_order - b.display_order)
        setScenes(sorted)
        const d: Record<string, any> = {}
        sorted.forEach(sc => { d[sc.id] = { prompt: sc.prompt ?? '', video_prompt: sc.video_prompt ?? '', narrator_text: sc.narrator_text ?? '' } })
        setDrafts(d)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadScenes() }, [selectedVideoId])

  const updateDraft = (id: string, field: string, value: string) =>
    setDrafts(prev => ({ ...prev, [id]: { ...prev[id], [field]: value } }))

  const saveScene = async (id: string) => {
    setSaving(id)
    try {
      await patchAPI(`/api/scenes/${id}`, {
        prompt: drafts[id]?.prompt || null,
        video_prompt: drafts[id]?.video_prompt || null,
        narrator_text: drafts[id]?.narrator_text || null,
      })
    } finally { setSaving(null) }
  }

  const deleteScene = async (id: string) => {
    if (!confirm('Xóa phân cảnh này?')) return
    await fetchAPI(`/api/scenes/${id}`, { method: 'DELETE' })
    loadScenes()
  }

  const addScene = async () => {
    await fetchAPI('/api/scenes', {
      method: 'POST',
      body: JSON.stringify({ video_id: selectedVideoId, display_order: scenes.length, chain_type: 'ROOT', prompt: '', video_prompt: null, narrator_text: null }),
    })
    loadScenes()
  }

  const regenImage = async (sceneId: string) => {
    await fetchAPI('/api/requests/batch', {
      method: 'POST',
      body: JSON.stringify({ requests: [{ type: 'REGENERATE_IMAGE', project_id: projectId, video_id: selectedVideoId, scene_id: sceneId, orientation: currentOrientation }] }),
    })
  }

  const regenVideo = async (sceneId: string) => {
    await fetchAPI('/api/requests/batch', {
      method: 'POST',
      body: JSON.stringify({ requests: [{ type: 'REGENERATE_VIDEO', project_id: projectId, video_id: selectedVideoId, scene_id: sceneId, orientation: currentOrientation }] }),
    })
  }

  if (videos.length === 0) {
    return <p className="text-xs text-[hsl(var(--muted-foreground))] py-6">Chưa có video nào — tạo video trước.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Select value={selectedVideoId} onValueChange={setSelectedVideoId}>
          <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            {videos.map(v => <SelectItem key={v.id} value={v.id}>{v.title}</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">{scenes.length} cảnh</span>
        <div className="flex-1" />
        <Button size="sm" onClick={addScene}><Plus size={11} /> Thêm cảnh</Button>
      </div>

      {loading ? (
        <p className="text-xs text-[hsl(var(--muted-foreground))]">Đang tải...</p>
      ) : scenes.length === 0 ? (
        <div className="flex flex-col gap-2 py-6">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Chưa có phân cảnh nào.</p>
          <div><Button size="sm" onClick={addScene}><Plus size={11} /> Thêm cảnh đầu tiên</Button></div>
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {scenes.map((scene: any) => {
            const expanded = expandedId === scene.id
            const draft = drafts[scene.id] ?? {}
            const isDirty = draft.prompt !== (scene.prompt ?? '') || draft.video_prompt !== (scene.video_prompt ?? '') || draft.narrator_text !== (scene.narrator_text ?? '')
            return (
              <div key={scene.id} className={cn('rounded-lg border bg-[hsl(var(--card))] flex flex-col', expanded ? 'border-[hsl(var(--ring))/0.4]' : 'border-[hsl(var(--border))]')}>
                <div className="flex items-center gap-2 px-3 py-2 cursor-pointer" onClick={() => setExpandedId(expanded ? null : scene.id)}>
                  <span className="text-xs font-bold w-6 flex-shrink-0 text-[hsl(var(--muted-foreground))]">#{scene.display_order + 1}</span>
                  <ChainBadge type={scene.chain_type} />
                  <div className="flex-1 text-xs truncate text-[hsl(var(--foreground))]">
                    {scene.prompt || scene.video_prompt || <span className="text-[hsl(var(--muted-foreground))] italic">Chưa có prompt</span>}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                      <StatusDot status={sceneStatus(scene, currentOrientation, 'image') as StatusType} /> img
                    </span>
                    <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                      <StatusDot status={sceneStatus(scene, currentOrientation, 'video') as StatusType} /> vid
                    </span>
                    <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                      <StatusDot status={sceneStatus(scene, currentOrientation, 'tts') as StatusType} /> tts
                    </span>
                  </div>
                  {isDirty && <span className="text-amber-500 text-xs">●</span>}
                  {expanded ? <ChevronUp size={12} className="text-[hsl(var(--muted-foreground))]" /> : <ChevronDown size={12} className="text-[hsl(var(--muted-foreground))]" />}
                </div>

                {expanded && (
                  <div className="flex flex-col gap-2 px-3 pb-3 border-t border-[hsl(var(--border))]">
                    {sceneUrl(scene, currentOrientation, 'image') && (
                      <img src={sceneUrl(scene, currentOrientation, 'image') ?? ''} alt={`scene ${scene.display_order}`}
                        className="rounded mt-2 object-cover" style={{ maxHeight: 130, maxWidth: 232 }} />
                    )}

                    <div className="flex flex-col gap-1 pt-2">
                      <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Image Prompt</Label>
                      <textarea rows={2} value={draft.prompt ?? ''}
                        onChange={e => updateDraft(scene.id, 'prompt', e.target.value)}
                        className="input resize-y text-xs" style={{ minHeight: 48 }}
                        placeholder="Mô tả hành động cho ảnh..." />
                    </div>

                    <div className="flex flex-col gap-1">
                      <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Video Prompt</Label>
                      <textarea rows={2} value={draft.video_prompt ?? ''}
                        onChange={e => updateDraft(scene.id, 'video_prompt', e.target.value)}
                        className="input resize-y text-xs" style={{ minHeight: 48 }}
                        placeholder="0-3s: ... 3-6s: ... 6-8s: ..." />
                    </div>

                    <div className="flex flex-col gap-1">
                      <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Narrator (TTS)</Label>
                      <textarea rows={2} value={draft.narrator_text ?? ''}
                        onChange={e => updateDraft(scene.id, 'narrator_text', e.target.value)}
                        className="input resize-y text-xs" style={{ minHeight: 48 }}
                        placeholder="Lời bình cho cảnh này..." />
                    </div>

                    <div className="flex gap-1.5 pt-1">
                      <Button size="sm" onClick={() => saveScene(scene.id)} disabled={saving === scene.id || !isDirty}>
                        <Save size={11} /> {saving === scene.id ? 'Đang lưu...' : 'Lưu'}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => regenImage(scene.id)}><Image size={11} /> Regen Ảnh</Button>
                      <Button variant="outline" size="sm" onClick={() => regenVideo(scene.id)}><Film size={11} /> Regen Video</Button>
                      <div className="flex-1" />
                      <Button variant="destructive" size="sm" onClick={() => deleteScene(scene.id)}><Trash2 size={11} /></Button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────
interface Props { projectId: string; onBack: () => void }

export default function ProjectDetailPage({ projectId, onBack }: Props) {
  const [project, setProject] = useState<Project | null>(null)
  const [characters, setCharacters] = useState<Character[]>([])
  const [videos, setVideos] = useState<Video[]>([])
  const [sceneCountByVideo, setSceneCountByVideo] = useState<Record<string, number>>({})
  const [totalScenes, setTotalScenes] = useState(0)
  const [loading, setLoading] = useState(true)
  const [activeVideo, setActiveVideo] = useState<Video | null>(null)

  async function syncActive(videoId?: string) {
    try {
      await fetchAPI('/api/active-project', {
        method: 'PUT',
        body: JSON.stringify(videoId ? { project_id: projectId, video_id: videoId } : { project_id: projectId }),
      })
    } catch { /* non-blocking */ }
  }

  function fetchAll() {
    setLoading(true)
    Promise.all([
      fetchAPI<Project>(`/api/projects/${projectId}`),
      fetchAPI<Character[]>(`/api/projects/${projectId}/characters`),
      fetchAPI<Video[]>(`/api/videos?project_id=${projectId}`),
    ])
      .then(async ([proj, chars, vids]) => {
        setProject(proj); setCharacters(chars); setVideos(vids)
        if (!vids.length) { setSceneCountByVideo({}); setTotalScenes(0); return }
        const counts = await Promise.all(vids.map(v => fetchAPI<any[]>(`/api/scenes?video_id=${v.id}`).then(s => s.length).catch(() => 0)))
        const byVideo: Record<string, number> = {}
        vids.forEach((v, i) => { byVideo[v.id] = counts[i] ?? 0 })
        setSceneCountByVideo(byVideo)
        setTotalScenes(counts.reduce((s, n) => s + n, 0))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  function patchProjectLocal(field: string, value: string) {
    setProject(prev => prev ? { ...prev, [field]: value } : prev)
  }

  useEffect(() => { fetchAll() }, [projectId])
  useEffect(() => { syncActive() }, [projectId])

  if (loading || !project) {
    return <p className="text-xs text-[hsl(var(--muted-foreground))]">Đang tải dự án...</p>
  }

  if (activeVideo) {
    return (
      <div className="h-full min-h-0 overflow-hidden">
        <VideoDetailPage video={activeVideo} projectId={projectId} onBack={() => { setActiveVideo(null); fetchAll() }} />
      </div>
    )
  }

  const aspectLabels = Array.from(new Set(
    (videos.length > 0 ? videos : [{ orientation: project.orientation } as Video])
      .map(v => orientationToAspect(v.orientation ?? project.orientation))
      .filter(Boolean),
  ))

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button variant="ghost" size="sm" onClick={onBack}>← Quay lại</Button>
        <span className="font-semibold text-sm">{project.name}</span>
        <Badge variant="outline">{project.material}</Badge>
      </div>

      <Tabs defaultValue="overview" className="flex-1 flex flex-col min-h-0">
        <TabsList className="flex-shrink-0">
          <TabsTrigger value="overview">Tổng quan</TabsTrigger>
          <TabsTrigger value="characters">Nhân vật ({characters.length})</TabsTrigger>
          <TabsTrigger value="videos">Video ({videos.length})</TabsTrigger>
          <TabsTrigger value="scenes">Phân cảnh</TabsTrigger>
        </TabsList>
        <div className="flex-1 overflow-y-auto pt-3">
          <TabsContent value="overview" className="mt-0">
            <OverviewTab project={project} sceneCount={totalScenes} aspectLabels={aspectLabels} onPatch={patchProjectLocal} onDelete={onBack} />
          </TabsContent>
          <TabsContent value="characters" className="mt-0">
            <CharactersTab projectId={projectId} orientation={project.orientation} characters={characters} onRefresh={fetchAll} />
          </TabsContent>
          <TabsContent value="videos" className="mt-0">
            <VideosTab projectId={projectId} project={project} videos={videos} sceneCountByVideo={sceneCountByVideo} onRefresh={fetchAll} onOpenVideo={v => {
              syncActive(v.id)
              fetchAPI<Video>(`/api/videos/${v.id}`).catch(() => v).then(setActiveVideo)
            }} />
          </TabsContent>
          <TabsContent value="scenes" className="mt-0">
            <ScenesTab projectId={projectId} videos={videos} defaultOrientation={project.orientation} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
