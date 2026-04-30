import { useEffect, useState } from 'react'
import { BadgeCheck, Image, Wand2 } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI } from '../../api/client'

interface Props {
    projectId: string
    videoId: string
    onClose: () => void
}

interface ChannelItem {
    name: string
    icon_exists: boolean
    intro_exists: boolean
    outro_exists: boolean
    badge_4k_exists: boolean
}

interface BrandResult {
    output_path: string
    width: number
    height: number
    logo_size: number
    logo_padding: number
    intro_used?: string | null
    outro_used?: string | null
    badge_4k_applied: boolean
    thumbnails: string[]
}

export default function BrandLogoModal({ projectId, videoId, onClose }: Props) {
    const [channels, setChannels] = useState<ChannelItem[]>([])
    const [channelName, setChannelName] = useState('')
    const [size, setSize] = useState('')
    const [applyThumbs, setApplyThumbs] = useState(false)
    const [includeIntro, setIncludeIntro] = useState(true)
    const [includeOutro, setIncludeOutro] = useState(true)

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [result, setResult] = useState<BrandResult | null>(null)

    useEffect(() => {
        fetchAPI<ChannelItem[]>('/api/workflows/channels')
            .then((rows) => {
                setChannels(rows)
                if (!channelName && rows[0]) setChannelName(rows[0].name)
            })
            .catch(() => setChannels([]))
    }, [channelName])

    const run = async () => {
        if (!channelName) return
        setLoading(true)
        setError('')
        setResult(null)
        try {
            const r = await fetchAPI<BrandResult>('/api/workflows/brand-logo', {
                method: 'POST',
                body: JSON.stringify({
                    channel_name: channelName,
                    project_id: projectId,
                    video_id: videoId,
                    size: size.trim() ? Number(size) : undefined,
                    apply_thumbnails: applyThumbs,
                    include_intro: includeIntro,
                    include_outro: includeOutro,
                }),
            })
            setResult(r)
        } catch (e: any) {
            setError(e.message ?? 'Branding failed')
        } finally {
            setLoading(false)
        }
    }

    const selected = channels.find(c => c.name === channelName)

    return (
        <Modal title="Brand Logo (fk:brand-logo)" onClose={onClose} width={640}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Áp intro/outro + watermark logo + 4K badge lên video final của project.
                </div>

                <div className="rounded p-3 flex flex-col gap-2" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
                    <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Channel</div>
                    <select value={channelName} onChange={e => setChannelName(e.target.value)} className="input">
                        <option value="">Select channel...</option>
                        {channels.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                    </select>
                    {selected && (
                        <div className="text-xs flex flex-wrap gap-2" style={{ color: 'var(--muted)' }}>
                            <span>Icon: {selected.icon_exists ? '✓' : '✗'}</span>
                            <span>Intro: {selected.intro_exists ? '✓' : '✗'}</span>
                            <span>Outro: {selected.outro_exists ? '✓' : '✗'}</span>
                            <span>4K badge: {selected.badge_4k_exists ? '✓' : '✗'}</span>
                        </div>
                    )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Logo size (optional)</label>
                        <input value={size} onChange={e => setSize(e.target.value)} className="input" placeholder="Auto" />
                    </div>
                    <div className="flex flex-col gap-1.5 justify-end text-xs" style={{ color: 'var(--text)' }}>
                        <label className="inline-flex items-center gap-2"><input type="checkbox" checked={includeIntro} onChange={e => setIncludeIntro(e.target.checked)} /> Include intro</label>
                        <label className="inline-flex items-center gap-2"><input type="checkbox" checked={includeOutro} onChange={e => setIncludeOutro(e.target.checked)} /> Include outro</label>
                        <label className="inline-flex items-center gap-2"><input type="checkbox" checked={applyThumbs} onChange={e => setApplyThumbs(e.target.checked)} /> Brand thumbnails</label>
                    </div>
                </div>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {result && (
                    <div className="rounded p-3 flex flex-col gap-1.5 text-xs" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}>
                        <div className="inline-flex items-center gap-1"><BadgeCheck size={12} /> Branding completed</div>
                        <div><strong>Output:</strong> {result.output_path}</div>
                        <div><strong>Resolution:</strong> {result.width}x{result.height}</div>
                        <div><strong>Logo:</strong> {result.logo_size}px (pad {result.logo_padding}px)</div>
                        <div><strong>Intro:</strong> {result.intro_used ?? 'skipped'} · <strong>Outro:</strong> {result.outro_used ?? 'skipped'}</div>
                        <div><strong>4K badge:</strong> {result.badge_4k_applied ? 'applied' : 'not applied'}</div>
                        {result.thumbnails.length > 0 && (
                            <div><strong>Thumbnails branded:</strong> {result.thumbnails.length}</div>
                        )}
                    </div>
                )}

                <div className="flex justify-end gap-2 pt-1">
                    <ActionButton variant="ghost" onClick={onClose}>Close</ActionButton>
                    <ActionButton variant="primary" onClick={run} disabled={loading || !channelName}>
                        <Wand2 size={12} /> {loading ? 'Processing...' : 'Apply Branding'}
                    </ActionButton>
                </div>
            </div>
        </Modal>
    )
}
