import { BrowserRouter, NavLink, Routes, Route, useLocation } from 'react-router-dom'
import { LayoutDashboard, FolderOpen, ScrollText, Film, Braces, WandSparkles } from 'lucide-react'
import { useWebSocket } from './api/useWebSocket'
import DashboardPage from './pages/DashboardPage'
import ProjectsPage from './pages/ProjectsPage'
import LogsPage from './pages/LogsPage'
import GalleryPage from './pages/GalleryPage'
import ApiStudioPage from './pages/ApiStudioPage'
import WorkflowPage from './pages/WorkflowPage'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { to: '/workflow', icon: WandSparkles, label: 'Workflow', exact: false },
  { to: '/projects', icon: FolderOpen, label: 'Projects', exact: false },
  { to: '/api-studio', icon: Braces, label: 'API Studio', exact: false },
  { to: '/logs', icon: ScrollText, label: 'Logs', exact: false },
  { to: '/gallery', icon: Film, label: 'Gallery', exact: false },
]

function PageTitle() {
  const loc = useLocation()
  const match = NAV.find(n => n.exact ? loc.pathname === n.to : loc.pathname.startsWith(n.to))
  return <span>{match?.label ?? 'Dashboard'}</span>
}

function Layout() {
  const { isConnected } = useWebSocket()

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Left sidebar */}
      <aside className="w-48 flex-shrink-0 flex flex-col border-r" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        <div className="px-4 py-4 text-xs font-bold tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
          Flow Agent
        </div>
        <nav className="flex flex-col gap-1 px-2">
          {NAV.map(({ to, icon: Icon, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded text-xs transition-colors ${
                  isActive
                    ? 'font-semibold'
                    : 'hover:opacity-80'
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? 'var(--card)' : 'transparent',
                color: isActive ? 'var(--accent)' : 'var(--muted)',
              })}
            >
              <Icon size={14} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top header */}
        <header className="flex items-center justify-between px-5 py-3 border-b flex-shrink-0" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
          <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
            <PageTitle />
          </span>
          <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--muted)' }}>
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ background: isConnected ? 'var(--green)' : 'var(--red)' }}
              />
              {isConnected ? 'WS connected' : 'WS disconnected'}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-5">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/workflow" element={<WorkflowPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:id" element={<ProjectsPage />} />
            <Route path="/api-studio" element={<ApiStudioPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/gallery" element={<GalleryPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout />
    </BrowserRouter>
  )
}
