/**
 * GenNarratorModal
 * Uses AI (configurable provider) to write narrator_text for all scenes
 * from the video's story/scene prompts, then PATCHes each scene.
 * Corresponds to CLI skill: fk:gen-narrator
 */
import { useState } from 'react'
import { FileText, RefreshCw, CheckCircle } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'
import { aiGenerate, loadGeneralSettings, type ProviderType } from '../../api/ai-service'

const PROVIDERS: { id: ProviderType; label: string }[] = [
    { id: 'gemini', label: 'Gemini' },
    { id: 'claude', label: 'Claude' },
    { id: 'openai', label: 'OpenAI' },
]

interface Scene {
    id: string
    display_order: number
    prompt: string | null
    video_prompt: string | null
    narrator_text: string | null
    character_names: string[] | null
}

interface SceneResult {
    scene: Scene
    status: 'pending' | 'generating' | 'done' | 'skipped' | 'error'
    text: string
    error?: string
}

interface Props {
    videoId: string
    projectId: string
    onClose: () => void
}

const SYSTEM_PROMPT = `You are a documentary narrator writer.
Generate compelling, concise narrator text for a scene.
Respond with a JSON object: {"narrator_text": "..."}
Keep it to 1-3 short sentences max.
Never describe the visual — narrate the meaning, context, or emotion.`

async function generateNarratorText(
    scene: Scene,
    language: string,
    projectStory: string,
    videoStory: string,
    provider: ProviderType
): Promise<string> {
    const lang = language === 'vi'
        ? 'Vietnamese'
        : language === 'en'
            ? 'English'
            : language === 'es'
                ? 'Spanish'
                : language
    const characterText = scene.character_names?.join(', ') || 'none'
    const prompt = `Write narrator text in ${lang} for this documentary scene.

Scene #${scene.display_order + 1}
Image prompt: ${scene.prompt ?? '(none)'}
Video motion: ${scene.video_prompt ?? '(none)'}
Characters: ${characterText}

Project storyline context (first 600 chars): ${projectStory.slice(0, 600) || '(none)'}
Episode/video context (first 500 chars): ${videoStory.slice(0, 500) || '(none)'}

Return JSON: {"narrator_text": "Your narrator text here"}`

    const result = await aiGenerate<{ narrator_text: string }>(prompt, SYSTEM_PROMPT, provider)
    return result.narrator_text ?? ''
}

