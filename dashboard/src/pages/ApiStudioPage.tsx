import { useEffect, useMemo, useState } from 'react'

type HttpMethod = 'get' | 'post' | 'put' | 'patch' | 'delete'

interface SchemaObject {
  type?: string
  properties?: Record<string, SchemaObject>
  items?: SchemaObject
  enum?: unknown[]
  default?: unknown
  example?: unknown
  required?: string[]
  oneOf?: SchemaObject[]
  anyOf?: SchemaObject[]
  allOf?: SchemaObject[]
  $ref?: string
}

interface ParameterObject {
  name: string
  in: 'path' | 'query' | 'header' | 'cookie'
  required?: boolean
  schema?: SchemaObject
}

interface RequestBodyObject {
  content?: Record<string, { schema?: SchemaObject; example?: unknown }>
}

interface OperationObject {
  summary?: string
  operationId?: string
  description?: string
  parameters?: ParameterObject[]
  requestBody?: RequestBodyObject
}

interface PathItemObject {
  parameters?: ParameterObject[]
  get?: OperationObject
  post?: OperationObject
  put?: OperationObject
  patch?: OperationObject
  delete?: OperationObject
}

interface OpenApiSpec {
  paths: Record<string, PathItemObject>
  components?: { schemas?: Record<string, SchemaObject> }
}

interface Endpoint {
  id: string
  method: HttpMethod
  path: string
  summary: string
  operation: OperationObject
  parameters: ParameterObject[]
}

interface ApiResult {
  status: number
  statusText: string
  contentType: string
  bodyText: string
}

const METHODS: HttpMethod[] = ['get', 'post', 'put', 'patch', 'delete']

function resolveSchema(schema: SchemaObject | undefined, spec: OpenApiSpec, depth = 0): SchemaObject | undefined {
  if (!schema || depth > 8) return schema
  if (!schema.$ref) return schema
  const prefix = '#/components/schemas/'
  if (!schema.$ref.startsWith(prefix)) return schema
  const name = schema.$ref.slice(prefix.length)
  const next = spec.components?.schemas?.[name]
  if (!next) return schema
  return resolveSchema(next, spec, depth + 1)
}

function sampleForSchema(schema: SchemaObject | undefined, spec: OpenApiSpec, depth = 0): unknown {
  if (!schema || depth > 8) return null
  const resolved = resolveSchema(schema, spec)
  if (!resolved) return null
  if (resolved.example !== undefined) return resolved.example
  if (resolved.default !== undefined) return resolved.default
  if (resolved.enum && resolved.enum.length > 0) return resolved.enum[0]
  if (resolved.oneOf && resolved.oneOf.length > 0) return sampleForSchema(resolved.oneOf[0], spec, depth + 1)
  if (resolved.anyOf && resolved.anyOf.length > 0) return sampleForSchema(resolved.anyOf[0], spec, depth + 1)
  if (resolved.allOf && resolved.allOf.length > 0) {
    const combined: Record<string, unknown> = {}
    for (const part of resolved.allOf) {
      const partSample = sampleForSchema(part, spec, depth + 1)
      if (partSample && typeof partSample === 'object' && !Array.isArray(partSample)) {
        Object.assign(combined, partSample)
      }
    }
    return Object.keys(combined).length > 0 ? combined : null
  }
  switch (resolved.type) {
    case 'object': {
      const out: Record<string, unknown> = {}
      const props = resolved.properties ?? {}
      for (const [key, val] of Object.entries(props)) {
        out[key] = sampleForSchema(val, spec, depth + 1)
      }
      return out
    }
    case 'array':
      return [sampleForSchema(resolved.items, spec, depth + 1)]
    case 'integer':
    case 'number':
      return 0
    case 'boolean':
      return false
    case 'string':
      return ''
    default:
      return null
  }
}

function prettifyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

