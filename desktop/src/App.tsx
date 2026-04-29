import { BrowserRouter, NavLink, Routes, Route, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    FolderOpen,
    ScrollText,
    Film,
    Globe,
    Settings,
    ImagePlus,
    Clapperboard,
    ShieldAlert,
    Copy,
    RefreshCw,
    Eye,
    EyeOff,
    Minus,
    Square,
    X,
} from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './api/useWebSocket'
import { useExtensionStatus } from './api/useExtensionStatus'
import { fetchAPI } from './api/client'
import { Badge } from './components/ui/badge'
import { Button } from './components/ui/button'
import { Toaster } from './components/ui/toaster'
import DashboardPage from './pages/DashboardPage'
import ProjectsPage from './pages/ProjectsPage'
import LogsPage from './pages/LogsPage'
import GalleryPage from './pages/GalleryPage'
import SettingsPage from './pages/SettingsPage'
import ManualImagesPage from './pages/ManualImagesPage'
import ManualVideosPage from './pages/ManualVideosPage'

type LicenseStatus = 'ACTIVE' | 'EXPIRED' | 'REVOKED' | 'PENDING' | 'ERROR'

interface LicenseCheckResult {
    allowed: boolean
    status: LicenseStatus
    machineId: string
    machineHash: string | null
    planCode: string | null
    planLabel: string | null
    activatedAt: string | null
    expiresAt: string | null
    revokedReason: string | null
    checkedAt: string
    serverTime: string | null
    source: 'remote' | 'cache'
    apiBaseUrl: string
    message: string
}

const NAV = [
    { to: '/', icon: LayoutDashboard, label: 'Tổng quan', exact: true },
    { to: '/projects', icon: FolderOpen, label: 'Dự án', exact: false },
    { to: '/manual-images', icon: ImagePlus, label: 'Tạo ảnh', exact: false },
    { to: '/manual-videos', icon: Clapperboard, label: 'Tạo video', exact: false },
    { to: '/logs', icon: ScrollText, label: 'Nhật ký', exact: false },
    { to: '/gallery', icon: Film, label: 'Thư viện', exact: false },
    { to: '/settings', icon: Settings, label: 'Cài đặt', exact: false },
]

const LICENSE_STATUS_LABEL: Record<LicenseStatus, string> = {
    ACTIVE: 'Đã kích hoạt',
    EXPIRED: 'Đã hết hạn',
    REVOKED: 'Đã thu hồi',
    PENDING: 'Chưa kích hoạt',
    ERROR: 'Lỗi kết nối',
}

function formatDateTime(value: string | null): string {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('vi-VN')
}

function statusVariant(status: LicenseStatus): 'success' | 'destructive' | 'secondary' {
    if (status === 'ACTIVE') return 'success'
    if (status === 'ERROR') return 'secondary'
    return 'destructive'
}

function PageTitle() {
    const loc = useLocation()
    const match = NAV.find(n => n.exact ? loc.pathname === n.to : loc.pathname.startsWith(n.to))
    return <span>{match?.label ?? 'Tổng quan'}</span>
}

function AgentStatusBadge() {
    const [status, setStatus] = useState('Đang khởi động...')

    useEffect(() => {
        if (window.electron?.onAgentStatus) {
            const unsub = window.electron.onAgentStatus(setStatus)
            return unsub
        }
    }, [])

    const variant = status === 'Ready'
        ? 'success'
        : status.startsWith('Error')
            ? 'destructive'
            : 'secondary'

    return (
        <Badge variant={variant as 'success' | 'destructive' | 'secondary'}>
            Agent · {status === 'Ready' ? 'Sẵn sàng' : status}
        </Badge>
    )
}

