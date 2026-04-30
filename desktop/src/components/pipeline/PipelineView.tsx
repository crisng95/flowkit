import { useState, useEffect, useCallback, useRef } from 'react'
import { Image, Film, Mic, Zap, Users } from 'lucide-react'
import { fetchAPI, patchAPI } from '../../api/client'
import { useWebSocket } from '../../api/useWebSocket'
import type { Character, Scene } from '../../types'
import StageNode from './StageNode'
import SceneCard from './SceneCard'
import { orientationPrefix, resolveMediaUrl, sceneStatus } from '../../lib/orientation'
import { Dialog, DialogContent } from '../ui/dialog'

type ExpandedStage = 'refs' | 'image' | 'video' | 'tts' | 'upscale' | null

interface PipelineViewProps {
  projectId: string
  videoId: string
  orientation?: string
}

function deriveStatus(completed: number, total: number, hasFailure: boolean) {
  if (total === 0) return 'pending' as const
  if (hasFailure) return 'failed' as const
  if (completed === total) return 'completed' as const
  if (completed > 0) return 'processing' as const
  return 'pending' as const
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

function resolveSceneImageSource(scene: Scene, orientation?: string): { prefix: 'vertical' | 'horizontal'; mediaId: string | null; url: string | null } | null {
  const primary = orientationPrefix(orientation)
  const secondary = primary === 'vertical' ? 'horizontal' : 'vertical'
  const slots: Array<'vertical' | 'horizontal'> = [primary, secondary]
  for (const prefix of slots) {
    const url = (scene as any)[`${prefix}_image_url`] as string | null
    const mediaId = (scene as any)[`${prefix}_image_media_id`] as string | null
    if (url || mediaId) {
      return { prefix, mediaId: mediaId ?? null, url: url ?? null }
    }
  }
  return null
}

export default function PipelineView({ projectId, videoId, orientation }: PipelineViewProps) {
  const [chars, setChars] = useState<Character[]>([])
  const [scenes, setScenes] = useState<Scene[]>([])
  const [expanded, setExpanded] = useState<ExpandedStage>(null)
  const [resolvedCharUrls, setResolvedCharUrls] = useState<Record<string, string>>({})
  const [resolvedSceneUrls, setResolvedSceneUrls] = useState<Record<string, string>>({})
  const [charPreview, setCharPreview] = useState<{ url: string; name: string } | null>(null)
  const { lastEvent } = useWebSocket()
  const refreshingCharIdsRef = useRef<Set<string>>(new Set())
  const refreshingSceneIdsRef = useRef<Set<string>>(new Set())
  const failedCharRefreshAtRef = useRef<Map<string, number>>(new Map())
  const failedSceneRefreshAtRef = useRef<Map<string, number>>(new Map())
  const autoSweepRanRef = useRef<string>('')
  const REFRESH_RETRY_DELAY_MS = 45_000

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

  const load = useCallback(async () => {
    const [c, s] = await Promise.all([
      fetchAPI<Character[]>(`/api/projects/${projectId}/characters`),
      fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`),
    ])
    setChars(c)
    setScenes(s)
  }, [projectId, videoId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    setResolvedCharUrls({})
    setResolvedSceneUrls({})
    failedCharRefreshAtRef.current.clear()
    failedSceneRefreshAtRef.current.clear()
    autoSweepRanRef.current = ''
  }, [projectId, videoId])

  useEffect(() => {
    if (!lastEvent) return
    const t = lastEvent.type
    if ([
      'scene_created',
      'scene_updated',
      'scene_deleted',
      'character_created',
      'character_updated',
      'character_deleted',
      'request_update',
      'request_completed',
      'request_failed',
      'urls_refreshed',
    ].includes(t)) {
      load()
    }
  }, [lastEvent, load])

  const refreshCharacterPreview = useCallback(async (char: Character) => {
    if (!char.media_id || refreshingCharIdsRef.current.has(char.id)) return null
    const failedAt = failedCharRefreshAtRef.current.get(char.id)
    if (failedAt && Date.now() - failedAt < REFRESH_RETRY_DELAY_MS) return null
    if (!(await ensureFlowTabReadyForMedia())) return null
    refreshingCharIdsRef.current.add(char.id)
    try {
      const refreshed = await fetchAPI<{ fifeUrl?: string; servingUri?: string; url?: string | null }>(
        `/api/flow/media/${char.media_id}?project_id=${encodeURIComponent(projectId)}`,
      )
      const url = pickDirectMediaUrl(refreshed)
      if (!url) return null
      setResolvedCharUrls(prev => (prev[char.id] === url ? prev : { ...prev, [char.id]: url }))
      failedCharRefreshAtRef.current.delete(char.id)
      if (/\/api\/flow\/local-media\?path=/.test(url)) {
        void patchAPI(`/api/characters/${char.id}`, { reference_image_url: url }).catch(() => { })
      }
      return url
    } catch {
      failedCharRefreshAtRef.current.set(char.id, Date.now())
      return null
    } finally {
      refreshingCharIdsRef.current.delete(char.id)
    }
  }, [ensureFlowTabReadyForMedia, projectId])

  const refreshScenePreview = useCallback(async (scene: Scene) => {
    if (refreshingSceneIdsRef.current.has(scene.id)) return null
    const source = resolveSceneImageSource(scene, orientation)
    if (!source?.mediaId) return null
    const failedAt = failedSceneRefreshAtRef.current.get(scene.id)
    if (failedAt && Date.now() - failedAt < REFRESH_RETRY_DELAY_MS) return null
    if (!(await ensureFlowTabReadyForMedia())) return null
    refreshingSceneIdsRef.current.add(scene.id)
    try {
      const refreshed = await fetchAPI<{ fifeUrl?: string; servingUri?: string; url?: string | null }>(
        `/api/flow/media/${source.mediaId}?project_id=${encodeURIComponent(projectId)}`,
      )
      const url = pickDirectMediaUrl(refreshed)
      if (!url) return null
      setResolvedSceneUrls(prev => (prev[scene.id] === url ? prev : { ...prev, [scene.id]: url }))
      failedSceneRefreshAtRef.current.delete(scene.id)
      if (/\/api\/flow\/local-media\?path=/.test(url)) {
        void patchAPI(`/api/scenes/${scene.id}`, { [`${source.prefix}_image_url`]: url }).catch(() => { })
      }
      return url
    } catch {
      failedSceneRefreshAtRef.current.set(scene.id, Date.now())
      return null
    } finally {
      refreshingSceneIdsRef.current.delete(scene.id)
    }
  }, [ensureFlowTabReadyForMedia, orientation, projectId])

  useEffect(() => {
    if (!chars.length) return
    let cancelled = false
    const now = Date.now()
    const candidates = chars
      .filter((char) => {
        if (!char.media_id) return false
        const current = resolveMediaUrl(resolvedCharUrls[char.id] || char.reference_image_url)
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
  }, [chars, refreshCharacterPreview, resolvedCharUrls])

  useEffect(() => {
    const sweepKey = `${projectId}:${videoId}:${orientation || ''}:${scenes.length}`
    if (!scenes.length || autoSweepRanRef.current === sweepKey) return
    autoSweepRanRef.current = sweepKey

    let cancelled = false
    const run = async () => {
      const now = Date.now()
      const candidates = scenes
        .filter((scene) => {
          if (sceneStatus(scene, orientation, 'image') !== 'COMPLETED') return false
          const source = resolveSceneImageSource(scene, orientation)
          if (!source?.mediaId) return false
          const current = resolveMediaUrl(source.url)
          if (!current) return true
          return needsMediaUrlRefresh(current, now)
        })
        .slice(0, 8)
      if (!candidates.length) return
      if (!(await ensureFlowTabReadyForMedia())) return
      const queue = [...candidates]
      const workers = new Array(2).fill(0).map(async () => {
        while (queue.length && !cancelled) {
          const next = queue.shift()
          if (!next) break
          // eslint-disable-next-line no-await-in-loop
          await refreshScenePreview(next)
          // small cooldown to avoid burst against extension
          // eslint-disable-next-line no-await-in-loop
          await new Promise(r => setTimeout(r, 280))
        }
      })
      await Promise.all(workers)
    }
    void run()
    return () => { cancelled = true }
  }, [ensureFlowTabReadyForMedia, orientation, projectId, refreshScenePreview, scenes, videoId])

  const imgStatus = (s: Scene) => sceneStatus(s, orientation, 'image')
  const vidStatus = (s: Scene) => sceneStatus(s, orientation, 'video')
  const ttsStatus = (s: Scene) => sceneStatus(s, orientation, 'tts')
  const upsStatus = (s: Scene) => sceneStatus(s, orientation, 'upscale')

  // Stats
  const refsCompleted = chars.filter(c => c.media_id).length
  const refsTotal = chars.length

  const imagesCompleted = scenes.filter(s => imgStatus(s) === 'COMPLETED').length
  const imagesFailedCount = scenes.filter(s => imgStatus(s) === 'FAILED').length
  const imagesFailed = imagesFailedCount > 0

  const videosCompleted = scenes.filter(s => vidStatus(s) === 'COMPLETED').length
  const videosFailedCount = scenes.filter(s => vidStatus(s) === 'FAILED').length
  const videosFailed = videosFailedCount > 0

  const ttsScenes = scenes.filter(s => (s.narrator_text ?? '').trim())
  const ttsTotal = ttsScenes.length
  const ttsCompleted = ttsScenes.filter(s => ttsStatus(s) === 'COMPLETED').length
  const ttsFailedCount = ttsScenes.filter(s => ttsStatus(s) === 'FAILED').length
  const ttsFailed = ttsFailedCount > 0

  const upscaleCompleted = scenes.filter(s => upsStatus(s) === 'COMPLETED').length
  const upscaleFailedCount = scenes.filter(s => upsStatus(s) === 'FAILED').length
  const upscaleFailed = upscaleFailedCount > 0

  const total = scenes.length

  const stages = [
    {
      key: 'refs' as const,
      name: 'Ref',
      icon: Users,
      completed: refsCompleted,
      total: refsTotal,
      status: deriveStatus(refsCompleted, refsTotal, false),
      failedCount: 0,
    },
    {
      key: 'image' as const,
      name: 'Ảnh',
      icon: Image,
      completed: imagesCompleted,
      total,
      status: deriveStatus(imagesCompleted, total, imagesFailed),
      failedCount: imagesFailedCount,
    },
    {
      key: 'video' as const,
      name: 'Video',
      icon: Film,
      completed: videosCompleted,
      total,
      status: deriveStatus(videosCompleted, total, videosFailed),
      failedCount: videosFailedCount,
    },
    {
      key: 'tts' as const,
      name: 'TTS',
      icon: Mic,
      completed: ttsCompleted,
      total: ttsTotal,
      status: deriveStatus(ttsCompleted, ttsTotal, ttsFailed),
      failedCount: ttsFailedCount,
    },
    {
      key: 'upscale' as const,
      name: 'Upscale',
      icon: Zap,
      completed: upscaleCompleted,
      total,
      status: deriveStatus(upscaleCompleted, total, upscaleFailed),
      failedCount: upscaleFailedCount,
    },
  ]

  const toggle = (key: ExpandedStage) => setExpanded(prev => prev === key ? null : key)

  return (
    <div className="flex flex-col gap-4">
      {/* Stage nodes row */}
      <div className="flex items-stretch gap-2">
        {stages.map((stage, i) => (
          <div key={stage.key} className="flex items-center gap-2 flex-1 min-w-0">
            <StageNode
              name={stage.name}
              icon={stage.icon}
              completed={stage.completed}
              total={stage.total}
              status={stage.status}
              failedCount={stage.failedCount}
              isExpanded={expanded === stage.key}
              onClick={() => toggle(stage.key)}
            />
            {i < stages.length - 1 && (
              <span className="flex-shrink-0 text-sm" style={{ color: 'var(--muted)' }}>→</span>
            )}
          </div>
        ))}
      </div>

      {/* Expanded scene grid */}
      {expanded && expanded !== 'refs' && scenes.length > 0 && (
        <div>
          <div className="text-xs mb-2 font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
            {expanded} — {expanded === 'tts' ? ttsTotal : scenes.length} cảnh
          </div>
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))' }}>
            {(expanded === 'tts' ? ttsScenes : scenes).map(scene => (
              <SceneCard
                key={scene.id}
                scene={scene}
                stage={expanded}
                orientation={orientation}
                thumbOverride={resolvedSceneUrls[scene.id]}
                onThumbError={() => { void refreshScenePreview(scene) }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Expanded refs grid */}
      {expanded === 'refs' && chars.length > 0 && (
        <div>
          <div className="text-xs mb-2 font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
            ref — {chars.length} thực thể
          </div>
          <div
            className="rounded overflow-hidden"
            style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-xs">
                <thead style={{ background: 'var(--surface)' }}>
                  <tr>
                    <th className="text-left font-semibold px-3 py-2 w-[160px]" style={{ color: 'var(--muted)' }}>Ảnh ref</th>
                    <th className="text-left font-semibold px-3 py-2 w-[190px]" style={{ color: 'var(--muted)' }}>Tên</th>
                    <th className="text-left font-semibold px-3 py-2 w-[120px]" style={{ color: 'var(--muted)' }}>Loại</th>
                    <th className="text-left font-semibold px-3 py-2" style={{ color: 'var(--muted)' }}>Prompt / mô tả (gọn)</th>
                    <th className="text-left font-semibold px-3 py-2 w-[140px]" style={{ color: 'var(--muted)' }}>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {chars.map(c => {
                    const refSrc = resolveMediaUrl(resolvedCharUrls[c.id] || c.reference_image_url)
                    const compactText = (c.image_prompt || c.description || '').replace(/\s+/g, ' ').trim()
                    return (
                      <tr key={c.id} style={{ borderTop: '1px solid var(--border)' }}>
                        <td className="px-3 py-2 align-top">
                          <div
                            className="w-[128px] h-[84px] rounded overflow-hidden flex items-center justify-center"
                            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                          >
                            {refSrc ? (
                              <img
                                src={refSrc}
                                alt={c.name}
                                className="max-w-full max-h-full object-contain cursor-zoom-in"
                                onClick={() => setCharPreview({ url: refSrc, name: c.name })}
                                onError={() => { void refreshCharacterPreview(c) }}
                              />
                            ) : (
                              <span style={{ color: 'var(--muted)', fontSize: '10px' }}>Chưa có ảnh</span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <div className="font-semibold truncate" style={{ color: 'var(--text)', maxWidth: 180 }}>{c.name}</div>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <div className="truncate" style={{ color: 'var(--muted)', maxWidth: 110 }}>{c.entity_type}</div>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <div
                            className="truncate"
                            title={compactText || 'Chưa có mô tả'}
                            style={{ color: 'var(--muted)', maxWidth: 420 }}
                          >
                            {compactText || 'Chưa có mô tả'}
                          </div>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <div style={{ color: c.media_id ? 'var(--green)' : 'var(--muted)' }}>
                            {c.media_id ? 'Sẵn sàng' : 'Đang chờ'}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
      {charPreview && (
        <Dialog open onOpenChange={() => setCharPreview(null)}>
          <DialogContent className="max-w-5xl p-0 overflow-hidden bg-black border-0">
            <div className="flex flex-col gap-2 p-3">
              <div className="text-xs text-white/80">{charPreview.name}</div>
              <div className="flex items-center justify-center min-h-[55vh] max-h-[86vh]">
                <img src={charPreview.url} alt={charPreview.name} className="max-w-full max-h-[82vh] object-contain" />
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
