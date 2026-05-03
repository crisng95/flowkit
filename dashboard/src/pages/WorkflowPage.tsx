import { useEffect, useMemo, useState } from 'react'
import { fetchAPI, postAPI } from '../api/client'
import type { ChainType, Character, EntityType, Project, Scene, Video } from '../types'

type Orientation = 'VERTICAL' | 'HORIZONTAL'

interface Material {
  id: string
  name: string
}

interface BatchStatus {
  total: number
  pending: number
  processing: number
  completed: number
  failed: number
  done: boolean
}

interface EntityDraft {
  name: string
  entity_type: EntityType
  description: string
}

const ENTITY_TYPES: EntityType[] = ['character', 'location', 'creature', 'visual_asset', 'generic_troop', 'faction']
const CHAIN_TYPES: ChainType[] = ['ROOT', 'CONTINUATION', 'INSERT']

export default function WorkflowPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [videos, setVideos] = useState<Video[]>([])
  const [characters, setCharacters] = useState<Character[]>([])

  const [selectedProject, setSelectedProject] = useState('')
  const [selectedVideo, setSelectedVideo] = useState('')
  const [orientation, setOrientation] = useState<Orientation>('VERTICAL')

  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [projectStory, setProjectStory] = useState('')
  const [projectMaterial, setProjectMaterial] = useState('realistic')
  const [projectLanguage, setProjectLanguage] = useState('en')
  const [allowMusic, setAllowMusic] = useState(false)
  const [allowVoice, setAllowVoice] = useState(false)
  const [entityDrafts, setEntityDrafts] = useState<EntityDraft[]>([
    { name: '', entity_type: 'character', description: '' },
  ])

  const [videoTitle, setVideoTitle] = useState('Video 1')
  const [videoDescription, setVideoDescription] = useState('')

  const [scenePrompt, setScenePrompt] = useState('')
  const [sceneVideoPrompt, setSceneVideoPrompt] = useState('')
  const [sceneOrder, setSceneOrder] = useState(0)
  const [sceneChain, setSceneChain] = useState<ChainType>('ROOT')
  const [sceneChars, setSceneChars] = useState<string[]>([])

  const [stats, setStats] = useState<Record<string, BatchStatus>>({})

  const selectedVideoObj = useMemo(
    () => videos.find((v) => v.id === selectedVideo) ?? null,
    [videos, selectedVideo],
  )

  const canOperatePipeline = selectedProject && selectedVideo

  async function loadProjects() {
    const rows = await fetchAPI<Project[]>('/api/projects')
    setProjects(rows)
  }

  async function loadMaterials() {
    const rows = await fetchAPI<Material[]>('/api/materials')
    setMaterials(rows)
    if (!rows.find((m) => m.id === projectMaterial) && rows.length > 0) {
      setProjectMaterial(rows[0].id)
    }
  }

  async function loadProjectData(projectId: string) {
    if (!projectId) return
    const [chars, vids] = await Promise.all([
      fetchAPI<Character[]>(`/api/projects/${projectId}/characters`),
      fetchAPI<Video[]>(`/api/videos?project_id=${projectId}`),
    ])
    setCharacters(chars)
    setVideos(vids)

    if (!vids.find((v) => v.id === selectedVideo)) {
      setSelectedVideo(vids[0]?.id ?? '')
    }
  }

  async function loadScenes(videoId: string) {
    if (!videoId) {
      setSceneOrder(0)
      return
    }
    const rows = await fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`)
    setSceneOrder(rows.length)
  }

  async function refreshAll() {
    if (!selectedProject) return
    await loadProjectData(selectedProject)
    if (selectedVideo) await loadScenes(selectedVideo)
  }

  useEffect(() => {
    Promise.all([loadProjects(), loadMaterials()]).catch((e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Load failed'
      setError(msg)
    })
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    loadProjectData(selectedProject).catch((e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Load project data failed'
      setError(msg)
    })
  }, [selectedProject])

  useEffect(() => {
    if (!selectedVideo) return
    loadScenes(selectedVideo).catch((e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Load scenes failed'
      setError(msg)
    })
  }, [selectedVideo])

  useEffect(() => {
    if (!selectedVideoObj?.orientation) return
    if (selectedVideoObj.orientation === 'HORIZONTAL' || selectedVideoObj.orientation === 'VERTICAL') {
      setOrientation(selectedVideoObj.orientation)
    }
  }, [selectedVideoObj])

  function updateEntity(index: number, patch: Partial<EntityDraft>) {
    setEntityDrafts((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  function addEntityRow() {
    setEntityDrafts((prev) => [...prev, { name: '', entity_type: 'character', description: '' }])
  }

  function removeEntityRow(index: number) {
    setEntityDrafts((prev) => prev.filter((_, i) => i !== index))
  }

  async function runAction<T>(label: string, fn: () => Promise<T>) {
    setBusy(true)
    setError('')
    setStatus(`${label}...`)
    try {
      const result = await fn()
      setStatus(`${label} xong`)
      return result
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : `${label} failed`
      setError(msg)
      throw e
    } finally {
      setBusy(false)
    }
  }

  async function createProject() {
    if (!projectName.trim()) {
      setError('Project name is required')
      return
    }
    const cleanedEntities = entityDrafts
      .map((e) => ({ ...e, name: e.name.trim(), description: e.description.trim() }))
      .filter((e) => e.name.length > 0)
      .map((e) => ({
        name: e.name,
        entity_type: e.entity_type,
        description: e.description || undefined,
      }))

    const created = await runAction('Tạo project', () =>
      postAPI<Project>('/api/projects', {
        name: projectName.trim(),
        description: projectDescription.trim() || undefined,
        story: projectStory.trim() || undefined,
        language: projectLanguage.trim() || 'en',
        material: projectMaterial,
        allow_music: allowMusic,
        allow_voice: allowVoice,
        characters: cleanedEntities.length > 0 ? cleanedEntities : undefined,
      }),
    )

    await loadProjects()
    setSelectedProject(created.id)
    setProjectName('')
    setProjectDescription('')
    setProjectStory('')
    setEntityDrafts([{ name: '', entity_type: 'character', description: '' }])
  }

  async function createVideo() {
    if (!selectedProject) {
      setError('Chọn project trước')
      return
    }
    if (!videoTitle.trim()) {
      setError('Video title is required')
      return
    }

    const created = await runAction('Tạo video', () =>
      postAPI<Video>('/api/videos', {
        project_id: selectedProject,
        title: videoTitle.trim(),
        description: videoDescription.trim() || undefined,
        orientation,
      }),
    )

    await loadProjectData(selectedProject)
    setSelectedVideo(created.id)
    setVideoTitle(`Video ${videos.length + 2}`)
    setVideoDescription('')
  }

  async function createScene() {
    if (!selectedVideo) {
      setError('Chọn video trước')
      return
    }
    if (!scenePrompt.trim()) {
      setError('Scene prompt is required')
      return
    }

    await runAction('Tạo scene', () =>
      postAPI<Scene>('/api/scenes', {
        video_id: selectedVideo,
        display_order: sceneOrder,
        prompt: scenePrompt.trim(),
        video_prompt: sceneVideoPrompt.trim() || undefined,
        chain_type: sceneChain,
        character_names: sceneChars.length > 0 ? sceneChars : undefined,
      }),
    )

    await loadScenes(selectedVideo)
    setScenePrompt('')
    setSceneVideoPrompt('')
    setSceneChars([])
    setSceneChain('ROOT')
  }

  async function runSkill(path: string, payload: Record<string, unknown>, label: string) {
    await runAction(label, () => postAPI(path, payload))
    await refreshAll()
    await refreshStats()
  }

  async function queueRefImages(regenerate: boolean) {
    if (!selectedProject) return
    await runSkill(
      '/api/skills/fk-gen-refs',
      {
        project_id: selectedProject,
        regenerate,
        wait: false,
      },
      regenerate ? 'Skill fk-gen-refs (regen)' : 'Skill fk-gen-refs',
    )
  }

  async function queueSceneImages(regenerate: boolean) {
    if (!canOperatePipeline) return
    await runSkill(
      '/api/skills/fk-gen-images',
      {
        orientation,
        project_id: selectedProject,
        video_id: selectedVideo,
        regenerate,
        wait: true,
      },
      regenerate ? 'Skill fk-gen-images (regen)' : 'Skill fk-gen-images',
    )
  }

  async function queueSceneVideos(regenerate: boolean) {
    if (!canOperatePipeline) return
    await runSkill(
      '/api/skills/fk-gen-videos',
      {
        orientation,
        project_id: selectedProject,
        video_id: selectedVideo,
        regenerate,
        wait: false,
      },
      regenerate ? 'Skill fk-gen-videos (regen)' : 'Skill fk-gen-videos',
    )
  }

  async function queueUpscales() {
    if (!canOperatePipeline) return
    await runSkill(
      '/api/skills/fk-upscale',
      {
        orientation,
        project_id: selectedProject,
        video_id: selectedVideo,
        wait: false,
      },
      'Skill fk-upscale',
    )
  }

  async function runFullPipeline() {
    if (!canOperatePipeline) return
    await runSkill(
      '/api/skills/fk-pipeline',
      {
        project_id: selectedProject,
        video_id: selectedVideo,
        orientation,
        include_upscale: false,
        regenerate_refs: false,
        regenerate_images: false,
        regenerate_videos: false,
        poll_interval_sec: 5,
        timeout_sec: 1800,
      },
      'Skill fk-pipeline',
    )
  }

  async function refreshStats() {
    if (!selectedVideo) return

    const sumStatuses = (rows: BatchStatus[]): BatchStatus => {
      const total = rows.reduce((acc, r) => acc + r.total, 0)
      const pending = rows.reduce((acc, r) => acc + r.pending, 0)
      const processing = rows.reduce((acc, r) => acc + r.processing, 0)
      const completed = rows.reduce((acc, r) => acc + r.completed, 0)
      const failed = rows.reduce((acc, r) => acc + r.failed, 0)
      return {
        total,
        pending,
        processing,
        completed,
        failed,
        done: pending === 0 && processing === 0 && total > 0,
      }
    }

    const fetchByType = async (baseQuery: string, types: string[]) => {
      const rows = await Promise.all(
        types.map((type) => fetchAPI<BatchStatus>(`/api/requests/batch-status${baseQuery}&type=${type}`)),
      )
      return sumStatuses(rows)
    }

    const next: Record<string, BatchStatus> = {}
    const [refs, images, videos, upscales] = await Promise.all([
      fetchByType(`?project_id=${selectedProject}`, ['GENERATE_CHARACTER_IMAGE', 'REGENERATE_CHARACTER_IMAGE']),
      fetchByType(`?video_id=${selectedVideo}&orientation=${orientation}`, ['GENERATE_IMAGE', 'REGENERATE_IMAGE']),
      fetchByType(`?video_id=${selectedVideo}&orientation=${orientation}`, ['GENERATE_VIDEO', 'REGENERATE_VIDEO']),
      fetchByType(`?video_id=${selectedVideo}&orientation=${orientation}`, ['UPSCALE_VIDEO']),
    ])
    next.Refs = refs
    next.Images = images
    next.Videos = videos
    next.Upscale = upscales
    setStats(next)
  }

  useEffect(() => {
    if (!selectedVideo || !selectedProject) {
      setStats({})
      return
    }
    refreshStats().catch((e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Load stats failed'
      setError(msg)
    })
  }, [selectedProject, selectedVideo, orientation])

  const availableSceneCharacters = useMemo(
    () => characters.map((c) => c.name),
    [characters],
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg p-3" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
        <div className="text-xs font-semibold mb-2" style={{ color: 'var(--muted)' }}>System</div>
        <div className="flex items-center gap-2 text-xs flex-wrap">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="px-2 py-1.5 rounded"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', minWidth: '220px' }}
          >
            <option value="">Select project...</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>

          <select
            value={selectedVideo}
            onChange={(e) => setSelectedVideo(e.target.value)}
            className="px-2 py-1.5 rounded"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', minWidth: '220px' }}
          >
            <option value="">Select video...</option>
            {videos.map((v) => <option key={v.id} value={v.id}>{v.title}</option>)}
          </select>

          <select
            value={orientation}
            onChange={(e) => setOrientation(e.target.value as Orientation)}
            className="px-2 py-1.5 rounded"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            <option value="VERTICAL">VERTICAL</option>
            <option value="HORIZONTAL">HORIZONTAL</option>
          </select>

          <button
            onClick={() => refreshAll().then(() => refreshStats())}
            disabled={busy || !selectedProject}
            className="px-3 py-1.5 rounded font-semibold"
            style={{ background: 'var(--accent)', color: '#fff', opacity: busy ? 0.7 : 1 }}
          >
            Refresh
          </button>
        </div>
        {status && <div className="mt-2 text-xs" style={{ color: 'var(--green)' }}>{status}</div>}
        {error && <div className="mt-2 text-xs" style={{ color: 'var(--red)' }}>{error}</div>}
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))' }}>
        <div className="rounded-lg p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>1) Create Project + Entities</div>
          <input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="Project name" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          <input value={projectDescription} onChange={(e) => setProjectDescription(e.target.value)} placeholder="Description" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          <textarea value={projectStory} onChange={(e) => setProjectStory(e.target.value)} rows={3} placeholder="Story" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />

          <div className="grid gap-2" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <select value={projectMaterial} onChange={(e) => setProjectMaterial(e.target.value)} className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}>
              {materials.map((m) => <option key={m.id} value={m.id}>{m.id}</option>)}
            </select>
            <input value={projectLanguage} onChange={(e) => setProjectLanguage(e.target.value)} placeholder="Language (en, vi...)" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          </div>

          <label className="text-xs flex items-center gap-2"><input type="checkbox" checked={allowMusic} onChange={(e) => setAllowMusic(e.target.checked)} /> allow_music</label>
          <label className="text-xs flex items-center gap-2"><input type="checkbox" checked={allowVoice} onChange={(e) => setAllowVoice(e.target.checked)} /> allow_voice</label>

          <div className="text-xs font-semibold mt-1" style={{ color: 'var(--muted)' }}>Entities</div>
          {entityDrafts.map((row, idx) => (
            <div key={`entity-${idx}`} className="grid gap-2" style={{ gridTemplateColumns: '1.2fr 1fr 1.6fr auto' }}>
              <input value={row.name} onChange={(e) => updateEntity(idx, { name: e.target.value })} placeholder="name" className="px-2 py-1 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
              <select value={row.entity_type} onChange={(e) => updateEntity(idx, { entity_type: e.target.value as EntityType })} className="px-2 py-1 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}>
                {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <input value={row.description} onChange={(e) => updateEntity(idx, { description: e.target.value })} placeholder="appearance description" className="px-2 py-1 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
              <button onClick={() => removeEntityRow(idx)} disabled={entityDrafts.length <= 1} className="px-2 py-1 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--red)' }}>x</button>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <button onClick={addEntityRow} className="px-2 py-1 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}>+ Entity</button>
            <button onClick={createProject} disabled={busy} className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy ? 0.7 : 1 }}>Create Project</button>
          </div>
        </div>

        <div className="rounded-lg p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>2) Create Video + Scene</div>
          <input value={videoTitle} onChange={(e) => setVideoTitle(e.target.value)} placeholder="Video title" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          <input value={videoDescription} onChange={(e) => setVideoDescription(e.target.value)} placeholder="Video description" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          <button onClick={createVideo} disabled={busy || !selectedProject} className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy || !selectedProject ? 0.7 : 1 }}>Create Video</button>

          <div className="mt-2 text-xs font-semibold" style={{ color: 'var(--muted)' }}>Scene Form</div>
          <input value={String(sceneOrder)} onChange={(e) => setSceneOrder(Number(e.target.value))} type="number" min={0} className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          <select value={sceneChain} onChange={(e) => setSceneChain(e.target.value as ChainType)} className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}>
            {CHAIN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <textarea value={scenePrompt} onChange={(e) => setScenePrompt(e.target.value)} rows={3} placeholder="Scene prompt (action)" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          <textarea value={sceneVideoPrompt} onChange={(e) => setSceneVideoPrompt(e.target.value)} rows={3} placeholder="Video prompt (optional)" className="px-2 py-1.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }} />

          <select
            value=""
            onChange={(e) => {
              const value = e.target.value
              if (!value) return
              if (!sceneChars.includes(value)) setSceneChars((prev) => [...prev, value])
            }}
            className="px-2 py-1.5 rounded text-xs"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            <option value="">Add character to scene...</option>
            {availableSceneCharacters.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
          {sceneChars.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {sceneChars.map((name) => (
                <button key={name} onClick={() => setSceneChars((prev) => prev.filter((x) => x !== name))} className="px-2 py-0.5 rounded text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}>
                  {name} x
                </button>
              ))}
            </div>
          )}
          <button onClick={createScene} disabled={busy || !selectedVideo} className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy || !selectedVideo ? 0.7 : 1 }}>Create Scene</button>
        </div>
      </div>

      <div className="rounded-lg p-3 flex flex-col gap-3" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
        <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>3) Run Pipeline (No JSON)</div>
        <button
          onClick={() => runFullPipeline()}
          disabled={busy || !canOperatePipeline}
          className="px-3 py-2 rounded text-xs font-semibold"
          style={{ background: 'var(--green)', color: '#0b111a', opacity: busy || !canOperatePipeline ? 0.7 : 1 }}
        >
          Run Full Pipeline Skill
        </button>
        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
          <button onClick={() => queueRefImages(false)} disabled={busy || !selectedProject} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy || !selectedProject ? 0.7 : 1 }}>Gen Refs</button>
          <button onClick={() => queueRefImages(true)} disabled={busy || !selectedProject} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', opacity: busy || !selectedProject ? 0.7 : 1 }}>Regen Refs</button>
          <button onClick={() => queueSceneImages(false)} disabled={busy || !canOperatePipeline} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy || !canOperatePipeline ? 0.7 : 1 }}>Gen Images</button>
          <button onClick={() => queueSceneImages(true)} disabled={busy || !canOperatePipeline} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', opacity: busy || !canOperatePipeline ? 0.7 : 1 }}>Regen Images</button>
          <button onClick={() => queueSceneVideos(false)} disabled={busy || !canOperatePipeline} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy || !canOperatePipeline ? 0.7 : 1 }}>Gen Videos</button>
          <button onClick={() => queueSceneVideos(true)} disabled={busy || !canOperatePipeline} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', opacity: busy || !canOperatePipeline ? 0.7 : 1 }}>Regen Videos</button>
          <button onClick={() => queueUpscales()} disabled={busy || !canOperatePipeline} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--accent)', color: '#fff', opacity: busy || !canOperatePipeline ? 0.7 : 1 }}>Upscale</button>
          <button onClick={() => refreshStats()} disabled={!canOperatePipeline} className="px-2 py-2 rounded text-xs font-semibold" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', opacity: !canOperatePipeline ? 0.7 : 1 }}>Refresh Status</button>
        </div>

        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          {Object.entries(stats).map(([label, s]) => (
            <div key={label} className="rounded p-2 text-xs" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="font-semibold mb-1">{label}</div>
              <div>Total: {s.total}</div>
              <div>Pending: {s.pending}</div>
              <div>Processing: {s.processing}</div>
              <div>Completed: {s.completed}</div>
              <div>Failed: {s.failed}</div>
              <div style={{ color: s.done ? 'var(--green)' : 'var(--yellow)' }}>{s.done ? 'Done' : 'Running'}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
