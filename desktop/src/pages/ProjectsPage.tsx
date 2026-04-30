import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, Sparkles } from 'lucide-react'
import { fetchAPI } from '../api/client'
import type { Project } from '../types'
import ProjectDetailPage from './ProjectDetailPage'
import CreateProjectModal from '../components/projects/CreateProjectModal'
import AISetupModal from '../components/projects/AISetupModal'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Separator } from '../components/ui/separator'

type FilterTab = 'ACTIVE' | 'ARCHIVED' | 'ALL'

const tabLabels: Record<FilterTab, string> = {
  ACTIVE: 'Hoạt động',
  ARCHIVED: 'Lưu trữ',
  ALL: 'Tất cả',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('vi-VN')
}

function TierBadge({ tier }: { tier: string | null }) {
  if (!tier) return null
  const isTwo = tier.includes('TWO')
  return (
    <Badge variant={isTwo ? 'warning' : 'secondary'} className="text-xs">
      {isTwo ? 'TIER 2' : 'TIER 1'}
    </Badge>
  )
}

function ProjectCard({ project, onClick }: { project: Project; onClick: () => void }) {
  return (
    <Card
      className="cursor-pointer transition-colors hover:shadow-md flex flex-col"
      onClick={onClick}
    >
      <CardContent className="p-4 flex flex-col gap-2 h-full">
        <div className="font-semibold text-sm text-[hsl(var(--foreground))]">
          {project.name}
        </div>
        {project.description && (
          <div
            className="text-xs text-[hsl(var(--muted-foreground))] overflow-hidden"
            style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}
          >
            {project.description}
          </div>
        )}
        <Separator className="mt-auto" />
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {project.material && (
            <Badge variant="outline" className="text-xs">{project.material}</Badge>
          )}
          <TierBadge tier={project.user_paygate_tier} />
          <span className="text-xs text-[hsl(var(--muted-foreground))] ml-auto">
            {formatDate(project.created_at)}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ProjectsPage() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<FilterTab>('ACTIVE')
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showAISetup, setShowAISetup] = useState(false)

  async function setActiveProject(projectId: string) {
    try {
      await fetchAPI('/api/active-project', {
        method: 'PUT',
        body: JSON.stringify({ project_id: projectId }),
      })
    } catch { /* non-blocking */ }
  }

  function load() {
    setLoading(true)
    fetchAPI<Project[]>('/api/projects')
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { if (!id) load() }, [id])
  useEffect(() => { if (id) { setActiveProject(id) } }, [id])

  if (id) {
    return (
      <div className="h-full min-h-0 overflow-hidden">
        <ProjectDetailPage
          projectId={id}
          onBack={() => { navigate('/projects') }}
        />
      </div>
    )
  }

  const filtered = projects.filter(p => {
    if (tab === 'ALL') return p.status !== 'DELETED'
    return p.status === tab
  })

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['ACTIVE', 'ARCHIVED', 'ALL'] as FilterTab[]).map(t => (
            <Button
              key={t}
              size="sm"
              variant={tab === t ? 'default' : 'outline'}
              onClick={() => setTab(t)}
            >
              {tabLabels[t]}
            </Button>
          ))}
        </div>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" onClick={() => setShowAISetup(true)}>
          <Sparkles size={13} />
          AI Tự động
        </Button>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={13} />
          Dự án mới
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-sm text-[hsl(var(--muted-foreground))]">Đang tải dự án...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col gap-3 py-8">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Chưa có dự án {tabLabels[tab].toLowerCase()} nào.
          </p>
          <div>
            <Button onClick={() => setShowCreate(true)}>
              <Plus size={13} /> Tạo dự án đầu tiên
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {filtered.map(p => (
            <ProjectCard
              key={p.id}
              project={p}
              onClick={() => {
                setActiveProject(p.id)
                navigate(`/projects/${p.id}`)
              }}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateProjectModal
          onClose={() => setShowCreate(false)}
          onCreated={(projId) => {
            setShowCreate(false)
            setActiveProject(projId)
            navigate(`/projects/${projId}`)
          }}
        />
      )}

      {showAISetup && (
        <AISetupModal
          onClose={() => setShowAISetup(false)}
          onCreated={(projId) => {
            setShowAISetup(false)
            setActiveProject(projId)
            navigate(`/projects/${projId}`)
          }}
        />
      )}
    </div>
  )
}
