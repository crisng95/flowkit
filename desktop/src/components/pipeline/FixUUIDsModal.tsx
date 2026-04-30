/**
 * FixUUIDsModal
 * Scans project entities and scenes for non-UUID media_ids (CAMS... format)
 * and repairs them by extracting UUID from the corresponding URL.
 * Corresponds to CLI skill: fk:fix-uuids
 */
import { useState } from 'react'
import { Wrench, CheckCircle, AlertTriangle } from 'lucide-react'
import Modal from '../ui/Modal'
import ActionButton from '../ui/ActionButton'
import { fetchAPI, patchAPI } from '../../api/client'
import { normalizeOrientation } from '../../lib/orientation'

interface Fix {
    resource: string
    field: string
    old: string
    new: string
    status: 'fixed' | 'error'
    error?: string
}

interface Props {
    projectId: string
    videoId: string
    orientation?: string
    onClose: () => void
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isUUID(v: string | null | undefined): boolean {
    return !!v && UUID_RE.test(v)
}

function extractUUIDFromUrl(url: string | null | undefined): string | null {
    if (!url) return null
    // Google Storage: /image/{UUID}?... or /{type}/{UUID}?...
    const m = url.match(/\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i)
    return m ? m[1] : null
}

export default function FixUUIDsModal({ projectId, videoId, orientation, onClose }: Props) {
    const [running, setRunning] = useState(false)
    const [fixes, setFixes] = useState<Fix[]>([])
    const [scanned, setScanned] = useState(false)
    const [error, setError] = useState('')

    const run = async () => {
        setRunning(true); setError(''); setFixes([])
        const newFixes: Fix[] = []

        try {
            // ── Scan entities ──────────────────────────────────────
            const chars = await fetchAPI<any[]>(`/api/projects/${projectId}/characters`)
            for (const c of chars) {
                if (!isUUID(c.media_id) && c.media_id) {
                    const extracted = extractUUIDFromUrl(c.reference_image_url)
                    if (extracted) {
                        let status: 'fixed' | 'error' = 'fixed'
                        let errMsg: string | undefined
                        try {
                            await patchAPI(`/api/characters/${c.id}`, { media_id: extracted })
                        } catch (e: any) { status = 'error'; errMsg = e.message }
                        newFixes.push({ resource: `Character: ${c.name}`, field: 'media_id', old: c.media_id, new: extracted, status, error: errMsg })
                    }
                }
            }

            // ── Scan scenes ────────────────────────────────────────
            const scenes = await fetchAPI<any[]>(`/api/scenes?video_id=${videoId}`)
            const primary = normalizeOrientation(orientation) === 'HORIZONTAL' ? 'horizontal' : 'vertical'
            const prefixes: Array<'vertical' | 'horizontal'> = primary === 'vertical'
                ? ['vertical', 'horizontal']
                : ['horizontal', 'vertical']
            const FIELDS: [string, string][] = prefixes.flatMap((ori) => ([
                [`${ori}_image_media_id`, `${ori}_image_url`],
                [`${ori}_video_media_id`, `${ori}_video_url`],
                [`${ori}_upscale_media_id`, `${ori}_upscale_url`],
            ]))

            for (const scene of scenes) {
                for (const [field, urlField] of FIELDS) {
                    const val = scene[field]
                    if (!isUUID(val) && val) {
                        const extracted = extractUUIDFromUrl(scene[urlField])
                        if (extracted) {
                            let status: 'fixed' | 'error' = 'fixed'
                            let errMsg: string | undefined
                            try {
                                await patchAPI(`/api/scenes/${scene.id}`, { [field]: extracted })
                            } catch (e: any) { status = 'error'; errMsg = e.message }
                            newFixes.push({ resource: `Scene #${scene.display_order + 1}`, field, old: val, new: extracted, status, error: errMsg })
                        }
                    }
                }
            }

            setFixes(newFixes)
            setScanned(true)
        } catch (err: any) { setError(err.message) }
        finally { setRunning(false) }
    }

    const fixed = fixes.filter(f => f.status === 'fixed').length
    const errors = fixes.filter(f => f.status === 'error').length

    return (
        <Modal title="Fix Media IDs (CAMS → UUID)" onClose={onClose} width={560}>
            <div className="flex flex-col gap-4">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                    Scans all character and scene media IDs for invalid CAMS... format and repairs them
                    by extracting the correct UUID from the stored URL.
                </div>

                <ActionButton variant="primary" onClick={run} disabled={running}>
                    <Wrench size={12} /> {running ? 'Scanning...' : scanned ? 'Re-scan & Fix' : 'Scan & Fix All'}
                </ActionButton>

                {error && <div className="text-xs p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--red)' }}>{error}</div>}

                {scanned && !running && (
                    fixes.length === 0 ? (
                        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--green)' }}>
                            <CheckCircle size={14} /> All media IDs are already UUID format. No fixes needed.
                        </div>
                    ) : (
                        <div className="flex flex-col gap-2">
                            <div className="flex gap-3 text-xs">
                                <span style={{ color: 'var(--green)' }}>✓ {fixed} fixed</span>
                                {errors > 0 && <span style={{ color: 'var(--red)' }}>✗ {errors} errors</span>}
                            </div>
                            <div className="rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                                <table className="w-full text-xs">
                                    <thead>
                                        <tr style={{ background: 'var(--surface)' }}>
                                            <th className="text-left px-3 py-2" style={{ color: 'var(--muted)' }}>Resource</th>
                                            <th className="text-left px-3 py-2" style={{ color: 'var(--muted)' }}>Field</th>
                                            <th className="text-left px-3 py-2" style={{ color: 'var(--muted)' }}>New UUID</th>
                                            <th className="text-left px-3 py-2" style={{ color: 'var(--muted)' }}>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {fixes.map((f, i) => (
                                            <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                                                <td className="px-3 py-2" style={{ color: 'var(--text)' }}>{f.resource}</td>
                                                <td className="px-3 py-2 font-mono" style={{ color: 'var(--muted)', fontSize: 10 }}>{f.field.replace('vertical_', '').replace('horizontal_', '').replace('_media_id', '')}</td>
                                                <td className="px-3 py-2 font-mono" style={{ color: 'var(--accent)', fontSize: 10 }}>{f.new.slice(0, 8)}...</td>
                                                <td className="px-3 py-2">
                                                    {f.status === 'fixed'
                                                        ? <span style={{ color: 'var(--green)' }}>✓ Fixed</span>
                                                        : <span style={{ color: 'var(--red)' }} title={f.error}>✗ Error</span>}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )
                )}

                <div className="flex justify-end">
                    <ActionButton variant="ghost" onClick={onClose}>Close</ActionButton>
                </div>
            </div>
        </Modal>
    )
}
