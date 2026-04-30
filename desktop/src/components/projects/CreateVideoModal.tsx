import { useState } from 'react'
import Modal from '../ui/Modal'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { Label } from '../ui/label'
import { fetchAPI } from '../../api/client'

interface CreateVideoModalProps {
    projectId: string
    displayOrder: number
    defaultOrientation?: string
    onClose: () => void
    onCreated: (videoId: string) => void
}

export default function CreateVideoModal({ projectId, displayOrder, defaultOrientation = 'VERTICAL', onClose, onCreated }: CreateVideoModalProps) {
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const submit = async () => {
        if (!title.trim()) { setError('Tiêu đề là bắt buộc'); return }
        setError('')
        setLoading(true)
        try {
            const video = await fetchAPI<{ id: string }>('/api/videos', {
                method: 'POST',
                body: JSON.stringify({ project_id: projectId, title: title.trim(), description, display_order: displayOrder, orientation: defaultOrientation }),
            })
            onCreated(video.id)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Lỗi tạo video')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Video mới" onClose={onClose}>
            <div className="flex flex-col gap-3.5">
                <div className="flex flex-col gap-1.5">
                    <Label className="text-[hsl(var(--muted-foreground))]">Tiêu đề *</Label>
                    <Input autoFocus value={title} onChange={e => setTitle(e.target.value)} placeholder="Tập 1 — Khởi đầu" onKeyDown={e => e.key === 'Enter' && submit()} />
                </div>
                <div className="flex flex-col gap-1.5">
                    <Label className="text-[hsl(var(--muted-foreground))]">Mô tả</Label>
                    <Textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="Nội dung diễn ra trong video này?" className="resize-none" />
                </div>
                {error && <p className="text-xs text-[hsl(var(--destructive))]">{error}</p>}
                <div className="flex justify-end gap-2 pt-1">
                    <Button variant="ghost" onClick={onClose}>Hủy</Button>
                    <Button onClick={submit} disabled={loading}>{loading ? 'Đang tạo...' : 'Tạo video'}</Button>
                </div>
            </div>
        </Modal>
    )
}