function AppWindowHeader() {
    const platform = window.electron?.platform
    const isMac = platform === 'darwin'
    const [isMaximized, setIsMaximized] = useState(false)

    const refreshMaximized = useCallback(() => {
        window.electron?.isWindowMaximized?.()
            .then((maximized) => setIsMaximized(Boolean(maximized)))
            .catch(() => { })
    }, [])

    useEffect(() => {
        refreshMaximized()
        window.addEventListener('resize', refreshMaximized)
        return () => window.removeEventListener('resize', refreshMaximized)
    }, [refreshMaximized])

    const minimize = async () => {
        await window.electron?.windowMinimize?.()
    }

    const toggleMaximize = async () => {
        await window.electron?.windowToggleMaximize?.()
        refreshMaximized()
    }

    const closeWindow = async () => {
        await window.electron?.windowClose?.()
    }

    return (
        <header className="app-window-header" data-platform={platform ?? 'unknown'}>
            <div className="app-window-title">FlowKit</div>
            {!isMac && (
                <div className="app-window-controls">
                    <button
                        type="button"
                        className="app-window-btn"
                        onClick={minimize}
                        aria-label="Thu nhỏ cửa sổ"
                        title="Thu nhỏ"
                    >
                        <Minus size={14} />
                    </button>
                    <button
                        type="button"
                        className="app-window-btn"
                        onClick={toggleMaximize}
                        aria-label={isMaximized ? 'Khôi phục cửa sổ' : 'Phóng to cửa sổ'}
                        title={isMaximized ? 'Khôi phục' : 'Phóng to'}
                    >
                        <Square size={12} />
                    </button>
                    <button
                        type="button"
                        className="app-window-btn app-window-btn-close"
                        onClick={closeWindow}
                        aria-label="Đóng cửa sổ"
                        title="Đóng"
                    >
                        <X size={14} />
                    </button>
                </div>
            )}
        </header>
    )
}

function Layout() {
    const { isConnected } = useWebSocket()
    const { connected: extensionConnected } = useExtensionStatus()
    const [appVersion, setAppVersion] = useState('0.2.0')
    const [flowPanelVisible, setFlowPanelVisible] = useState(true)
    const location = useLocation()

    const openFlowTab = () => window.electron?.openFlowTab({ focus: true, reveal: true })
    const toggleFlowPanel = async () => {
        try {
            const next = await window.electron?.toggleFlowPanel?.()
            if (next) setFlowPanelVisible(Boolean(next.visible))
        } catch {
            // no-op
        }
    }

    useEffect(() => {
        window.electron?.getAppInfo?.()
            .then((info) => {
                if (info?.version) setAppVersion(info.version)
            })
            .catch(() => { })
    }, [])

    useEffect(() => {
        let mounted = true
        window.electron?.getFlowPanelState?.()
            .then((state) => {
                if (!mounted || !state) return
                setFlowPanelVisible(Boolean(state.visible))
            })
            .catch(() => { })
        const unsub = window.electron?.onFlowPanelStateChanged?.((state) => {
            setFlowPanelVisible(Boolean(state?.visible))
        })
        return () => {
            mounted = false
            unsub?.()
        }
    }, [])

    useEffect(() => {
        const match = location.pathname.match(/^\/projects\/([0-9a-f-]{36})$/i)
        if (!match) return
        const projectId = match[1]
        fetchAPI('/api/active-project', {
            method: 'PUT',
            body: JSON.stringify({ project_id: projectId }),
        }).catch(() => { })
    }, [location.pathname])

    return (
        <div className="flex h-full overflow-hidden text-[hsl(var(--foreground))]">
            <aside
                className="w-[220px] flex-shrink-0 flex flex-col border-r border-[hsl(var(--border))] bg-[hsl(var(--sidebar))]"
            >
                <div
                    className="border-b border-[hsl(var(--border))] px-4 pt-4 pb-3"
                >
                    <div className="text-[15px] font-bold leading-none tracking-tight text-[hsl(var(--foreground))]">
                        FlowKit
                    </div>
                    <div className="mt-1 text-[11px] leading-none text-[hsl(var(--muted-foreground))]">
                        v{appVersion}
                    </div>
                </div>

                <nav className="flex flex-col gap-0.5 px-2 py-3 flex-1">
                    {NAV.map(({ to, icon: Icon, label, exact }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={exact}
                            className={({ isActive }) =>
                                `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs transition-all ${isActive
                                    ? 'bg-[hsl(var(--sidebar-accent))] text-[hsl(var(--sidebar-primary))] font-semibold border border-[hsl(var(--sidebar-border))]'
                                    : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--sidebar-accent))] hover:text-[hsl(var(--sidebar-foreground))] border border-transparent'
                                }`
                            }
                        >
                            <Icon size={13} />
                            {label}
                        </NavLink>
                    ))}
                </nav>

                <div className="p-3 border-t border-[hsl(var(--border))]">
                    <Button onClick={openFlowTab} className="w-full gap-1.5 shadow-sm">
                        <Globe size={12} />
                        Mở Google Flow
                    </Button>
                    <Button
                        onClick={() => void toggleFlowPanel()}
                        variant={flowPanelVisible ? 'secondary' : 'outline'}
                        className="w-full gap-1.5 mt-2"
                    >
                        {flowPanelVisible ? <EyeOff size={12} /> : <Eye size={12} />}
                        {flowPanelVisible ? 'Ẩn Extension Panel' : 'Hiện Extension Panel'}
                    </Button>
                </div>
            </aside>

            <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
                <header className="mx-3 mt-3 flex-shrink-0 rounded-lg border border-[hsl(var(--border))] px-4 py-2 bg-[hsl(var(--card))] shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
                                Trung tâm điều khiển
                            </div>
                            <span className="truncate text-sm font-bold tracking-tight text-[hsl(var(--foreground))]">
                                <PageTitle />
                            </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <Badge variant={extensionConnected ? 'success' : 'destructive'}>
                                {extensionConnected ? 'Extension kết nối' : 'Extension mất kết nối'}
                            </Badge>
                            <Badge variant={flowPanelVisible ? 'secondary' : 'outline'}>
                                {flowPanelVisible ? 'Panel: Hiện' : 'Panel: Ẩn'}
                            </Badge>
                            <Badge variant={isConnected ? 'secondary' : 'destructive'}>
                                {isConnected ? 'Realtime ổn' : 'Realtime lỗi'}
                            </Badge>
                            <AgentStatusBadge />
                        </div>
                    </div>
                </header>

                <main className="flex-1 min-h-0 overflow-auto px-3 pb-3 pt-2">
                    <div className="h-full min-h-0 rounded-lg border border-[hsl(var(--border))] p-4 bg-[hsl(var(--card))] shadow-sm">
                        <Routes>
                            <Route path="/" element={<DashboardPage />} />
                            <Route path="/projects" element={<ProjectsPage />} />
                            <Route path="/projects/:id" element={<ProjectsPage />} />
                            <Route path="/manual-images" element={<ManualImagesPage />} />
                            <Route path="/manual-videos" element={<ManualVideosPage />} />
                            <Route path="/logs" element={<LogsPage />} />
                            <Route path="/gallery" element={<GalleryPage />} />
                            <Route path="/settings" element={<SettingsPage />} />
                        </Routes>
                    </div>
                </main>
            </div>

            <Toaster />
        </div>
    )
}

