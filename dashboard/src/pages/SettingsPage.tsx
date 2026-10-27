import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Globe } from 'lucide-react'
import { LANGS, LANG_LABELS, type Lang } from '../i18n/translations'
import { fetchAPI, patchAPI } from '../api/client'
import { useTranslation } from '../i18n/useTranslation'
import type { RoleAssignment, ProvidersResponse, ProviderModelsResponse, ProvidersUpdateResponse } from '../types'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardAction } from '../components/ui/card'
import { Button } from '../components/ui/button'

const DEFAULT_OPTION = '__default__'
const CUSTOM_OPTION = '__custom__'

const CONTROL_CLASS = 'text-xs px-2 py-1.5 rounded outline-none w-full'
const CONTROL_STYLE = { background: 'var(--card)', color: 'var(--text)', border: '1px solid var(--border)' }

interface SaveState {
  ok: boolean
  text: string
}

// fetchAPI throws `API <status>: <body>` — pull the backend's `detail` back out so a 400 reads verbatim.
function apiDetail(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err)
  const body = raw.replace(/^API \d+: /, '')
  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
  } catch {
    // not JSON — fall through to the raw message
  }
  return raw
}

function cloneRoles(roles: Record<string, RoleAssignment>): Record<string, RoleAssignment> {
  return Object.fromEntries(Object.entries(roles).map(([id, r]) => [id, { ...r }]))
}

function sameAssignment(a: RoleAssignment, b: RoleAssignment): boolean {
  return a.provider === b.provider && a.model === b.model && a.effort === b.effort
}

