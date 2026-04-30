import { useState, useEffect } from 'react'
import type { Scene } from '../../types'

interface VideoPlayerProps {
  scenes: Scene[]
  orientation?: 'vertical' | 'horizontal'
  initialIndex: number
  onClose: () => void
}

function parseCharacterNames(raw: string[] | string | null): string[] {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed
    return []
  } catch {
    return []
  }
}

export default function VideoPlayer({ scenes, orientation = 'vertical', initialIndex, onClose }: VideoPlayerProps) {
  const [index, setIndex] = useState(initialIndex)
  const scene = scenes[index]
  const primary = orientation
  const secondary = primary === 'vertical' ? 'horizontal' : 'vertical'
  const videoSrc = (
    scene[`${primary}_upscale_url` as keyof Scene] as string | null | undefined
  ) || (
    scene[`${primary}_video_url` as keyof Scene] as string | null | undefined
  ) || (
    scene[`${secondary}_upscale_url` as keyof Scene] as string | null | undefined
  ) || (
    scene[`${secondary}_video_url` as keyof Scene] as string | null | undefined
  ) || ''
  const charNames = parseCharacterNames(scene.character_names)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft' && index > 0) setIndex(i => i - 1)
      if (e.key === 'ArrowRight' && index < scenes.length - 1) setIndex(i => i + 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, scenes.length, onClose])

  function chainBadgeStyle(ct: string) {
    if (ct === 'ROOT') return { background: 'var(--accent)', color: '#fff' }
    if (ct === 'CONTINUATION') return { background: 'var(--green)', color: '#fff' }
    return { background: 'var(--yellow)', color: '#000' }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.85)' }}
      onClick={onClose}
    >
      <div
        className="flex rounded-lg overflow-hidden relative"
        style={{ maxHeight: '90vh', maxWidth: '90vw', background: 'var(--surface)' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          className="absolute top-2 right-2 z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
          style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--text)' }}
          onClick={onClose}
        >
          X
        </button>

        {/* Video */}
        <div className="flex items-center justify-center" style={{ background: '#000', minWidth: 280, maxWidth: '60vw' }}>
          <video
            key={videoSrc}
            src={videoSrc}
            controls
            autoPlay
            className="h-full"
            style={{ maxHeight: '90vh', maxWidth: '60vw', display: 'block' }}
          />
        </div>

        {/* Sidebar */}
        <div
          className="flex flex-col p-4 gap-3 overflow-y-auto"
          style={{ width: 320, background: 'var(--surface)', borderLeft: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-2">
              <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: 'var(--card)', color: 'var(--muted)' }}>
              Cảnh #{scene.display_order + 1}
              </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded" style={chainBadgeStyle(scene.chain_type)}>
              {scene.chain_type}
            </span>
          </div>

          {scene.prompt && (
            <div>
              <div className="text-xs font-bold mb-1" style={{ color: 'var(--muted)' }}>PROMPT ẢNH</div>
              <div className="text-xs" style={{ color: 'var(--text)' }}>{scene.prompt}</div>
            </div>
          )}

          {scene.video_prompt && (
            <div>
              <div className="text-xs font-bold mb-1" style={{ color: 'var(--muted)' }}>VIDEO PROMPT</div>
              <div className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text)' }}>{scene.video_prompt}</div>
            </div>
          )}

          {charNames.length > 0 && (
            <div>
              <div className="text-xs font-bold mb-1" style={{ color: 'var(--muted)' }}>NHÂN VẬT</div>
              <div className="flex flex-wrap gap-1">
                {charNames.map(name => (
                  <span key={name} className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--card)', color: 'var(--accent)' }}>
                    {name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Download */}
          <a
            href={videoSrc}
            download={`scene-${scene.display_order + 1}.mp4`}
            className="text-xs px-3 py-1.5 rounded text-center font-semibold mt-auto"
            style={{ background: 'var(--accent)', color: '#fff', textDecoration: 'none' }}
          >
            Tải video
          </a>

          {/* Prev / Next */}
          <div className="flex gap-2">
            <button
              disabled={index === 0}
              onClick={() => setIndex(i => i - 1)}
              className="flex-1 text-xs py-1.5 rounded font-semibold disabled:opacity-30"
              style={{ background: 'var(--card)', color: 'var(--text)', border: '1px solid var(--border)' }}
            >
              Trước
            </button>
            <button
              disabled={index === scenes.length - 1}
              onClick={() => setIndex(i => i + 1)}
              className="flex-1 text-xs py-1.5 rounded font-semibold disabled:opacity-30"
              style={{ background: 'var(--card)', color: 'var(--text)', border: '1px solid var(--border)' }}
            >
              Sau
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
