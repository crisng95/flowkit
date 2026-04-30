import { useMemo, useState } from 'react'
import {
    AlertTriangle,
    CheckCircle2,
    Loader2,
    PlayCircle,
    RefreshCw,
    Wrench,
} from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'

export type PreflightStatus = 'pass' | 'warn' | 'fail' | 'running'

export interface PreflightCheckItem {
    id: string
    label: string
    status: PreflightStatus
    description?: string
    hint?: string
    blocking?: boolean
    quickFixLabel?: string
    quickFix?: () => Promise<void> | void
    lastError?: string | null
}

interface PreflightModalProps {
    title?: string
    subtitle?: string
    checks: PreflightCheckItem[]
    onClose: () => void
    onRecheck?: () => Promise<void> | void
    onContinue?: () => Promise<void> | void
    continueLabel?: string
    allowContinueWithBlocking?: boolean
    showApplyAllFixes?: boolean
}

type FixState = 'idle' | 'running' | 'done' | 'error'

const STATUS_META: Record<PreflightStatus, { text: string; color: string; bg: string; border: string }> = {
    pass: {
        text: 'PASS',
        color: 'var(--green)',
        bg: 'rgba(34,197,94,0.08)',
        border: 'rgba(34,197,94,0.28)',
    },
    warn: {
        text: 'WARN',
        color: '#b45309',
        bg: 'rgba(245,158,11,0.10)',
        border: 'rgba(245,158,11,0.30)',
    },
    fail: {
        text: 'FAIL',
        color: 'var(--red)',
        bg: 'rgba(239,68,68,0.10)',
        border: 'rgba(239,68,68,0.30)',
    },
    running: {
        text: 'RUNNING',
        color: 'var(--accent)',
        bg: 'rgba(59,130,246,0.10)',
        border: 'rgba(59,130,246,0.30)',
    },
}

function StatusIcon({ status }: { status: PreflightStatus }) {
    if (status === 'pass') return <CheckCircle2 size={13} style={{ color: 'var(--green)' }} />
    if (status === 'running') return <Loader2 size={13} className="animate-spin" style={{ color: 'var(--accent)' }} />
    return <AlertTriangle size={13} style={{ color: status === 'warn' ? '#b45309' : 'var(--red)' }} />
}

function MiniBadge({ status }: { status: PreflightStatus }) {
    const m = STATUS_META[status]
    return (
        <span
            className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide"
            style={{ color: m.color, background: m.bg, border: `1px solid ${m.border}` }}
        >
            {m.text}
        </span>
    )
}

