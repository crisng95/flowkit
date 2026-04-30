import type { Scene } from '../types'

export type NormalizedOrientation = 'VERTICAL' | 'HORIZONTAL'
export type SceneStage = 'image' | 'video' | 'upscale' | 'tts'
const LOCAL_MEDIA_PROXY_BASE = 'http://127.0.0.1:8100/api/flow/local-media?path='

export function normalizeOrientation(value?: string | null, fallback: NormalizedOrientation = 'VERTICAL'): NormalizedOrientation {
  if (!value) return fallback
  const upper = String(value).trim().toUpperCase().replace(/\s+/g, '')
  if (
    upper === 'VERTICAL' ||
    upper === 'PORTRAIT' ||
    upper === '9:16' ||
    upper === '9/16' ||
    upper.endsWith('_PORTRAIT')
  ) {
    return 'VERTICAL'
  }
  if (
    upper === 'HORIZONTAL' ||
    upper === 'LANDSCAPE' ||
    upper === '16:9' ||
    upper === '16/9' ||
    upper.endsWith('_LANDSCAPE')
  ) {
    return 'HORIZONTAL'
  }
  return fallback
}

export function orientationPrefix(value?: string | null, fallback: NormalizedOrientation = 'VERTICAL'): 'vertical' | 'horizontal' {
  return normalizeOrientation(value, fallback) === 'VERTICAL' ? 'vertical' : 'horizontal'
}

export function orientationAspect(value?: string | null): string {
  return normalizeOrientation(value) === 'VERTICAL' ? '9:16' : '16:9'
}

export function orientationAspectCss(value?: string | null): string {
  return normalizeOrientation(value) === 'VERTICAL' ? '9 / 16' : '16 / 9'
}

function stageStatus(scene: Scene, prefix: 'vertical' | 'horizontal', stage: SceneStage) {
  if (stage === 'tts') {
    return scene.tts_status as string | undefined
  }
  return scene[`${prefix}_${stage}_status` as keyof Scene] as string | undefined
}

function stageUrl(scene: Scene, prefix: 'vertical' | 'horizontal', stage: SceneStage) {
  const raw = stage === 'tts'
    ? (scene.tts_audio_path as string | null | undefined)
    : (scene[`${prefix}_${stage}_url` as keyof Scene] as string | null | undefined)
  return resolveMediaUrl(raw)
}

export function resolveMediaUrl(value: string | null | undefined): string | null {
  if (!value) return null
  const text = String(value).trim()
  if (!text) return null
  if (/^https?:\/\//i.test(text)) return text
  if (/^data:/i.test(text)) return text
  if (/^\/api\//i.test(text)) return `http://127.0.0.1:8100${text}`
  if (/^file:\/\//i.test(text)) {
    try {
      const parsed = new URL(text)
      const localPath = decodeURIComponent(parsed.pathname)
      return `${LOCAL_MEDIA_PROXY_BASE}${encodeURIComponent(localPath)}`
    } catch {
      return text
    }
  }
  if (/^(\/|[A-Za-z]:[\\/])/.test(text)) {
    return `${LOCAL_MEDIA_PROXY_BASE}${encodeURIComponent(text)}`
  }
  return text
}

export function sceneStatus(scene: Scene, orientation: string | null | undefined, stage: SceneStage): string {
  const primary = orientationPrefix(orientation)
  const secondary = primary === 'vertical' ? 'horizontal' : 'vertical'
  return stageStatus(scene, primary, stage) ?? stageStatus(scene, secondary, stage) ?? 'PENDING'
}

export function sceneUrl(scene: Scene, orientation: string | null | undefined, stage: SceneStage): string | null {
  const primary = orientationPrefix(orientation)
  const secondary = primary === 'vertical' ? 'horizontal' : 'vertical'
  return stageUrl(scene, primary, stage) ?? stageUrl(scene, secondary, stage) ?? null
}
