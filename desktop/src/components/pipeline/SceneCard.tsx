import type { Scene, StatusType } from '../../types'
import { orientationAspectCss, orientationPrefix, resolveMediaUrl } from '../../lib/orientation'

interface SceneCardProps {
  scene: Scene
  stage: 'image' | 'video' | 'upscale' | 'tts'
  orientation?: string
  thumbOverride?: string | null
  onThumbError?: () => void
}

const STATUS_COLORS: Record<StatusType, string> = {
  COMPLETED: 'var(--green)',
  PROCESSING: 'var(--yellow)',
  PENDING: 'var(--muted)',
  FAILED: 'var(--red)',
}

const CHAIN_COLORS: Record<string, string> = {
  ROOT: 'var(--accent)',
  CONTINUATION: 'var(--green)',
  INSERT: 'var(--yellow)',
}

function getStageStatus(scene: Scene, stage: 'image' | 'video' | 'upscale' | 'tts', orientation?: string): StatusType {
  if (stage === 'tts') return scene.tts_status ?? 'PENDING'
  const primary = orientationPrefix(orientation)
  const secondary = primary === 'vertical' ? 'horizontal' : 'vertical'
  const primaryStatus = scene[`${primary}_${stage}_status` as keyof Scene] as StatusType | undefined
  const secondaryStatus = scene[`${secondary}_${stage}_status` as keyof Scene] as StatusType | undefined
  return primaryStatus ?? secondaryStatus ?? 'PENDING'
}

function getThumbUrl(scene: Scene, orientation?: string): string | null {
  const primary = orientationPrefix(orientation)
  const secondary = primary === 'vertical' ? 'horizontal' : 'vertical'
  return (
    (scene[`${primary}_image_url` as keyof Scene] as string | null | undefined) ??
    (scene[`${secondary}_image_url` as keyof Scene] as string | null | undefined) ??
    null
  )
}

export default function SceneCard({ scene, stage, orientation, thumbOverride, onThumbError }: SceneCardProps) {
  const status = getStageStatus(scene, stage, orientation)
  const thumbUrl = resolveMediaUrl(thumbOverride ?? getThumbUrl(scene, orientation))
  const displayText = stage === 'tts' ? scene.narrator_text : (scene.prompt ?? scene.image_prompt)
  const prompt = (displayText ?? '').slice(0, 60)

  return (
    <div
      className="flex flex-col gap-1.5 p-2 rounded text-xs"
      style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
    >
      {/* Thumbnail */}
      <div
        className="w-full rounded overflow-hidden flex items-center justify-center"
        style={{ aspectRatio: orientationAspectCss(orientation), background: 'var(--surface)', maxHeight: '80px' }}
      >
        {thumbUrl ? (
          <img
            src={thumbUrl}
            alt={`Cảnh ${scene.display_order + 1}`}
            className="w-full h-full object-cover"
            onError={() => onThumbError?.()}
          />
        ) : (
          <span style={{ color: 'var(--muted)', fontSize: '10px' }}>Chưa có ảnh</span>
        )}
      </div>

      {/* Scene # + chain badge */}
      <div className="flex items-center gap-1 flex-wrap">
        <span className="font-bold" style={{ color: 'var(--text)' }}>
          #{scene.display_order + 1}
        </span>
        <span
          className="px-1 rounded"
          style={{
            background: CHAIN_COLORS[scene.chain_type] ?? 'var(--muted)',
            color: '#000',
            fontSize: '9px',
            fontWeight: 700,
          }}
        >
          {scene.chain_type}
        </span>
        <span
          className="ml-auto px-1 rounded"
          style={{
            background: STATUS_COLORS[status],
            color: '#000',
            fontSize: '9px',
            fontWeight: 700,
          }}
        >
          {status}
        </span>
      </div>

      {/* Prompt */}
      {prompt && (
        <p className="truncate" style={{ color: 'var(--muted)', fontSize: '10px' }} title={displayText ?? ''}>
          {prompt}{(displayText ?? '').length > 60 ? '…' : ''}
        </p>
      )}
    </div>
  )
}
