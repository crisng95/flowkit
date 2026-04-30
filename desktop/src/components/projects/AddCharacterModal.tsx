import { useState } from 'react'
import Modal from '../ui/Modal'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { fetchAPI } from '../../api/client'
import type { EntityType } from '../../types'

const ENTITY_TYPES: EntityType[] = ['character', 'location', 'creature', 'visual_asset', 'generic_troop', 'faction']

const ENTITY_LABELS: Record<EntityType, string> = {
    character: 'Nhân vật',
    location: 'Địa điểm',
    creature: 'Sinh vật',
    visual_asset: 'Tài sản hình ảnh',
    generic_troop: 'Quân đội',
    faction: 'Phe phái',
}

interface AddCharacterModalProps {
    projectId: string
    onClose: () => void
    onCreated: () => void
}

export default function AddCharacterModal({ projectId, onClose, onCreated }: AddCharacterModalProps) {
    const [name, setName] = useState('')
    const [entityType, setEntityType] = useState<EntityType>('character')
    const [description, setDescription] = useState('')
    const [imagePrompt, setImagePrompt] = useState('')
    const [voiceDescription, setVoiceDescription] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const submit = async () => {
        if (!name.trim()) { setError('Tên thực thể là bắt buộc'); return }
        setError('')
        setLoading(true)
        try {
            const char = await fetchAPI<{ id: string }>('/api/characters', {
                method: 'POST',
                body: JSON.stringify({
                    name: name.trim(), entity_type: entityType, description, image_prompt: imagePrompt, voice_description: voiceDescription,
                }),
            })
            await fetchAPI(`/api/projects/${projectId}/characters/${char.id}`, { method: 'POST' })
            onCreated()
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Lỗi tạo thực thể')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Thêm thực thể" onClose={onClose} width={520}>
            <div className="flex flex-col gap-3.5">
                <div className="grid grid-cols-2 gap-3">
                    <Field label="Tên *">
                        <Input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="Tướng Nguyễn" onKeyDown={e => e.key === 'Enter' && submit()} />
                    </Field>
                    <Field label="Loại thực thể">
                        <Select value={entityType} onValueChange={v => setEntityType(v as EntityType)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {ENTITY_TYPES.map(t => <SelectItem key={t} value={t}>{ENTITY_LABELS[t]}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </Field>
                </div>

                <Field label="Mô tả">
                    <Textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} placeholder="Nhân vật là ai? Vai trò, tính cách, bối cảnh..." className="resize-none" />
                </Field>

                <Field label="Prompt ảnh">
                    <Textarea value={imagePrompt} onChange={e => setImagePrompt(e.target.value)} rows={3} placeholder="Mô tả ngoại hình (chỉ ngoại hình, không có hành động). Để trống để tự động tạo từ mô tả." className="resize-none" />
                </Field>

                <Field label="Giọng nói (TTS)">
                    <Input value={voiceDescription} onChange={e => setVoiceDescription(e.target.value)} placeholder="VD: giọng nam trầm, uy quyền, trung niên" />
                </Field>

                {error && <p className="text-xs text-[hsl(var(--destructive))]">{error}</p>}

                <div className="flex justify-end gap-2 pt-1">
                    <Button variant="ghost" onClick={onClose}>Hủy</Button>
                    <Button onClick={submit} disabled={loading}>{loading ? 'Đang tạo...' : 'Thêm thực thể'}</Button>
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
