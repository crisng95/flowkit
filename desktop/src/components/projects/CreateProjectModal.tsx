import { useState, useEffect } from 'react'
import Modal from '../ui/Modal'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { fetchAPI } from '../../api/client'

interface Material { id: string; name: string }

interface CreateProjectModalProps {
    onClose: () => void
    onCreated: (projectId: string) => void
}

export default function CreateProjectModal({ onClose, onCreated }: CreateProjectModalProps) {
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [material, setMaterial] = useState('realistic')
    const [language, setLanguage] = useState('vi')
    const [orientation, setOrientation] = useState('VERTICAL')
    const [materials, setMaterials] = useState<Material[]>([])
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        fetchAPI<Material[]>('/api/materials').then(setMaterials).catch(() => { })
    }, [])

    const submit = async () => {
        if (!name.trim()) { setError('Tên dự án là bắt buộc'); return }
        setError('')
        setLoading(true)
        try {
            const proj = await fetchAPI<{ id: string }>('/api/projects', {
                method: 'POST',
                body: JSON.stringify({ name: name.trim(), description, material, language, orientation }),
            })
            onCreated(proj.id)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Lỗi tạo dự án')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Dự án mới" onClose={onClose}>
            <div className="flex flex-col gap-3.5">
                <Field label="Tên dự án *">
                    <Input
                        autoFocus
                        value={name}
                        onChange={e => setName(e.target.value)}
                        placeholder="Video của tôi"
                        onKeyDown={e => e.key === 'Enter' && submit()}
                    />
                </Field>

                <Field label="Mô tả">
                    <Textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        rows={2}
                        placeholder="Mô tả ngắn về dự án..."
                        className="min-h-[52px] resize-none"
                    />
                </Field>

                <div className="grid grid-cols-3 gap-3">
                    <Field label="Phong cách">
                        <Select value={material} onValueChange={setMaterial}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {materials.length > 0
                                    ? materials.map(m => <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>)
                                    : <SelectItem value="realistic">Realistic</SelectItem>}
                            </SelectContent>
                        </Select>
                    </Field>

                    <Field label="Tỉ lệ">
                        <Select value={orientation} onValueChange={setOrientation}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="VERTICAL">9:16 — Dọc</SelectItem>
                                <SelectItem value="HORIZONTAL">16:9 — Ngang</SelectItem>
                                <SelectItem value="LANDSCAPE_4_3">4:3 — Cổ điển</SelectItem>
                                <SelectItem value="SQUARE">1:1 — Vuông</SelectItem>
                            </SelectContent>
                        </Select>
                    </Field>

                    <Field label="Ngôn ngữ">
                        <Select value={language} onValueChange={setLanguage}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="vi">Tiếng Việt</SelectItem>
                                <SelectItem value="en">English</SelectItem>
                                <SelectItem value="es">Español</SelectItem>
                                <SelectItem value="zh">Chinese</SelectItem>
                                <SelectItem value="ja">Japanese</SelectItem>
                                <SelectItem value="ko">Korean</SelectItem>
                            </SelectContent>
                        </Select>
                    </Field>
                </div>

                {error && <p className="text-xs text-[hsl(var(--destructive))]">{error}</p>}

                <div className="flex justify-end gap-2 pt-1">
                    <Button variant="ghost" onClick={onClose}>Hủy</Button>
                    <Button onClick={submit} disabled={loading}>
                        {loading ? 'Đang tạo...' : 'Tạo dự án'}
                    </Button>
                </div>
            </div>
        </Modal>
    )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex flex-col gap-1.5">
            <Label className="text-[hsl(var(--muted-foreground))]">{label}</Label>
            {children}
        </div>
    )
}
