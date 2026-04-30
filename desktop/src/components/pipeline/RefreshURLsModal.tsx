/**
 * RefreshURLsModal
 * Refreshes expired Google Storage URLs for all scenes in a video.
 * Triggers a re-fetch of each scene to get fresh signed URLs.
 * Corresponds to CLI skill: fk:refresh-urls
 */
import { useState } from 'react'
import { RefreshCw, CheckCircle } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface Props {
    videoId: string
    projectId: string
    onClose: () => void
}

export default function RefreshURLsModal({ videoId: _videoId, projectId, onClose }: Props) {
    const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
    const [count, setCount] = useState(0)
    const [charCount, setCharCount] = useState(0)
    const [note, setNote] = useState('')
    const [errors, setErrors] = useState<string[]>([])
    const [error, setError] = useState('')

    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

    const isExtensionDisconnectedError = (msg: string) =>
        msg.includes('Extension not connected') || msg.includes('API 503')

    const checkExtensionConnected = async (): Promise<boolean> => {
        try {
            if (window.electron?.getHealth) {
                const health = await window.electron.getHealth()
                return !!health?.extension_connected
            }
            const res = await fetch('http://127.0.0.1:8100/health')
            if (!res.ok) return false
            const health = await res.json()
            return !!health?.extension_connected
        } catch {
            return false
        }
    }

    const reconnectExtension = async (): Promise<boolean> => {
        try {
            await window.electron?.openFlowTab?.()
            await window.electron?.reconnectExtension?.()
        } catch {
            // no-op
        }

        for (let i = 0; i < 10; i += 1) {
            // eslint-disable-next-line no-await-in-loop
            await sleep(600)
            // eslint-disable-next-line no-await-in-loop
            const ok = await checkExtensionConnected()
            if (ok) return true
        }
        return false
    }

    const run = async () => {
        setStatus('running')
        setError('')
        setNote('')
        setErrors([])
        setCharCount(0)

        const doRefresh = () => fetchAPI<{
            refreshed?: number
            characters_refreshed?: number
            note?: string
            errors?: string[]
        }>(`/api/flow/refresh-urls/${projectId}`, {
            method: 'POST',
        })

        try {
            let result: {
                refreshed?: number
                characters_refreshed?: number
                note?: string
                errors?: string[]
            }
            try {
                result = await doRefresh()
            } catch (err: any) {
                const msg = err?.message ?? ''
                if (!isExtensionDisconnectedError(msg)) throw err

                setNote('Extension chưa kết nối. Đang tự động mở Flow và kết nối lại...')
                const reconnected = await reconnectExtension()
                if (!reconnected) {
                    throw new Error('Extension vẫn chưa kết nối. Vui lòng mở cửa sổ Google Flow và bật extension, rồi thử lại.')
                }
                result = await doRefresh()
            }

            // Auth expired path: warm token + retry once automatically.
            if ((result.note ?? '').includes('AUTH_EXPIRED')) {
                setNote('Token Flow đã hết hạn. Đang mở Flow để làm mới token...')
                await reconnectExtension()
                try {
                    await fetchAPI('/api/flow/credits')
                } catch {
                    // ignore; refresh call below is source of truth
                }
                result = await doRefresh()
            }

            setCount(result.refreshed ?? 0)
            setCharCount(result.characters_refreshed ?? 0)
            setNote(result.note ?? '')
            setErrors(result.errors ?? [])
            setStatus('done')
        } catch (err: any) {
            setStatus('error')
            setError(err.message)
        }
    }

    return (
        <Modal title="Làm Mới URL Hết Hạn" onClose={onClose} width={440}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    URL ký số từ Google Storage sẽ hết hạn sau 7 ngày. Nếu ảnh hoặc video bị lỗi hiển thị,
                    hãy làm mới để lấy URL mới.
                </div>

                {status === 'idle' && (
                    <ActionButton variant="primary" onClick={run}>
                        <RefreshCw size={12} /> Làm Mới Tất Cả URL
                    </ActionButton>
                )}

                {status === 'running' && (
                    <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                        <RefreshCw size={12} className="animate-spin" />
                        Đang làm mới... {count} cảnh đã xong
                    </div>
                )}

                {status === 'done' && (
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--green)' }}>
                            <CheckCircle size={14} />
                            ✓ Đã làm mới {count} cảnh, {charCount} ảnh tham chiếu nhân vật.
                        </div>
                        {note && (
                            <div className="text-xs p-2 rounded border" style={{ background: 'rgba(251,191,36,0.12)', color: '#92400e', borderColor: 'rgba(251,191,36,0.4)' }}>
                                {note}
                            </div>
                        )}
                        {errors.length > 0 && (
                            <div className="text-xs p-2 rounded border" style={{ background: 'rgba(239,68,68,0.08)', color: '#b91c1c', borderColor: 'rgba(239,68,68,0.28)' }}>
                                <div className="font-semibold mb-1">Một số media chưa refresh được:</div>
                                <ul className="list-disc pl-4">
                                    {errors.map((item, idx) => <li key={idx}>{item}</li>)}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {status === 'error' && (
                    <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>
                        {error}
                    </div>
                )}

                <div className="flex justify-end">
                    <ActionButton variant="ghost" onClick={onClose}>Đóng</ActionButton>
                </div>
            </div>
        </Modal>
    )
}