export default function PreflightModal({
    title = 'Preflight Checklist',
    subtitle = 'Kiểm tra điều kiện trước khi chạy batch. Có thể sửa nhanh các lỗi phổ biến.',
    checks,
    onClose,
    onRecheck,
    onContinue,
    continueLabel = 'Tiếp tục',
    allowContinueWithBlocking = false,
    showApplyAllFixes = true,
}: PreflightModalProps) {
    const [runningRecheck, setRunningRecheck] = useState(false)
    const [runningContinue, setRunningContinue] = useState(false)
    const [runningApplyAll, setRunningApplyAll] = useState(false)
    const [globalError, setGlobalError] = useState('')
    const [fixStateById, setFixStateById] = useState<Record<string, FixState>>({})
    const [fixErrorById, setFixErrorById] = useState<Record<string, string>>({})

    const summary = useMemo(() => {
        const pass = checks.filter(c => c.status === 'pass').length
        const warn = checks.filter(c => c.status === 'warn').length
        const fail = checks.filter(c => c.status === 'fail').length
        const running = checks.filter(c => c.status === 'running').length
        const blockingFail = checks.some(c => c.status === 'fail' && c.blocking !== false)
        return { pass, warn, fail, running, blockingFail }
    }, [checks])

    const actionableChecks = useMemo(
        () => checks.filter(c => (c.status === 'warn' || c.status === 'fail') && !!c.quickFix),
        [checks],
    )

    const runRecheck = async () => {
        if (!onRecheck) return
        setGlobalError('')
        setRunningRecheck(true)
        try {
            await onRecheck()
        } catch (e: any) {
            setGlobalError(e?.message ?? 'Recheck thất bại')
        } finally {
            setRunningRecheck(false)
        }
    }

    const runFix = async (item: PreflightCheckItem) => {
        if (!item.quickFix) return
        setGlobalError('')
        setFixErrorById(prev => ({ ...prev, [item.id]: '' }))
        setFixStateById(prev => ({ ...prev, [item.id]: 'running' }))
        try {
            await item.quickFix()
            setFixStateById(prev => ({ ...prev, [item.id]: 'done' }))
            if (onRecheck) await onRecheck()
        } catch (e: any) {
            const msg = e?.message ?? 'Fix thất bại'
            setFixErrorById(prev => ({ ...prev, [item.id]: msg }))
            setFixStateById(prev => ({ ...prev, [item.id]: 'error' }))
        }
    }

    const applyAllFixes = async () => {
        if (!actionableChecks.length) return
        setGlobalError('')
        setRunningApplyAll(true)
        try {
            for (const item of actionableChecks) {
                // eslint-disable-next-line no-await-in-loop
                await runFix(item)
            }
            if (onRecheck) await onRecheck()
        } catch (e: any) {
            setGlobalError(e?.message ?? 'Áp dụng tất cả fix thất bại')
        } finally {
            setRunningApplyAll(false)
        }
    }

    const continueDisabled =
        !onContinue ||
        runningContinue ||
        runningApplyAll ||
        runningRecheck ||
        (!allowContinueWithBlocking && summary.blockingFail)

    const handleContinue = async () => {
        if (!onContinue) return
        setGlobalError('')
        setRunningContinue(true)
        try {
            await onContinue()
        } catch (e: any) {
            setGlobalError(e?.message ?? 'Không thể tiếp tục')
        } finally {
            setRunningContinue(false)
        }
    }

    return (
        <Modal title={title} onClose={onClose} width={720}>
            <div className="flex flex-col gap-4">
                <div className="text-xs leading-relaxed" style={{ color: 'var(--muted)' }}>
                    {subtitle}
                </div>

                <div
                    className="rounded-lg p-3 flex flex-wrap gap-2 text-xs"
                    style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
                >
                    <span style={{ color: 'var(--green)' }}>✓ Pass: {summary.pass}</span>
                    <span style={{ color: '#b45309' }}>⚠ Warn: {summary.warn}</span>
                    <span style={{ color: 'var(--red)' }}>✗ Fail: {summary.fail}</span>
                    {summary.running > 0 && <span style={{ color: 'var(--accent)' }}>⏳ Running: {summary.running}</span>}
                    <div className="flex-1" />
                    <span style={{ color: 'var(--muted)' }}>
                        {summary.blockingFail ? 'Có lỗi chặn thao tác' : 'Đủ điều kiện để tiếp tục'}
                    </span>
                </div>

                <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
                    {checks.map(item => {
                        const currentFixState = fixStateById[item.id] ?? 'idle'
                        const hasFix = !!item.quickFix
                        const canFix = hasFix && (item.status === 'warn' || item.status === 'fail')

                        return (
                            <div
                                key={item.id}
                                className="rounded-lg p-3 flex flex-col gap-2"
                                style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
                            >
                                <div className="flex items-start gap-2">
                                    <StatusIcon status={item.status} />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-xs font-semibold" style={{ color: 'var(--text)' }}>
                                                {item.label}
                                            </span>
                                            <MiniBadge status={item.status} />
                                            {item.blocking !== false && item.status === 'fail' && (
                                                <span
                                                    className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold"
                                                    style={{
                                                        color: 'var(--red)',
                                                        background: 'rgba(239,68,68,0.08)',
                                                        border: '1px solid rgba(239,68,68,0.28)',
                                                    }}
                                                >
                                                    BLOCKING
                                                </span>
                                            )}
                                        </div>
                                        {item.description && (
                                            <div className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--muted)' }}>
                                                {item.description}
                                            </div>
                                        )}
                                        {item.hint && (
                                            <div
                                                className="text-[11px] mt-1 rounded px-2 py-1"
                                                style={{
                                                    color: 'var(--muted)',
                                                    background: 'rgba(59,130,246,0.08)',
                                                    border: '1px solid rgba(59,130,246,0.20)',
                                                }}
                                            >
                                                {item.hint}
                                            </div>
                                        )}
                                        {(fixErrorById[item.id] || item.lastError) && (
                                            <div
                                                className="text-[11px] mt-1 rounded px-2 py-1"
                                                style={{
                                                    color: 'var(--red)',
                                                    background: 'rgba(239,68,68,0.08)',
                                                    border: '1px solid rgba(239,68,68,0.24)',
                                                }}
                                            >
                                                {fixErrorById[item.id] || item.lastError}
                                            </div>
                                        )}
                                    </div>

                                    {canFix && (
                                        <ActionButton
                                            variant="secondary"
                                            size="sm"
                                            onClick={() => runFix(item)}
                                            disabled={currentFixState === 'running' || runningApplyAll}
                                        >
                                            {currentFixState === 'running' ? (
                                                <>
                                                    <Loader2 size={11} className="animate-spin" />
                                                    Đang fix...
                                                </>
                                            ) : (
                                                <>
                                                    <Wrench size={11} />
                                                    {item.quickFixLabel || 'Fix nhanh'}
                                                </>
                                            )}
                                        </ActionButton>
                                    )}
                                </div>
                            </div>
                        )
                    })}
                </div>

                {globalError && (
                    <div
                        className="text-xs rounded px-3 py-2"
                        style={{
                            color: 'var(--red)',
                            background: 'rgba(239,68,68,0.10)',
                            border: '1px solid rgba(239,68,68,0.25)',
                        }}
                    >
                        {globalError}
                    </div>
                )}

                <div className="flex items-center justify-between gap-2 pt-1">
                    <div className="flex items-center gap-2">
                        {showApplyAllFixes && actionableChecks.length > 0 && (
                            <ActionButton
                                variant="secondary"
                                size="sm"
                                onClick={applyAllFixes}
                                disabled={runningApplyAll || runningRecheck}
                            >
                                {runningApplyAll ? (
                                    <>
                                        <Loader2 size={11} className="animate-spin" />
                                        Đang áp dụng...
                                    </>
                                ) : (
                                    <>
                                        <Wrench size={11} />
                                        Fix tất cả ({actionableChecks.length})
                                    </>
                                )}
                            </ActionButton>
                        )}

                        {onRecheck && (
                            <ActionButton
                                variant="ghost"
                                size="sm"
                                onClick={runRecheck}
                                disabled={runningRecheck || runningApplyAll}
                            >
                                {runningRecheck ? (
                                    <>
                                        <Loader2 size={11} className="animate-spin" />
                                        Đang kiểm tra...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw size={11} />
                                        Recheck
                                    </>
                                )}
                            </ActionButton>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                        <ActionButton variant="ghost" size="sm" onClick={onClose}>
                            Đóng
                        </ActionButton>

                        <ActionButton
                            variant="primary"
                            size="sm"
                            onClick={handleContinue}
                            disabled={continueDisabled}
                        >
                            {runningContinue ? (
                                <>
                                    <Loader2 size={11} className="animate-spin" />
                                    Đang chạy...
                                </>
                            ) : (
                                <>
                                    <PlayCircle size={11} />
                                    {continueLabel}
                                </>
                            )}
                        </ActionButton>
                    </div>
                </div>
            </div>
        </Modal>
    )
}