export default function SettingsPage() {
  const { lang, setLang, t } = useTranslation()
  const [data, setData] = useState<ProvidersResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, RoleAssignment>>({})
  const [models, setModels] = useState<Record<string, ProviderModelsResponse>>({})
  const [modelsLoading, setModelsLoading] = useState<Record<string, boolean>>({})
  const [customModel, setCustomModel] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saveState, setSaveState] = useState<Record<string, SaveState>>({})
  const [testing, setTesting] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)

  const loadModels = useCallback(async (provider: string, refresh: boolean) => {
    setModelsLoading(prev => ({ ...prev, [provider]: true }))
    try {
      const res = await fetchAPI<ProviderModelsResponse>(
        `/api/providers/models?provider=${encodeURIComponent(provider)}&refresh=${refresh}`
      )
      setModels(prev => ({ ...prev, [provider]: res }))
    } catch {
      // an unreachable catalog is not fatal — render it as "no catalog available"
      setModels(prev => ({ ...prev, [provider]: { provider, models: [], authoritative: false } }))
    } finally {
      setModelsLoading(prev => ({ ...prev, [provider]: false }))
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await fetchAPI<ProvidersResponse>('/api/providers?live=false')
      setData(res)
      setDrafts(cloneRoles(res.roles))
      setCustomModel({})
      setSaveState({})
      Array.from(new Set(Object.values(res.roles).map(r => r.provider))).forEach(p => { loadModels(p, false) })
    } catch (err) {
      setData(null)
      setLoadError(apiDetail(err))
    } finally {
      setLoading(false)
    }
  }, [loadModels])

  useEffect(() => { Promise.resolve().then(load) }, [load])

  function updateDraft(roleId: string, patch: Partial<RoleAssignment>) {
    setDrafts(prev => ({ ...prev, [roleId]: { ...prev[roleId], ...patch } }))
    setSaveState(prev => {
      if (!(roleId in prev)) return prev
      const next = { ...prev }
      delete next[roleId]
      return next
    })
  }

  function changeProvider(roleId: string, provider: string) {
    // a model slug from one CLI means nothing to another, and effort ladders differ per provider
    const efforts = data?.providers[provider]?.efforts ?? []
    const current = drafts[roleId]
    const effort = current.effort !== null && efforts.includes(current.effort) ? current.effort : null
    updateDraft(roleId, { provider, model: null, effort })
    setCustomModel(prev => ({ ...prev, [roleId]: false }))
    if (!models[provider] && !modelsLoading[provider]) loadModels(provider, false)
  }

  function setModel(roleId: string, model: string | null) {
    // a provider whose slugs name their own effort rejects --model and --effort together
    const encodesEffort = data?.providers[drafts[roleId].provider]?.model_encodes_effort ?? false
    updateDraft(roleId, model !== null && encodesEffort ? { model, effort: null } : { model })
  }

  function selectModel(roleId: string, value: string) {
    if (value === CUSTOM_OPTION) {
      setCustomModel(prev => ({ ...prev, [roleId]: true }))
      setModel(roleId, null)
      return
    }
    setModel(roleId, value === DEFAULT_OPTION ? null : value)
  }

  async function save(roleId: string) {
    const draft = drafts[roleId]
    const model = draft.model !== null && draft.model.trim() !== '' ? draft.model.trim() : null
    const encodesEffort = data?.providers[draft.provider]?.model_encodes_effort ?? false
    const effort = model !== null && encodesEffort ? null : draft.effort
    setSaving(prev => ({ ...prev, [roleId]: true }))
    try {
      const res = await patchAPI<ProvidersUpdateResponse>('/api/providers', {
        roles: { [roleId]: { provider: draft.provider, model, effort } },
      })
      setData(prev => (prev ? { ...prev, active: res.active, roles: res.roles } : prev))
      setDrafts(prev => ({ ...prev, [roleId]: { ...(res.roles[roleId] ?? prev[roleId]) } }))
      setSaveState(prev => ({ ...prev, [roleId]: { ok: true, text: t('settings.saved') } }))
    } catch (err) {
      setSaveState(prev => ({ ...prev, [roleId]: { ok: false, text: apiDetail(err) } }))
    } finally {
      setSaving(prev => ({ ...prev, [roleId]: false }))
    }
  }

  async function runTest() {
    setTesting(true)
    setTestError(null)
    try {
      const res = await fetchAPI<ProvidersResponse>('/api/providers?live=true')
      setData(prev => (prev ? { ...prev, providers: res.providers } : res))
    } catch (err) {
      setTestError(apiDetail(err))
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return <div className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.loading')}</div>
  }

  if (!data) {
    return (
      <div className="flex flex-col items-start gap-2.5">
        <span className="text-xs" style={{ color: 'var(--red)' }}>{loadError ?? t('settings.loadFailed')}</span>
        <Button variant="outline" size="sm" onClick={() => { Promise.resolve().then(load) }}>{t('settings.retry')}</Button>
      </div>
    )
  }

  const providers = data.providers
  const roleIds = Object.keys(data.roles)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-lg font-semibold" style={{ color: 'var(--text)' }}>{t('settings.title')}</h1>
        <span className="text-[11px]" style={{ color: 'var(--muted)' }}>{t('settings.desc')}</span>
      </div>

      <Card className="py-4">
        <CardHeader>
          <CardTitle className="text-xs tracking-widest uppercase flex items-center gap-1.5">
            <Globe size={13} style={{ color: 'var(--accent)' }} />
            {t('settings.language.title')}
          </CardTitle>
          <CardDescription className="text-[11px]">{t('settings.language.desc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="max-w-xs">
            <select
              value={lang}
              onChange={e => setLang(e.target.value as Lang)}
              className={CONTROL_CLASS}
              style={CONTROL_STYLE}
            >
              {LANGS.map(l => (
                <option key={l} value={l}>{LANG_LABELS[l]}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      <Card className="py-4">
        <CardHeader>
          <CardTitle className="text-xs tracking-widest uppercase">{t('settings.providers.title')}</CardTitle>
          <CardDescription className="text-[11px]">{t('settings.testHint')}</CardDescription>
          <CardAction>
            <Button variant="outline" size="sm" disabled={testing} onClick={runTest}>
              {testing ? t('settings.testing') : t('settings.test')}
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent>
          {testError && <div className="text-[10px] pb-2" style={{ color: 'var(--red)' }}>{testError}</div>}
          <div className="flex flex-col gap-1.5">
            {Object.entries(providers).map(([name, info]) => (
              <div key={name} className="flex items-center gap-3 text-[11px]">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: info.installed ? 'var(--green)' : 'var(--red)' }} />
                <span style={{ width: 90 }}>{info.binary ?? name}</span>
                <span style={{ color: 'var(--muted)', width: 100 }}>
                  {info.installed ? t('settings.providers.installed') : t('settings.providers.missing')}
                </span>
                <span style={{ width: 100, color: info.tested === null ? 'var(--muted)' : info.tested ? 'var(--green)' : 'var(--red)' }}>
                  {info.tested === null ? t('settings.providers.untested') : info.tested ? t('settings.providers.ok') : t('settings.providers.failed')}
                </span>
                {info.error && <span className="truncate" style={{ color: 'var(--muted)' }}>{info.error}</span>}
                {name === data.active && (
                  <span className="ml-auto text-[9px] tracking-widest flex-shrink-0" style={{ color: 'var(--accent)' }}>{t('settings.activeProvider')}</span>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {roleIds.length === 0 ? (
        <div className="text-xs" style={{ color: 'var(--muted)' }}>{t('settings.empty')}</div>
      ) : roleIds.map(roleId => {
        const draft = drafts[roleId]
        const meta = data.role_meta[roleId]
        const info = providers[draft.provider]
        const efforts = info?.efforts ?? []
        const catalog = models[draft.provider]
        const modelList = catalog?.models ?? []
        const authoritative = catalog?.authoritative ?? false
        const modelBusy = modelsLoading[draft.provider] ?? false
        const custom = customModel[roleId] ?? false
        const knownModel = draft.model !== null && modelList.some(m => m.id === draft.model)
        const effortLocked = (info?.model_encodes_effort ?? false) && draft.model !== null
        const dirty = !sameAssignment(draft, data.roles[roleId])
        const busy = saving[roleId] ?? false
        const state = saveState[roleId]

        return (
          <Card key={roleId} className="py-4">
            <CardHeader>
              <CardTitle className="text-xs tracking-widest uppercase">{meta?.label ?? roleId}</CardTitle>
              <CardDescription className="text-[11px]">{meta?.description ?? roleId}</CardDescription>
              <CardAction>
                <span className="text-[9px] tracking-widest" style={{ color: dirty ? 'var(--yellow)' : 'var(--muted)' }}>
                  {dirty ? t('settings.unsaved') : t('settings.inSync')}
                </span>
              </CardAction>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3.5 items-start" style={{ gridTemplateColumns: '1fr 1.6fr 1fr' }}>
                <div className="flex flex-col gap-1">
                  <span className="text-[9px] tracking-widest" style={{ color: 'var(--muted)' }}>{t('settings.field.agent')}</span>
                  <select
                    value={draft.provider}
                    onChange={e => changeProvider(roleId, e.target.value)}
                    className={CONTROL_CLASS}
                    style={CONTROL_STYLE}
                  >
                    {Object.entries(providers).map(([name, p]) => (
                      <option key={name} value={name} disabled={!p.installed}>
                        {p.installed ? (p.binary ?? name) : `${p.binary} · ${t('settings.notInstalled')}`}
                      </option>
                    ))}
                  </select>
                  {info && !info.installed && (
                    <span className="text-[10px] leading-snug" style={{ color: 'var(--red)' }}>
                      {t('settings.installHint', { binary: info.binary })}
                    </span>
                  )}
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[9px] tracking-widest" style={{ color: 'var(--muted)' }}>{t('settings.field.model')}</span>
                  <div className="flex items-center gap-1.5">
                    {custom ? (
                      <input
                        value={draft.model ?? ''}
                        onChange={e => setModel(roleId, e.target.value === '' ? null : e.target.value)}
                        placeholder={t('settings.modelCustomPlaceholder')}
                        className={CONTROL_CLASS}
                        style={CONTROL_STYLE}
                      />
                    ) : (
                      <select
                        value={draft.model ?? DEFAULT_OPTION}
                        onChange={e => selectModel(roleId, e.target.value)}
                        className={CONTROL_CLASS}
                        style={CONTROL_STYLE}
                      >
                        <option value={DEFAULT_OPTION}>{t('settings.optionDefault')}</option>
                        {modelList.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
                        {draft.model !== null && !knownModel && <option value={draft.model}>{draft.model}</option>}
                        {!authoritative && <option value={CUSTOM_OPTION}>{t('settings.optionCustom')}</option>}
                      </select>
                    )}
                    <Button
                      variant="outline"
                      size="icon-xs"
                      aria-label={t('settings.refreshModels')}
                      title={t('settings.refreshModels')}
                      disabled={modelBusy}
                      onClick={() => { loadModels(draft.provider, true) }}
                    >
                      <RefreshCw className={modelBusy ? 'animate-spin' : undefined} />
                    </Button>
                  </div>
                  <span className="text-[10px] leading-snug" style={{ color: 'var(--muted)' }}>
                    {modelBusy
                      ? t('settings.modelsLoading')
                      : modelList.length === 0
                        ? t('settings.modelsEmpty')
                        : !authoritative
                          ? t('settings.modelsFreeText')
                          : ''}
                  </span>
                  {custom && (
                    <button
                      type="button"
                      className="text-[10px] text-left cursor-pointer bg-transparent border-0 p-0"
                      style={{ color: 'var(--accent)' }}
                      onClick={() => {
                        setCustomModel(prev => ({ ...prev, [roleId]: false }))
                        setModel(roleId, null)
                      }}
                    >
                      {t('settings.modelBackToList')}
                    </button>
                  )}
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[9px] tracking-widest" style={{ color: 'var(--muted)' }}>{t('settings.field.effort')}</span>
                  <select
                    value={effortLocked ? DEFAULT_OPTION : draft.effort ?? DEFAULT_OPTION}
                    disabled={effortLocked}
                    onChange={e => updateDraft(roleId, { effort: e.target.value === DEFAULT_OPTION ? null : e.target.value })}
                    className={CONTROL_CLASS}
                    style={{ ...CONTROL_STYLE, opacity: effortLocked ? 0.5 : 1 }}
                  >
                    <option value={DEFAULT_OPTION}>{t('settings.optionDefault')}</option>
                    {efforts.map(x => <option key={x} value={x}>{x}</option>)}
                  </select>
                  {effortLocked && (
                    <span className="text-[10px] leading-snug" style={{ color: 'var(--muted)' }}>
                      {t('settings.effortLockedHint', { binary: info.binary })}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 pt-3.5">
                <Button size="sm" disabled={!dirty || busy} onClick={() => save(roleId)}>
                  {busy ? t('settings.saving') : t('settings.save')}
                </Button>
                {state && (
                  <span className="text-[10px] leading-snug" style={{ color: state.ok ? 'var(--green)' : 'var(--red)' }}>{state.text}</span>
                )}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
