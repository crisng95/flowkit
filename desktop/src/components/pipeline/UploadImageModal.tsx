import { useEffect, useMemo, useState } from 'react'
import { Upload, Link2, User, Image as ImageIcon } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'
import type { Character, Scene } from '../../types'
import { normalizeOrientation } from '../../lib/orientation'

interface Props {
    projectId: string
    videoId: string
    orientation: string
    onClose: () => void
}

type TargetMode = 'none' | 'character' | 'scene_image' | 'new_character'
const ENTITY_TYPES = ['character', 'location', 'creature', 'visual_asset', 'generic_troop', 'faction'] as const

export default function UploadImageModal({ projectId, videoId, orientation, onClose }: Props) {
    const [characters, setCharacters] = useState<Character[]>([])
    const [scenes, setScenes] = useState<Scene[]>([])

    const [filePath, setFilePath] = useState('')
    const [fileName, setFileName] = useState('')
    const [targetMode, setTargetMode] = useState<TargetMode>('none')
    const [characterId, setCharacterId] = useState('')
    const [sceneId, setSceneId] = useState('')
    const [newName, setNewName] = useState('')
    const [newEntityType, setNewEntityType] = useState<typeof ENTITY_TYPES[number]>('character')
    const [newDescription, setNewDescription] = useState('')

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [result, setResult] = useState<{ media_id: string; url?: string | null } | null>(null)

    const ori = normalizeOrientation(orientation)

    useEffect(() => {
        Promise.all([
            fetchAPI<Character[]>(`/api/projects/${projectId}/characters`).catch(() => []),
            fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`).catch(() => []),
        ]).then(([chars, ss]) => {
            setCharacters(chars)
            setScenes(ss.sort((a, b) => a.display_order - b.display_order))
            if (!characterId && chars[0]) setCharacterId(chars[0].id)
            if (!sceneId && ss[0]) setSceneId(ss[0].id)
        })
    }, [projectId, videoId, characterId, sceneId])

    const chosenCharacter = useMemo(
        () => characters.find(c => c.id === characterId) ?? null,
        [characters, characterId],
    )

    const chooseFile = async () => {
        const picked = await window.electron?.pickFile?.('image')
            ?? await window.electron?.pickImageFile?.()
        if (!picked) return
        setFilePath(picked)
        setFileName(picked.split(/[\\/]/).pop() || 'image.png')
    }

    const upload = async () => {
        if (!filePath.trim()) return
        setLoading(true)
        setError('')
        setResult(null)

        try {
            const uploaded = await fetchAPI<{ media_id?: string; url?: string | null }>('/api/flow/upload-image', {
                method: 'POST',
                body: JSON.stringify({
                    file_path: filePath.trim(),
                    project_id: projectId,
                    file_name: fileName.trim() || 'image.png',
                }),
            })
            if (!uploaded.media_id) throw new Error('Upload thành công nhưng không có media_id')

            if (targetMode === 'character' && characterId) {
                await patchAPI(`/api/characters/${characterId}`, {
                    media_id: uploaded.media_id,
                    reference_image_url: uploaded.url ?? chosenCharacter?.reference_image_url ?? null,
                })
            }

            if (targetMode === 'scene_image' && sceneId) {
                const payload = ori === 'HORIZONTAL'
                    ? {
                        horizontal_image_media_id: uploaded.media_id,
                        horizontal_image_url: uploaded.url ?? null,
                        horizontal_image_status: 'COMPLETED',
                    }
                    : {
                        vertical_image_media_id: uploaded.media_id,
                        vertical_image_url: uploaded.url ?? null,
                        vertical_image_status: 'COMPLETED',
                    }
                await patchAPI(`/api/scenes/${sceneId}`, payload)
            }

            if (targetMode === 'new_character') {
                const created = await fetchAPI<Character>('/api/characters', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: newName.trim() || fileName.replace(/\.[^.]+$/, ''),
                        entity_type: newEntityType,
                        description: newDescription.trim() || null,
                        media_id: uploaded.media_id,
                        reference_image_url: uploaded.url ?? null,
                    }),
                })
                await fetchAPI(`/api/projects/${projectId}/characters/${created.id}`, { method: 'POST' })
                setCharacters(prev => [...prev, created])
                setCharacterId(created.id)
            }

            setResult({ media_id: uploaded.media_id, url: uploaded.url ?? null })
        } catch (e: any) {
            setError(e.message ?? 'Upload thất bại')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal title="Upload Ảnh (fk:upload-image)" onClose={onClose} width={620}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Upload ảnh local lên Google Flow để lấy <code>media_id</code>. Có thể bind ngay vào entity hoặc scene image.
                </div>

                <div className="flex gap-2">
                    <input
                        value={filePath}
                        onChange={e => setFilePath(e.target.value)}
                        placeholder="/absolute/path/to/image.png"
                        className="input"
                    />
                    <ActionButton variant="secondary" size="sm" onClick={chooseFile}>
                        <Upload size={11} /> Chọn file
                    </ActionButton>
                </div>

                <input
                    value={fileName}
                    onChange={e => setFileName(e.target.value)}
                    placeholder="Tên file trên Flow (tùy chọn)"
                    className="input"
                />

                <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Đích gán (tùy chọn)</div>
                    <select value={targetMode} onChange={e => setTargetMode(e.target.value as TargetMode)} className="input">
                        <option value="none">Không gán (chỉ upload)</option>
                        <option value="character">Ảnh tham chiếu nhân vật</option>
                        <option value="new_character">Tạo thực thể mới từ ảnh này</option>
                        <option value="scene_image">Ảnh cảnh ({ori})</option>
                    </select>

                    {targetMode === 'character' && (
                        <div className="flex items-center gap-2">
                            <User size={12} style={{ color: 'var(--muted)' }} />
                            <select value={characterId} onChange={e => setCharacterId(e.target.value)} className="input">
                                {characters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                        </div>
                    )}

                    {targetMode === 'scene_image' && (
                        <div className="flex items-center gap-2">
                            <ImageIcon size={12} style={{ color: 'var(--muted)' }} />
                            <select value={sceneId} onChange={e => setSceneId(e.target.value)} className="input">
                                {scenes.map(s => (
                                    <option key={s.id} value={s.id}>
                                        #{s.display_order + 1} · {(s.prompt ?? s.video_prompt ?? 'Không có prompt').slice(0, 60)}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {targetMode === 'new_character' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <input
                                value={newName}
                                onChange={e => setNewName(e.target.value)}
                                placeholder="Tên thực thể"
                                className="input"
                            />
                            <select value={newEntityType} onChange={e => setNewEntityType(e.target.value as typeof ENTITY_TYPES[number])} className="input">
                                {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <textarea
                                rows={2}
                                value={newDescription}
                                onChange={e => setNewDescription(e.target.value)}
                                placeholder="Mô tả tùy chọn (chỉ ngoại hình)"
                                className="input resize-none md:col-span-2"
                            />
                        </div>
                    )}
                </div>

                {error && (
                    <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>
                        {error}
                    </div>
                )}

                {result && (
                    <div className="text-xs p-3 rounded flex flex-col gap-1" style={{ background: 'rgba(34,197,94,0.12)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.25)' }}>
                        <div>✓ Upload thành công</div>
                        <div><strong>media_id:</strong> {result.media_id}</div>
                        {result.url && (
                            <a href={result.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:opacity-80" style={{ color: 'var(--accent)' }}>
                                <Link2 size={11} /> Mở URL ảnh đã upload
                            </a>
                        )}
                    </div>
                )}

                <div className="flex justify-end gap-2 pt-2">
                    <ActionButton variant="ghost" onClick={onClose}>Đóng</ActionButton>
                    <ActionButton variant="primary" onClick={upload} disabled={loading || !filePath.trim()}>
                        <Upload size={12} /> {loading ? 'Đang upload...' : 'Upload'}
                    </ActionButton>
                </div>
            </div>
        </Modal>
    )
}
