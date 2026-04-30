import { useMemo, useState } from 'react'
import Modal from '../ui/Modal'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { cn } from '../../lib/utils'
import { fetchAPI } from '../../api/client'
import type { Character, Scene } from '../../types'

interface AddSceneModalProps {
    videoId: string
    scenes: Scene[]
    characters: Character[]
    defaultAfterOrder?: number
    onClose: () => void
    onCreated: () => void
}

type Mode = 'append' | 'insert'

function parseChars(raw: string[] | string | null): string[] {
    if (!raw) return []
    if (Array.isArray(raw)) return raw
    try { const p = JSON.parse(raw); return Array.isArray(p) ? p : [] } catch { return [] }
}

export default function AddSceneModal({ videoId, scenes, characters, defaultAfterOrder, onClose, onCreated }: AddSceneModalProps) {
    const sortedScenes = useMemo(() => [...scenes].sort((a, b) => a.display_order - b.display_order), [scenes])
    const [mode, setMode] = useState<Mode>('append')
    const [afterOrder, setAfterOrder] = useState<number>(defaultAfterOrder ?? Math.max(0, sortedScenes.length - 1))
    const [prompt, setPrompt] = useState('')
    const [videoPrompt, setVideoPrompt] = useState('')
    const [narratorText, setNarratorText] = useState('')
    const [selectedChars, setSelectedChars] = useState<string[]>([])
    const [loading, setLoading] = useState(false)

    const parentScene = sortedScenes.find(s => s.display_order === afterOrder) ?? null

    const toggleChar = (name: string) =>
        setSelectedChars(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name])

    const submit = async () => {
        const isInsert = mode === 'insert' && parentScene
        const fallbackParentChars = isInsert ? parseChars(parentScene.character_names as any) : []
        const charNames = selectedChars.length > 0 ? selectedChars : fallbackParentChars
        setLoading(true)
        try {
            await fetchAPI('/api/scenes', {
                method: 'POST',
                body: JSON.stringify({
                    video_id: videoId,
                    display_order: isInsert ? parentScene.display_order + 1 : sortedScenes.length,
                    chain_type: isInsert ? 'INSERT' : 'ROOT',
                    parent_scene_id: isInsert ? parentScene.id : null,
                    source: 'user',
                    prompt: prompt || '',
                    video_prompt: videoPrompt || null,
                    narrator_text: narratorText || null,
                    character_names: charNames.length > 0 ? charNames : null,
                }),
            })
            onCreated()
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Thêm phân cảnh" onClose={onClose} width={620}>
            <div className="flex flex-col gap-3.5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <Field label="Chế độ">
                        <Select value={mode} onValueChange={v => setMode(v as Mode)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="append">Thêm cuối video</SelectItem>
                                <SelectItem value="insert">Chèn vào giữa chain</SelectItem>
                            </SelectContent>
                        </Select>
                    </Field>

                    {mode === 'insert' && (
                        <Field label="Chèn sau cảnh">
                            <Select value={String(afterOrder)} onValueChange={v => setAfterOrder(Number(v))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {sortedScenes.map(s => (
                                        <SelectItem key={s.id} value={String(s.display_order)}>
                                            #{s.display_order + 1} · {(s.prompt ?? s.video_prompt ?? 'Chưa có prompt').slice(0, 48)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </Field>
                    )}
                </div>

                {mode === 'insert' && parentScene && (
                    <div className="text-xs rounded-md px-3 py-2 bg-blue-50 border border-blue-200 text-blue-700">
                        Cảnh sẽ được tạo dạng <strong>INSERT</strong> sau cảnh #{parentScene.display_order + 1}. Các cảnh tiếp theo sẽ tự dịch chuyển.
                    </div>
                )}

                <Field label="Image Prompt">
                    <Textarea autoFocus value={prompt} onChange={e => setPrompt(e.target.value)} rows={2}
                        placeholder="Mô tả cảnh quay. Nhân vật được tham chiếu qua ảnh ref — chỉ mô tả HÀNH ĐỘNG và KHÔNG GIAN."
                        className="resize-none" />
                </Field>

                <Field label="Video Prompt">
                    <Textarea value={videoPrompt} onChange={e => setVideoPrompt(e.target.value)} rows={3}
                        placeholder="0-3s: [hành động camera]. 3-6s: [hành động tiếp]. 6-8s: [kết thúc]."
                        className="resize-none" />
                </Field>

                <Field label="Narrator (TTS)">
                    <Textarea value={narratorText} onChange={e => setNarratorText(e.target.value)} rows={2}
                        placeholder="Lời bình cho cảnh này..." className="resize-none" />
                </Field>

                {characters.length > 0 && (
                    <Field label="Nhân vật trong cảnh">
                        <div className="flex flex-wrap gap-1.5">
                            {characters.map(c => (
                                <button key={c.id} type="button" onClick={() => toggleChar(c.name)}
                                    className={cn(
                                        'px-2.5 py-1 rounded-md text-xs font-medium border transition-colors',
                                        selectedChars.includes(c.name)
                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]'
                                            : 'bg-transparent text-[hsl(var(--foreground))] border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))]'
                                    )}
                                >
                                    {c.name}
                                </button>
                            ))}
                        </div>
                    </Field>
                )}

                <div className="flex justify-end gap-2 pt-1">
                    <Button variant="ghost" onClick={onClose}>Hủy</Button>
                    <Button onClick={submit} disabled={loading}>{loading ? 'Đang tạo...' : 'Thêm phân cảnh'}</Button>
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