function LicenseGate({
    machineId,
    license,
    onCopyMachineId,
    onRefresh,
    checking,
    feedback,
}: {
    machineId: string
    license: LicenseCheckResult | null
    onCopyMachineId: () => void
    onRefresh: () => void
    checking: boolean
    feedback: string
}) {
    const isRevoked = license?.status === 'REVOKED'
    const isExpired = license?.status === 'EXPIRED'

    return (
        <div className="h-full w-full bg-[hsl(var(--background))] flex items-center justify-center p-6">
            <div className="w-full max-w-3xl rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] shadow-sm p-6 space-y-5">
                <div className="flex items-start gap-3">
                    <div className="h-10 w-10 rounded-lg bg-[hsl(var(--secondary))] flex items-center justify-center">
                        <ShieldAlert size={18} />
                    </div>
                    <div className="space-y-1">
                        <h1 className="text-xl font-semibold tracking-tight">Kích hoạt bản quyền FlowKit</h1>
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">
                            Ứng dụng chỉ hoạt động khi thiết bị đã được active trong CMS theo Machine ID.
                        </p>
                    </div>
                </div>

                <div className="grid gap-4">
                    <div className="space-y-1.5">
                        <div className="text-xs font-medium text-[hsl(var(--muted-foreground))]">Machine ID</div>
                        <div className="flex gap-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-2">
                            <code className="flex-1 text-[11px] break-all leading-5">{machineId || '—'}</code>
                            <Button variant="secondary" onClick={onCopyMachineId} className="gap-1.5 whitespace-nowrap">
                                <Copy size={13} /> Sao chép
                            </Button>
                        </div>
                    </div>
                </div>

                <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] p-3 text-xs space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[hsl(var(--muted-foreground))]">Trạng thái:</span>
                        <Badge variant={license ? statusVariant(license.status) : 'secondary'}>
                            {license ? LICENSE_STATUS_LABEL[license.status] : 'Chưa kiểm tra'}
                        </Badge>
                        {license?.planLabel && <Badge variant="outline">Gói: {license.planLabel}</Badge>}
                        {license?.source === 'cache' && <Badge variant="outline">Bản lưu ngoại tuyến</Badge>}
                    </div>
                    <div className="text-[hsl(var(--muted-foreground))]">
                        {license?.message || 'Bấm kiểm tra lại sau khi admin active máy trong CMS.'}
                    </div>
                    <div className="text-[hsl(var(--muted-foreground))]">
                        Kích hoạt: {formatDateTime(license?.activatedAt ?? null)} · Hết hạn: {formatDateTime(license?.expiresAt ?? null)}
                    </div>
                    <div className="text-[hsl(var(--muted-foreground))]">
                        Lần kiểm tra gần nhất: {formatDateTime(license?.checkedAt ?? null)}
                    </div>
                </div>

                {isRevoked && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 space-y-1.5">
                        <div className="font-semibold">Thiết bị đang ở trạng thái REVOKED</div>
                        <div>Lý do: {license?.revokedReason || 'Không có lý do cụ thể từ quản trị viên.'}</div>
                        <div>Machine ID: <code className="font-mono">{machineId}</code></div>
                        <div>Hướng xử lý: admin cần Active lại license cho đúng Machine ID này trên CMS.</div>
                    </div>
                )}

                {isExpired && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
                        License đã hết hạn. Vui lòng gia hạn lại trong CMS rồi bấm “Kiểm tra lại license”.
                    </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                    <Button onClick={onRefresh} disabled={checking} className="gap-1.5">
                        <RefreshCw size={13} className={checking ? 'animate-spin' : ''} />
                        {checking ? 'Đang kiểm tra...' : 'Kiểm tra lại license'}
                    </Button>
                </div>

                {feedback && (
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-xs text-[hsl(var(--muted-foreground))]">
                        {feedback}
                    </div>
                )}
            </div>
            <Toaster />
        </div>
    )
}

