/**
 * YouTubeSEOModal
 * AI generates YouTube-optimized title, description, tags, and hashtags
 * from project storyline + selected video episode context.
 * Corresponds to CLI skill: fk:youtube-seo
 */
import { useState } from 'react'
import { Copy, Check, Tv2 } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'
import { aiGenerate, loadGeneralSettings, type ProviderType } from '../../api/ai-service'

interface SEOResult {
    title: string
    description: string
    tags: string[]
    hashtags: string[]
    chapters?: string
}

const PROVIDERS: { id: ProviderType; label: string }[] = [
    { id: 'gemini', label: 'Gemini' },
    { id: 'claude', label: 'Claude' },
    { id: 'openai', label: 'OpenAI' },
]

const SYSTEM_PROMPT = `You are a YouTube SEO expert specializing in documentary content.
Generate highly optimized YouTube metadata to maximize discovery and CTR.
Always respond with valid JSON only.`

interface Props {
    projectId: string
    videoId: string
    onClose: () => void
}

export default function YouTubeSEOModal({ projectId, videoId, onClose }: Props) {
    const defaults = loadGeneralSettings()
    const [provider, setProvider] = useState<ProviderType>(defaults.defaultProvider)
    const [language, setLanguage] = useState(defaults.defaultLanguage)
    const [result, setResult] = useState<SEOResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [copied, setCopied] = useState<string | null>(null)

    const generate = async () => {
        setLoading(true); setError('')
        try {
            const [proj, video, scenes] = await Promise.all([
                fetchAPI<any>(`/api/projects/${projectId}`),
                fetchAPI<any>(`/api/videos/${videoId}`),
                fetchAPI<any[]>(`/api/scenes?video_id=${videoId}`),
            ])

            const lang = language === 'vi'
                ? 'Vietnamese'
                : language === 'en'
                    ? 'English'
                    : language === 'es'
                        ? 'Spanish'
                        : language
            const narratorTexts = scenes.slice(0, 5).map(s => s.narrator_text).filter(Boolean).join(' ')

            const prompt = `Generate YouTube SEO metadata for this documentary video.

Project: ${proj.name}
Project storyline context (excerpt): ${(proj.story || proj.description || '').slice(0, 700)}
Video title: ${video.title}
Video story (excerpt): ${(video.description || '').slice(0, 600)}
Sample narrator text: ${narratorTexts}

Language: ${lang}
Target audience: Documentary viewers, history enthusiasts

Return JSON:
{
  "title": "Compelling YouTube title (max 70 chars, include year/hook). Write in ${lang}.",
  "description": "Full YouTube description (300-500 chars). Include key facts, hook, call to action. Write in ${lang}.",
  "tags": ["tag1", "tag2", ...], // 15-20 SEO-optimized English tags
  "hashtags": ["#tag1", "#tag2", ...], // 5-8 trending hashtags in ${lang}
  "chapters": "0:00 Intro\\n0:30 [Chapter]\\n..." // optional YouTube chapters based on scenes
}`

            const r = await aiGenerate<SEOResult>(prompt, SYSTEM_PROMPT, provider)
            setResult(r)
        } catch (err: any) { setError(err.message) }
        finally { setLoading(false) }
    }

    const copyText = (key: string, text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            setCopied(key)
            setTimeout(() => setCopied(null), 2000)
        })
    }

    const CopyBtn = ({ k, text }: { k: string; text: string }) => (
        <button onClick={() => copyText(k, text)} className="hover:opacity-70 p-1" style={{ color: 'var(--muted)' }}>
            {copied === k ? <Check size={12} style={{ color: 'var(--green)' }} /> : <Copy size={12} />}
        </button>
    )

    return (
        <Modal title="YouTube SEO Generator" onClose={onClose} width={580}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    AI generates YouTube SEO from project storyline + selected video context.
                </div>

                <div className="flex gap-3 items-end flex-wrap">
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
                        </select>
                    </div>
                    <ActionButton variant="primary" onClick={generate} disabled={loading}>
                        <Tv2 size={12} /> {loading ? 'Generating...' : 'Generate SEO'}
                    </ActionButton>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {result && (
                    <div className="flex flex-col gap-3">
                        {/* Title */}
                        <Field label="Title" chars={result.title.length} max={70}>
                            <div className="flex gap-2 items-start">
                                <div className="flex-1 text-sm font-semibold" style={{ color: 'var(--text)' }}>{result.title}</div>
                                <CopyBtn k="title" text={result.title} />
                            </div>
                        </Field>

                        {/* Description */}
                        <Field label="Description" chars={result.description.length} max={500}>
                            <div className="flex gap-2 items-start">
                                <div className="flex-1 text-xs whitespace-pre-wrap" style={{ color: 'var(--text)' }}>{result.description}</div>
                                <CopyBtn k="desc" text={result.description} />
                            </div>
                        </Field>

                        {/* Tags */}
                        <Field label={`Tags (${result.tags?.length ?? 0})`}>
                            <div className="flex gap-2 items-start">
                                <div className="flex-1 flex flex-wrap gap-1">
                                    {result.tags?.map((t, i) => (
                                        <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface)', color: 'var(--muted)', border: '1px solid var(--border)' }}>{t}</span>
                                    ))}
                                </div>
                                <CopyBtn k="tags" text={result.tags?.join(', ') ?? ''} />
                            </div>
                        </Field>

                        {/* Hashtags */}
                        <Field label="Hashtags">
                            <div className="flex gap-2 items-start">
                                <div className="flex-1 text-xs" style={{ color: 'var(--accent)' }}>{result.hashtags?.join(' ')}</div>
                                <CopyBtn k="hashtags" text={result.hashtags?.join(' ') ?? ''} />
                            </div>
                        </Field>

                        {/* Chapters */}
                        {result.chapters && (
                            <Field label="Chapters">
                                <div className="flex gap-2 items-start">
                                    <pre className="flex-1 text-xs" style={{ color: 'var(--text)', fontFamily: 'monospace' }}>{result.chapters}</pre>
                                    <CopyBtn k="chapters" text={result.chapters} />
                                </div>
                            </Field>
                        )}

                        {/* Copy all */}
                        <ActionButton variant="secondary" onClick={() => {
                            const all = `${result.title}\n\n${result.description}\n\n${result.hashtags?.join(' ')}\n\nTags: ${result.tags?.join(', ')}`
                            copyText('all', all)
                        }}>
                            <Copy size={12} /> {copied === 'all' ? '✓ Copied!' : 'Copy All'}
                        </ActionButton>
                    </div>
                )}
            </div>
        </Modal>
    )
}

function Field({ label, chars, max, children }: { label: string; chars?: number; max?: number; children: React.ReactNode }) {
    const over = chars !== undefined && max !== undefined && chars > max
    return (
        <div className="flex flex-col gap-1.5 rounded p-3" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>{label}</span>
                {chars !== undefined && (
                    <span className="text-xs ml-auto" style={{ color: over ? 'var(--red)' : 'var(--muted)' }}>{chars}/{max}</span>
                )}
            </div>
            {children}
        </div>
    )
}
