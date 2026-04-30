import { useState, useEffect } from 'react'
import { fetchAPI } from '../api/client'
import type { Project, Video, Scene } from '../types'
import VideoGallery from '../components/gallery/VideoGallery'
import { normalizeOrientation } from '../lib/orientation'
import { Label } from '../components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select'

export default function GalleryPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [videos, setVideos] = useState<Video[]>([])
  const [selectedVideo, setSelectedVideo] = useState<string>('')
  const [scenes, setScenes] = useState<Scene[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAPI<Project[]>('/api/projects')
      .then(ps => {
        const active = ps.filter(p => p.status !== 'DELETED')
        setProjects(active)
        if (active.length > 0) setSelectedProject(active[0].id)
      })
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    setVideos([]); setSelectedVideo(''); setScenes([])
    fetchAPI<Video[]>(`/api/videos?project_id=${selectedProject}`)
      .then(vs => { setVideos(vs); if (vs.length > 0) setSelectedVideo(vs[0].id) })
      .catch(console.error)
  }, [selectedProject])

  useEffect(() => {
    if (!selectedVideo) return
    setLoading(true)
    fetchAPI<Scene[]>(`/api/scenes?video_id=${selectedVideo}`)
      .then(setScenes).catch(console.error).finally(() => setLoading(false))
  }, [selectedVideo])

  const activeVideo = videos.find(v => v.id === selectedVideo)

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs text-[hsl(var(--muted-foreground))]">Dự án</Label>
          <Select value={selectedProject} onValueChange={setSelectedProject}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Chọn dự án..." />
            </SelectTrigger>
            <SelectContent>
              {projects.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {videos.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-[hsl(var(--muted-foreground))]">Video</Label>
            <Select value={selectedVideo} onValueChange={setSelectedVideo}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Chọn video..." />
              </SelectTrigger>
              <SelectContent>
                {videos.map(v => (
                  <SelectItem key={v.id} value={v.id}>{v.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {loading ? (
        <div className="text-sm text-[hsl(var(--muted-foreground))]">Đang tải cảnh...</div>
      ) : (
        <VideoGallery scenes={scenes} orientation={normalizeOrientation(activeVideo?.orientation)} />
      )}
    </div>
  )
}