export default function GenNarratorModal({ videoId, projectId, onClose }: Props) {
    const defaults = loadGeneralSettings()
    const [provider, setProvider] = useState<ProviderType>(defaults.defaultProvider)
    const [language, setLanguage] = useState(defaults.defaultLanguage)
    const [forceOverwrite, setForceOverwrite] = useState(false)
    const [results, setResults] = useState<SceneResult[]>([])
    const [running, setRunning] = useState(false)
    const run = async () => {
        setRunning(true)
        try {
            const [scenes, video, project] = await Promise.all([
                fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`),
                fetchAPI<any>(`/api/videos/${videoId}`),
                fetchAPI<any>(`/api/projects/${projectId}`),
            ])
            const projectStory = ((project?.story ?? project?.description ?? '') as string).trim()
            const videoStory = (video?.description ?? '').trim()

            const initial: SceneResult[] = scenes.map(s => ({
                scene: s,
                status: 'pending',
                text: s.narrator_text ?? '',
            }))
            setResults(initial)

            for (let i = 0; i < scenes.length; i++) {
                const scene = scenes[i]
                // Skip if already has text and not force
                const isInterview = (scene.character_names ?? []).some(name => name.toLowerCase().includes('interview'))
                if (isInterview) {
                    setResults(prev => prev.map((r, idx) => idx === i ? { ...r, status: 'skipped', text: '(interview scene — skipped)' } : r))
                    continue
                }
                if (scene.narrator_text && !forceOverwrite) {
                    setResults(prev => prev.map((r, idx) => idx === i ? { ...r, status: 'skipped', text: scene.narrator_text! } : r))
                    continue
                }

                setResults(prev => prev.map((r, idx) => idx === i ? { ...r, status: 'generating' } : r))
                try {
                    const text = await generateNarratorText(scene, language, projectStory, videoStory, provider)
                    await patchAPI(`/api/scenes/${scene.id}`, { narrator_text: text })
                    setResults(prev => prev.map((r, idx) => idx === i ? { ...r, status: 'done', text } : r))
                } catch (err: any) {
                    setResults(prev => prev.map((r, idx) => idx === i ? { ...r, status: 'error', error: err.message } : r))
                }
            }
        } finally { setRunning(false) }
    }

    const done = results.filter(r => r.status === 'done').length
    const skipped = results.filter(r => r.status === 'skipped').length
    const errors = results.filter(r => r.status === 'error').length

    return (
        <Modal title="Generate Narrator Text (AI)" onClose={onClose} width={600}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    AI writes <code>narrator_text</code> for each scene from scene prompts + story context.
                    Interview scenes are automatically skipped.
                </div>

                {/* Config */}
                <div className="flex gap-3 flex-wrap">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Provider</label>
                        <select value={provider} onChange={e => setProvider(e.target.value as ProviderType)} className="input">
                            {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                        </select>
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Language</label>
                        <select value={language} onChange={e => setLanguage(e.target.value)} className="input">
                            <option value="vi">Vietnamese</option>
                            <option value="en">English</option>
                            <option value="es">Spanish</option>
                            <option value="zh">Chinese</option>
                            <option value="ja">Japanese</option>
                        </select>
                    </div>
                    <div className="flex flex-col gap-1 justify-end">
                        <label className="flex items-center gap-2 text-xs cursor-pointer">
                            <input type="checkbox" checked={forceOverwrite} onChange={e => setForceOverwrite(e.target.checked)} />
                            Overwrite existing narrator text
                        </label>
                    </div>
                </div>

                {results.length === 0 && (
                    <ActionButton variant="primary" onClick={run} disabled={running}>
                        <FileText size={13} /> Generate All Narrator Text
                    </ActionButton>
                )}

                {/* Progress summary */}
                {results.length > 0 && (
                    <div className="flex items-center gap-3 text-xs">
                        <span style={{ color: 'var(--green)' }}>✓ {done} done</span>
                        <span style={{ color: 'var(--muted)' }}>⏭ {skipped} skipped</span>
                        {errors > 0 && <span style={{ color: 'var(--red)' }}>✗ {errors} error</span>}
                        {running && <span style={{ color: 'var(--accent)' }}>⏳ generating...</span>}
                    </div>
                )}

                {/* Scene results */}
                {results.length > 0 && (
                    <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto">
                        {results.map((r, i) => (
                            <div key={r.scene.id} className="flex gap-2 rounded px-3 py-2"
                                style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                                <span className="text-xs font-bold w-5 flex-shrink-0" style={{ color: 'var(--muted)' }}>#{i + 1}</span>
                                <div className="flex-1 flex flex-col gap-0.5">
                                    {r.status === 'generating' && (
                                        <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--accent)' }}>
                                            <RefreshCw size={10} className="animate-spin" /> Generating...
                                        </div>
                                    )}
                                    {r.status === 'done' && (
                                        <>
                                            <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--green)' }}>
                                                <CheckCircle size={10} /> Done
                                            </div>
                                            <div className="text-xs" style={{ color: 'var(--text)' }}>{r.text}</div>
                                        </>
                                    )}
                                    {r.status === 'skipped' && (
                                        <div className="text-xs" style={{ color: 'var(--muted)' }}>⏭ {r.text || 'Skipped (has text)'}</div>
                                    )}
                                    {r.status === 'error' && (
                                        <div className="text-xs" style={{ color: 'var(--red)' }}>✗ {r.error}</div>
                                    )}
                                    {r.status === 'pending' && (
                                        <div className="text-xs" style={{ color: 'var(--muted)' }}>Waiting...</div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {!running && results.length > 0 && (
                    <div className="flex justify-between items-center pt-2">
                        <ActionButton variant="ghost" size="sm" onClick={run}>
                            <RefreshCw size={11} /> Re-run
                        </ActionButton>
                        <ActionButton variant="primary" onClick={onClose}>Done</ActionButton>
                    </div>
                )}
            </div>
        </Modal>
    )
}
