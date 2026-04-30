import { useState } from 'react'
import { Download, FolderOpen } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'
import { loadGeneralSettings } from '../../api/ai-service'

interface Props {
    videoId: string
    projectId: string
    defaultOrientation?: string
    onClose: () => void
}

const ORIENTATIONS = [
    { id: 'VERTICAL', label: '📱 Dọc (9:16) — Shorts/Reels' },
    { id: 'HORIZONTAL', label: '🖥 Ngang (16:9) — YouTube' },
]

export default function ExportModal({ videoId, projectId, defaultOrientation = 'VERTICAL', onClose }: Props) {
    const defaults = loadGeneralSettings()
    const [orientation, setOrientation] = useState(defaultOrientation)
    const [withNarrator, setWithNarrator] = useState(true)
    const [withMusic, setWithMusic] = useState(false)
    const [fitNarrator, setFitNarrator] = useState(false)
    const [narratorBuffer, setNarratorBuffer] = useState(0.5)
    const [status, setStatus] = useState<'idle' | 'exporting' | 'done' | 'error'>('idle')
    const [outputPath, setOutputPath] = useState('')
    const [exportDir, setExportDir] = useState('')
    const [exportedImages, setExportedImages] = useState(0)
    const [exportedVideos, setExportedVideos] = useState(0)
    const [error, setError] = useState('')

    const exportVideo = async () => {
        setStatus('exporting'); setError('')
        try {
            const r = await fetchAPI<{
                output_path?: string
                export_dir?: string | null
                exported_images?: number
                exported_videos?: number
            }>(`/api/videos/${videoId}/concat`, {
                method: 'POST',
                body: JSON.stringify({
                    project_id: projectId,
                    orientation,
                    with_narrator: withNarrator,
                    with_music: withMusic,
                    fit_narrator: fitNarrator,
                    narrator_buffer: narratorBuffer,
                    export_root_dir: defaults.exportRootDir || null,
                    export_assets: true,
                }),
            })
            setOutputPath(r.output_path ?? '')
            setExportDir(r.export_dir ?? '')
            setExportedImages(r.exported_images ?? 0)
            setExportedVideos(r.exported_videos ?? 0)
            setStatus('done')
        } catch (e: any) {
            setStatus('error')
            setError(e.message)
        }
    }

    const openFolder = async () => {
        const target = exportDir || outputPath
        if (!target) return
        if (window.electron?.openPath) {
            const result = await window.electron.openPath(target)
            if (!result.ok && result.error) alert(result.error)
            return
        }
        alert(`Đã xuất file tại:\n${target}`)
    }

    return (
        <Modal title="Xuất / Nối Video" onClose={onClose} width={480}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Nối toàn bộ video cảnh thành file xuất cuối bằng FFmpeg.
                    Cần tạo video cho các cảnh trước khi xuất.
                </div>
                <div className="text-xs rounded p-2" style={{ background: 'var(--card)', color: 'var(--muted)' }}>
                    Export folder: {defaults.exportRootDir ? <span className="font-mono">{defaults.exportRootDir}</span> : 'chưa cấu hình trong Cài đặt → Chung'}
                </div>

                {/* Orientation */}
                <div className="flex flex-col gap-1.5">
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Tỉ lệ</div>
                    {ORIENTATIONS.map(o => (
                        <label key={o.id} className="flex items-center gap-2 cursor-pointer text-xs p-2 rounded" style={{ background: orientation === o.id ? 'var(--card)' : 'transparent', border: orientation === o.id ? '1px solid var(--border)' : '1px solid transparent' }}>
                            <input type="radio" name="orientation" value={o.id} checked={orientation === o.id} onChange={() => setOrientation(o.id)} />
                            {o.label}
                        </label>
                    ))}
                </div>

                {/* Options */}
                <div className="flex flex-col gap-2">
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Tùy chọn</div>
                    <label className="flex items-center gap-2 cursor-pointer text-xs">
                        <input type="checkbox" checked={withNarrator} onChange={e => setWithNarrator(e.target.checked)} />
                        Dùng TTS narration (ghi đè audio gốc từ Veo nếu có file TTS)
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs">
                        <input type="checkbox" checked={fitNarrator} onChange={e => setFitNarrator(e.target.checked)} />
                        Khớp từng cảnh theo độ dài narrator (parity CLI)
                    </label>
                    {fitNarrator && (
                        <div className="flex items-center gap-2 text-xs">
                            <span style={{ color: 'var(--muted)' }}>Đệm narrator (giây)</span>
                            <input
                                type="number"
                                step={0.1}
                                min={0}
                                value={narratorBuffer}
                                onChange={e => setNarratorBuffer(Math.max(0, Number(e.target.value) || 0))}
                                className="input"
                                style={{ maxWidth: 100 }}
                            />
                        </div>
                    )}
                    <label className="flex items-center gap-2 cursor-pointer text-xs">
                        <input type="checkbox" checked={withMusic} onChange={e => setWithMusic(e.target.checked)} />
                        Gồm nhạc nền
                    </label>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {status === 'exporting' && (
                    <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                        <div className="w-4 h-4 rounded-full border border-current animate-spin" style={{ borderTopColor: 'transparent' }} />
                        Đang nối video... có thể mất vài phút
                    </div>
                )}

                {status === 'done' && (
                    <div className="flex flex-col gap-2 text-xs p-3 rounded" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}>
                        ✓ Xuất file thành công!
                        {outputPath && <span className="font-mono" style={{ color: 'var(--muted)', wordBreak: 'break-all' }}>{outputPath}</span>}
                        {exportDir && (
                            <>
                                <span className="font-mono" style={{ color: 'var(--muted)', wordBreak: 'break-all' }}>
                                    Tài nguyên: {exportDir}
                                </span>
                                <span style={{ color: 'var(--muted)' }}>
                                    Đã xuất {exportedImages} ảnh · {exportedVideos} video cảnh
                                </span>
                            </>
                        )}
                        <ActionButton variant="ghost" size="sm" onClick={openFolder}>
                            <FolderOpen size={11} /> Mở thư mục
                        </ActionButton>
                    </div>
                )}

                <div className="flex justify-end gap-2 pt-2">
                    <ActionButton variant="ghost" onClick={onClose}>Hủy</ActionButton>
                    <ActionButton variant="primary" onClick={exportVideo} disabled={status === 'exporting'}>
                        <Download size={12} /> Xuất video
                    </ActionButton>
                </div>
            </div>
        </Modal>
    )
}
