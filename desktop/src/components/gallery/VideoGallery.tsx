import { useState } from 'react'
import type { Scene } from '../../types'
import VideoPlayer from './VideoPlayer'
import { orientationAspectCss, orientationPrefix, sceneUrl } from '../../lib/orientation'

interface VideoGalleryProps {
  scenes: Scene[]
  orientation?: string
}

export default function VideoGallery({ scenes, orientation }: VideoGalleryProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const prefix = orientationPrefix(orientation)

  const videoscenes = scenes.filter(s => {
    const video = sceneUrl(s, orientation, 'video')
    const upscale = sceneUrl(s, orientation, 'upscale')
    return Boolean(video || upscale)
  })

  if (videoscenes.length === 0) {
    return (
      <div className="flex items-center justify-center py-16" style={{ color: 'var(--muted)' }}>
        Chưa có video hoàn tất.
      </div>
    )
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {videoscenes.map((scene, idx) => (
          <div
            key={scene.id}
            className="relative rounded-lg overflow-hidden cursor-pointer transition-transform hover:scale-105"
            style={{ border: '1px solid var(--border)', background: 'var(--card)' }}
            onClick={() => setActiveIndex(idx)}
          >
            {/* Thumbnail */}
            <div className="relative" style={{ aspectRatio: orientationAspectCss(orientation) }}>
              {sceneUrl(scene, orientation, 'image') ? (
                <img
                  src={sceneUrl(scene, orientation, 'image') ?? ''}
                  alt={`Cảnh ${scene.display_order + 1}`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center" style={{ background: 'var(--surface)', color: 'var(--muted)' }}>
                  Chưa có ảnh
                </div>
              )}

              {/* Overlay */}
              <div className="absolute inset-0 flex flex-col justify-between p-2" style={{ background: 'linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 30%, transparent 70%, rgba(0,0,0,0.6) 100%)' }}>
                <div className="flex items-start justify-between">
                  <span className="text-xs font-bold px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.6)', color: 'var(--text)' }}>
                    #{scene.display_order + 1}
                  </span>
                  <div className="flex gap-1">
                    {sceneUrl(scene, orientation, 'video') && (
                      <span title="Video sẵn sàng" className="text-xs px-1 py-0.5 rounded" style={{ background: 'rgba(34,197,94,0.8)', color: '#fff' }}>
                        ✓
                      </span>
                    )}
                    {sceneUrl(scene, orientation, 'upscale') && (
                      <span title="Đã upscale" className="text-xs px-1 py-0.5 rounded" style={{ background: 'rgba(245,158,11,0.8)', color: '#fff' }}>
                        ★
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-xs truncate" style={{ color: 'var(--text)' }}>
                  {scene.prompt?.slice(0, 60) ?? ''}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {activeIndex !== null && (
        <VideoPlayer
          scenes={videoscenes}
          orientation={prefix}
          initialIndex={activeIndex}
          onClose={() => setActiveIndex(null)}
        />
      )}
    </>
  )
}