export default function App() {
    const hasLicenseBridge = Boolean(
        window.electron
        && 'getMachineId' in window.electron
        && 'getLicenseStatus' in window.electron
    )

    const [licenseReady, setLicenseReady] = useState(!hasLicenseBridge)
    const [machineId, setMachineId] = useState('')
    const [license, setLicense] = useState<LicenseCheckResult | null>(null)
    const [checking, setChecking] = useState(false)
    const [feedback, setFeedback] = useState('')

    const runLicenseCheck = async (force: boolean) => {
        if (!window.electron?.getLicenseStatus) return
        setChecking(true)
        try {
            const data = await window.electron.getLicenseStatus(force)
            setLicense(data)
            setFeedback(data.message || '')
        } catch (error) {
            setFeedback(error instanceof Error ? error.message : 'Không kiểm tra được license.')
        } finally {
            setChecking(false)
        }
    }

    const copyMachineId = async () => {
        if (!machineId) return
        try {
            await navigator.clipboard.writeText(machineId)
            setFeedback('Đã copy Machine ID.')
        } catch {
            setFeedback(`Machine ID: ${machineId}`)
        }
    }

    useEffect(() => {
        if (!hasLicenseBridge) {
            setLicenseReady(true)
            return
        }

        let isMounted = true
        let timer: ReturnType<typeof setInterval> | null = null

        const init = async () => {
            try {
                const resolvedMachineId = await window.electron!.getMachineId()
                if (!isMounted) return

                setMachineId(resolvedMachineId)

                await runLicenseCheck(true)
            } catch (error) {
                if (!isMounted) return
                setFeedback(error instanceof Error ? error.message : 'Không khởi tạo được license gate.')
            } finally {
                if (isMounted) setLicenseReady(true)
            }

            timer = setInterval(() => {
                void runLicenseCheck(false)
            }, 30000)
        }

        void init()

        return () => {
            isMounted = false
            if (timer) clearInterval(timer)
        }
    }, [hasLicenseBridge])

    useEffect(() => {
        if (!hasLicenseBridge || !window.electron?.onLicenseStatusChanged) return
        return window.electron.onLicenseStatusChanged((next) => {
            setLicense(next)
            setFeedback(next.message || '')
            if (next.machineId) setMachineId((prev) => prev || next.machineId)
        })
    }, [hasLicenseBridge])

    const licenseUnlocked = !hasLicenseBridge || (license?.allowed && license.status === 'ACTIVE')

    if (!licenseReady) {
        return (
            <div className="h-full w-full flex flex-col">
                <AppWindowHeader />
                <div className="flex-1 min-h-0 flex items-center justify-center bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))]">
                    Đang kiểm tra bản quyền thiết bị...
                </div>
            </div>
        )
    }

    if (!licenseUnlocked) {
        return (
            <div className="h-full w-full flex flex-col">
                <AppWindowHeader />
                <div className="flex-1 min-h-0">
                    <LicenseGate
                        machineId={machineId}
                        license={license}
                        onCopyMachineId={copyMachineId}
                        onRefresh={() => void runLicenseCheck(true)}
                        checking={checking}
                        feedback={feedback}
                    />
                </div>
            </div>
        )
    }

    return (
        <div className="h-full w-full flex flex-col">
            <AppWindowHeader />
            <div className="flex-1 min-h-0">
                <BrowserRouter>
                    <Layout />
                </BrowserRouter>
            </div>
        </div>
    )
}