export default function ApiStudioPage() {
  const [spec, setSpec] = useState<OpenApiSpec | null>(null)
  const [loadingSpec, setLoadingSpec] = useState(true)
  const [specError, setSpecError] = useState('')

  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [pathValues, setPathValues] = useState<Record<string, string>>({})
  const [queryValues, setQueryValues] = useState<Record<string, string>>({})
  const [bodyText, setBodyText] = useState('')
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [result, setResult] = useState<ApiResult | null>(null)

  useEffect(() => {
    setLoadingSpec(true)
    ;(async () => {
      const urls = ['/openapi.json', 'http://127.0.0.1:8100/openapi.json']
      let lastError = 'Cannot load OpenAPI'
      for (const url of urls) {
        try {
          const res = await fetch(url)
          if (!res.ok) throw new Error(`Cannot load OpenAPI (${res.status})`)
          const contentType = res.headers.get('content-type') ?? ''
          const text = await res.text()
          if (!contentType.includes('application/json')) {
            throw new Error(`OpenAPI response is not JSON (got: ${contentType || 'unknown'})`)
          }
          const data = JSON.parse(text) as OpenApiSpec
          setSpec(data)
          setSpecError('')
          return
        } catch (e: unknown) {
          lastError = e instanceof Error ? e.message : 'Cannot load OpenAPI'
        }
      }
      setSpecError(lastError)
    })().finally(() => setLoadingSpec(false))
  }, [])

  const endpoints = useMemo<Endpoint[]>(() => {
    if (!spec) return []
    const out: Endpoint[] = []
    for (const [path, item] of Object.entries(spec.paths)) {
      for (const method of METHODS) {
        const op = item[method]
        if (!op) continue
        const params = [...(item.parameters ?? []), ...(op.parameters ?? [])]
        out.push({
          id: `${method.toUpperCase()} ${path}`,
          method,
          path,
          summary: op.summary || op.operationId || '(no summary)',
          operation: op,
          parameters: params,
        })
      }
    }
    return out.sort((a, b) => a.path.localeCompare(b.path) || a.method.localeCompare(b.method))
  }, [spec])

  useEffect(() => {
    if (!selectedId && endpoints.length > 0) {
      setSelectedId(endpoints[0].id)
    }
  }, [selectedId, endpoints])

  const selected = endpoints.find((e) => e.id === selectedId) ?? null

  useEffect(() => {
    if (!selected || !spec) return
    const newPathValues: Record<string, string> = {}
    const newQueryValues: Record<string, string> = {}

    for (const p of selected.parameters) {
      const seed = sampleForSchema(p.schema, spec)
      const val = seed === null || seed === undefined ? '' : String(seed)
      if (p.in === 'path') newPathValues[p.name] = val
      if (p.in === 'query') newQueryValues[p.name] = val
    }
    setPathValues(newPathValues)
    setQueryValues(newQueryValues)

    const bodySchema = selected.operation.requestBody?.content?.['application/json']?.schema
    const bodyExample = selected.operation.requestBody?.content?.['application/json']?.example
    if (bodyExample !== undefined) {
      setBodyText(JSON.stringify(bodyExample, null, 2))
    } else if (bodySchema) {
      const seed = sampleForSchema(bodySchema, spec)
      setBodyText(JSON.stringify(seed, null, 2))
    } else {
      setBodyText('')
    }

    setRunError('')
    setResult(null)
  }, [selected, spec])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return endpoints
    return endpoints.filter((e) =>
      e.id.toLowerCase().includes(q) ||
      e.summary.toLowerCase().includes(q),
    )
  }, [endpoints, search])

  async function runEndpoint() {
    if (!selected) return
    setRunning(true)
    setRunError('')
    setResult(null)

    try {
      let urlPath = selected.path
      for (const p of selected.parameters.filter((x) => x.in === 'path')) {
        const raw = pathValues[p.name] ?? ''
        if (p.required && !raw) throw new Error(`Missing path param: ${p.name}`)
        urlPath = urlPath.replace(`{${p.name}}`, encodeURIComponent(raw))
      }

      const query = new URLSearchParams()
      for (const p of selected.parameters.filter((x) => x.in === 'query')) {
        const raw = queryValues[p.name] ?? ''
        if (!raw && p.required) throw new Error(`Missing query param: ${p.name}`)
        if (raw) query.set(p.name, raw)
      }
      const finalUrl = query.size > 0 ? `${urlPath}?${query.toString()}` : urlPath

      const method = selected.method.toUpperCase()
      const init: RequestInit = { method, headers: {} }

      if (method !== 'GET' && bodyText.trim()) {
        try {
          const parsed = JSON.parse(bodyText)
          init.body = JSON.stringify(parsed)
          ;(init.headers as Record<string, string>)['Content-Type'] = 'application/json'
        } catch {
          throw new Error('Body JSON is invalid')
        }
      }

      const res = await fetch(finalUrl, init)
      const contentType = res.headers.get('content-type') ?? ''
      const rawText = await res.text()
      const body = contentType.includes('application/json') ? prettifyJson(rawText) : rawText

      setResult({
        status: res.status,
        statusText: res.statusText,
        contentType,
        bodyText: body || '(empty)',
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Request failed'
      setRunError(msg)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="grid gap-4 h-full" style={{ gridTemplateColumns: '320px minmax(0, 1fr)' }}>
      <section className="rounded-lg border p-3 flex flex-col gap-3 overflow-hidden" style={{ borderColor: 'var(--border)', background: 'var(--card)' }}>
        <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>
          API ENDPOINTS
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search path or summary..."
          className="w-full px-2 py-1.5 rounded text-xs outline-none"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
        />
        <div className="text-xs" style={{ color: 'var(--muted)' }}>
          {loadingSpec ? 'Loading OpenAPI...' : `${filtered.length} endpoints`}
        </div>
        <div className="overflow-auto pr-1 flex-1">
          {specError && <div className="text-xs" style={{ color: 'var(--red)' }}>{specError}</div>}
          {!specError && filtered.map((e) => (
            <button
              key={e.id}
              onClick={() => setSelectedId(e.id)}
              className="w-full text-left px-2 py-2 rounded mb-1 border"
              style={{
                borderColor: selectedId === e.id ? 'var(--accent)' : 'var(--border)',
                background: selectedId === e.id ? 'rgba(59,130,246,0.12)' : 'var(--surface)',
                color: 'var(--text)',
              }}
            >
              <div className="text-[11px] font-semibold" style={{ color: 'var(--accent)' }}>{e.method.toUpperCase()}</div>
              <div className="text-xs">{e.path}</div>
              <div className="text-[11px]" style={{ color: 'var(--muted)' }}>{e.summary}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-lg border p-4 flex flex-col gap-4 overflow-auto" style={{ borderColor: 'var(--border)', background: 'var(--card)' }}>
        {!selected ? (
          <div className="text-xs" style={{ color: 'var(--muted)' }}>Select an endpoint.</div>
        ) : (
          <>
            <div>
              <div className="text-[11px] font-semibold" style={{ color: 'var(--accent)' }}>{selected.method.toUpperCase()}</div>
              <div className="text-sm font-semibold">{selected.path}</div>
              <div className="text-xs" style={{ color: 'var(--muted)' }}>{selected.summary}</div>
            </div>

            {selected.parameters.filter((p) => p.in === 'path').length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Path Params</div>
                {selected.parameters.filter((p) => p.in === 'path').map((p) => (
                  <label key={`path-${p.name}`} className="flex items-center gap-2 text-xs">
                    <span className="w-44">{p.name}{p.required ? ' *' : ''}</span>
                    <input
                      value={pathValues[p.name] ?? ''}
                      onChange={(e) => setPathValues((prev) => ({ ...prev, [p.name]: e.target.value }))}
                      className="flex-1 px-2 py-1.5 rounded outline-none"
                      style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
                    />
                  </label>
                ))}
              </div>
            )}

            {selected.parameters.filter((p) => p.in === 'query').length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Query Params</div>
                {selected.parameters.filter((p) => p.in === 'query').map((p) => (
                  <label key={`query-${p.name}`} className="flex items-center gap-2 text-xs">
                    <span className="w-44">{p.name}{p.required ? ' *' : ''}</span>
                    <input
                      value={queryValues[p.name] ?? ''}
                      onChange={(e) => setQueryValues((prev) => ({ ...prev, [p.name]: e.target.value }))}
                      className="flex-1 px-2 py-1.5 rounded outline-none"
                      style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
                    />
                  </label>
                ))}
              </div>
            )}

            <div className="flex flex-col gap-2">
              <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>JSON Body</div>
              <textarea
                value={bodyText}
                onChange={(e) => setBodyText(e.target.value)}
                rows={14}
                className="w-full px-2 py-2 rounded text-xs outline-none"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', fontFamily: 'inherit' }}
                placeholder={selected.method === 'get' ? 'GET usually has no body' : '{ }'}
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={runEndpoint}
                disabled={running}
                className="px-3 py-1.5 rounded text-xs font-semibold"
                style={{ background: 'var(--accent)', color: '#fff', opacity: running ? 0.7 : 1 }}
              >
                {running ? 'Running...' : 'Run Endpoint'}
              </button>
              {runError && <span className="text-xs" style={{ color: 'var(--red)' }}>{runError}</span>}
            </div>

            {result && (
              <div className="flex flex-col gap-2">
                <div className="text-xs">
                  <span className="font-semibold">Status:</span> {result.status} {result.statusText}
                </div>
                <div className="text-xs" style={{ color: 'var(--muted)' }}>
                  Content-Type: {result.contentType || '(unknown)'}
                </div>
                <pre
                  className="rounded p-3 overflow-auto text-xs"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)', whiteSpace: 'pre-wrap' }}
                >
                  {result.bodyText}
                </pre>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
