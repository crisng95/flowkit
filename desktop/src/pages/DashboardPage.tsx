import { useState, useEffect } from 'react'
import { fetchAPI } from '../api/client'
import { useWebSocket } from '../api/useWebSocket'
import type { Project, Video } from '../types'
import PipelineView from '../components/pipeline/PipelineView'
import { normalizeOrientation } from '../lib/orientation'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select'

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [videos, setVideos] = useState<Video[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [selectedVideo, setSelectedVideo] = useState<string>('')
  const [preferredVideoId, setPreferredVideoId] = useState<string>('')
  const { lastEvent } = useWebSocket()

  useEffect(() => {
    Promise.all([
      fetchAPI<Project[]>('/api/projects').catch(() => []),
      fetchAPI<{ project_id?: string | null; video_id?: string | null }>('/api/active-project').catch(() => ({ project_id: null, video_id: null })),
    ]).then(([ps, active]) => {
      const visible = ps.filter(p => p.status !== 'DELETED')
      setProjects(visible)
      const activeProjectId = active.project_id && visible.some(p => p.id === active.project_id)
        ? active.project_id
        : (visible[0]?.id ?? '')
      setSelectedProject(activeProjectId)
      setPreferredVideoId(active.video_id ?? '')
    }).catch(() => { })
  }, [])

  useEffect(() => {
    if (!selectedProject) { setVideos([]); setSelectedVideo(''); return }
    fetchAPI<Video[]>(`/api/videos?project_id=${selectedProject}`)
      .then(v => {
        setVideos(v)
        if (v.length === 0) { setSelectedVideo(''); return }
        if (preferredVideoId && v.some(item => item.id === preferredVideoId)) {
          setSelectedVideo(preferredVideoId)
          setPreferredVideoId('')
          return
        }
        setSelectedVideo(v[0].id)
      })
      .catch(() => { })
  }, [selectedProject, preferredVideoId])

  const syncActive = async (projectId: string, videoId?: string) => {
    if (!projectId) return
    try {
      await fetchAPI('/api/active-project', {
        method: 'PUT',
        body: JSON.stringify(videoId ? { project_id: projectId, video_id: videoId } : { project_id: projectId }),
      })
    } catch { /* non-blocking */ }
  }

  const changeProject = async (projectId: string) => {
    setSelectedProject(projectId)
    await syncActive(projectId)
  }

  useEffect(() => {
    if (!selectedProject || !selectedVideo) return
    if (!videos.some(v => v.id === selectedVideo)) return
    syncActive(selectedProject, selectedVideo)
  }, [selectedProject, selectedVideo, videos])

  useEffect(() => {
    if (!lastEvent) return
    if (['project_created', 'project_updated', 'project_deleted'].includes(lastEvent.type)) {
      fetchAPI<Project[]>('/api/projects').then(setProjects).catch(() => { })
    }
  }, [lastEvent])

  const activeVideo = videos.find(v => v.id === selectedVideo)

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Selectors */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select value={selectedProject} onValueChange={changeProject}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Chọn dự án..." />
          </SelectTrigger>
          <SelectContent>
            {projects.map(p => (
              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={selectedVideo}
          onValueChange={setSelectedVideo}
          disabled={!selectedProject || videos.length === 0}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Chọn video..." />
          </SelectTrigger>
          <SelectContent>
            {videos.map(v => (
              <SelectItem key={v.id} value={v.id}>{v.title}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Pipeline */}
      {selectedProject && selectedVideo ? (
        <PipelineView
          projectId={selectedProject}
          videoId={selectedVideo}
          orientation={normalizeOrientation(activeVideo?.orientation)}
        />
      ) : (
        <div className="py-8 text-sm text-[hsl(var(--muted-foreground))]">
          Chọn dự án và video để xem pipeline
        </div>
      )}
    </div>
  )
}
