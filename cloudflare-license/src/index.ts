interface Env {
  LICENSE_DB: D1Database
  ADMIN_TOKEN?: string
  ADMIN_USERNAME?: string
  ADMIN_PASSWORD?: string
  SESSION_SECRET?: string
  CORS_ORIGIN?: string
}

type PlanCode = 'TRIAL_3D' | '1M' | '3M' | '6M' | '1Y' | 'LIFE'

interface LicenseRow {
  id: number
  machine_hash: string
  plan_code: PlanCode
  status: string
  activated_at: string
  expires_at: string | null
  note: string | null
  revoked_at: string | null
  revoked_reason: string | null
}

const JSON_CONTENT_TYPE = 'application/json; charset=utf-8'
const SHA256_RE = /^[a-f0-9]{64}$/i
const SESSION_COOKIE_NAME = 'flowkit_admin_session'
const SESSION_TTL_SECONDS = 60 * 60 * 12
const textEncoder = new TextEncoder()

const PLAN_ALIAS: Record<string, PlanCode> = {
  'TRIAL_3D': 'TRIAL_3D',
  'TRIAL': 'TRIAL_3D',
  'TRIAL3D': 'TRIAL_3D',
  '3D': 'TRIAL_3D',
  '3DAY': 'TRIAL_3D',
  '3DAYS': 'TRIAL_3D',
  'TRIAL_3_DAYS': 'TRIAL_3D',
  'TRIAL-3DAYS': 'TRIAL_3D',
  '1M': '1M',
  '1_MONTH': '1M',
  'MONTH_1': '1M',
  '3M': '3M',
  '3_MONTH': '3M',
  'MONTH_3': '3M',
  '6M': '6M',
  '6_MONTH': '6M',
  'MONTH_6': '6M',
  '1Y': '1Y',
  '12M': '1Y',
  '1_YEAR': '1Y',
  'YEAR_1': '1Y',
  'LIFE': 'LIFE',
  'LIFETIME': 'LIFE',
  'FOREVER': 'LIFE',
}

const PLAN_LABEL: Record<PlanCode, string> = {
  'TRIAL_3D': 'Trial - 3 ngày',
  '1M': '1 tháng',
  '3M': '3 tháng',
  '6M': '6 tháng',
  '1Y': '1 năm',
  'LIFE': 'Trọn đời',
}

function nowIso(): string {
  return new Date().toISOString()
}

function normalizeMachineId(value: unknown): string {
  if (typeof value !== 'string') return ''
  return value.trim().toUpperCase().replace(/\s+/g, '')
}

function normalizePlan(value: unknown): PlanCode | null {
  if (typeof value !== 'string') return null
  const key = value.trim().toUpperCase()
  return PLAN_ALIAS[key] ?? null
}

function machineHint(machineId: string): string {
  if (!machineId) return 'UNKNOWN'
  if (machineId.length <= 12) return machineId
  return `${machineId.slice(0, 8)}...${machineId.slice(-6)}`
}

function planExpiresAt(plan: PlanCode, activatedAt: string): string | null {
  if (plan === 'LIFE') return null
  if (plan === 'TRIAL_3D') {
    const trialEnd = new Date(activatedAt)
    trialEnd.setUTCDate(trialEnd.getUTCDate() + 3)
    return trialEnd.toISOString()
  }
  const months = plan === '1M' ? 1 : plan === '3M' ? 3 : plan === '6M' ? 6 : 12
  const base = new Date(activatedAt)
  const originalDay = base.getUTCDate()
  base.setUTCMonth(base.getUTCMonth() + months)
  if (base.getUTCDate() < originalDay) {
    base.setUTCDate(0)
  }
  return base.toISOString()
}

function resolveCorsOrigin(req: Request, env: Env): string {
  const configured = (env.CORS_ORIGIN ?? '*').trim()
  if (!configured || configured === '*') return '*'
  const allowed = configured.split(',').map((v) => v.trim()).filter(Boolean)
  const requestOrigin = req.headers.get('Origin') ?? ''
  if (requestOrigin && allowed.includes(requestOrigin)) return requestOrigin
  return allowed[0] ?? '*'
}

function withCors(req: Request, env: Env, headers?: Headers): Headers {
  const result = headers ?? new Headers()
  const origin = resolveCorsOrigin(req, env)
  result.set('Access-Control-Allow-Origin', origin)
  result.set('Access-Control-Allow-Headers', 'authorization, content-type, x-admin-user')
  result.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  result.set('Vary', 'Origin')
  return result
}

function json(req: Request, env: Env, payload: unknown, status = 200): Response {
  const headers = withCors(req, env)
  headers.set('Content-Type', JSON_CONTENT_TYPE)
  return new Response(JSON.stringify(payload), { status, headers })
}

function html(req: Request, env: Env, body: string, status = 200): Response {
  const headers = withCors(req, env)
  headers.set('Content-Type', 'text/html; charset=utf-8')
  headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
  headers.set('Pragma', 'no-cache')
  headers.set('Expires', '0')
  return new Response(body, { status, headers })
}

function unauthorized(req: Request, env: Env): Response {
  return json(req, env, { error: 'UNAUTHORIZED' }, 401)
}

function hasPasswordLoginConfigured(env: Env): boolean {
  return Boolean((env.ADMIN_USERNAME ?? '').trim() && (env.ADMIN_PASSWORD ?? '').trim())
}

function getSessionSecret(env: Env): string {
  return (env.SESSION_SECRET ?? env.ADMIN_TOKEN ?? '').trim()
}

function normalizeBase64Url(input: string): string {
  return input.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function toBase64UrlFromBytes(bytes: Uint8Array): string {
  let binary = ''
  bytes.forEach((b) => { binary += String.fromCharCode(b) })
  return normalizeBase64Url(btoa(binary))
}

function toBase64UrlFromText(value: string): string {
  return toBase64UrlFromBytes(textEncoder.encode(value))
}

function fromBase64UrlToText(value: string): string | null {
  try {
    const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4 || 4)) % 4)
    const raw = atob(padded)
    const bytes = new Uint8Array(raw.length)
    for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i)
    return new TextDecoder().decode(bytes)
  } catch {
    return null
  }
}

async function signHmacSha256(secret: string, data: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    textEncoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const signature = await crypto.subtle.sign('HMAC', key, textEncoder.encode(data))
  return toBase64UrlFromBytes(new Uint8Array(signature))
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return diff === 0
}

function parseCookies(req: Request): Record<string, string> {
  const raw = req.headers.get('Cookie') ?? ''
  const pairs = raw.split(';').map((v) => v.trim()).filter(Boolean)
  const result: Record<string, string> = {}
  pairs.forEach((entry) => {
    const idx = entry.indexOf('=')
    if (idx <= 0) return
    const key = entry.slice(0, idx).trim()
    const val = entry.slice(idx + 1).trim()
    result[key] = decodeURIComponent(val)
  })
  return result
}

interface SessionPayload {
  u: string
  iat: number
  exp: number
}

async function createSessionToken(env: Env, username: string): Promise<string | null> {
  const secret = getSessionSecret(env)
  if (!secret) return null
  const now = Math.floor(Date.now() / 1000)
  const payload: SessionPayload = {
    u: username,
    iat: now,
    exp: now + SESSION_TTL_SECONDS,
  }
  const payloadB64 = toBase64UrlFromText(JSON.stringify(payload))
  const signature = await signHmacSha256(secret, payloadB64)
  return `${payloadB64}.${signature}`
}

async function verifySessionToken(env: Env, token: string): Promise<SessionPayload | null> {
  const secret = getSessionSecret(env)
  if (!secret) return null
  const [payloadB64, signature] = token.split('.')
  if (!payloadB64 || !signature) return null
  const expected = await signHmacSha256(secret, payloadB64)
  if (!timingSafeEqual(expected, signature)) return null
  const decoded = fromBase64UrlToText(payloadB64)
  if (!decoded) return null
  try {
    const payload = JSON.parse(decoded) as Partial<SessionPayload>
    const username = (payload.u ?? '').trim()
    const exp = Number(payload.exp ?? 0)
    const iat = Number(payload.iat ?? 0)
    if (!username || Number.isNaN(exp) || Number.isNaN(iat)) return null
    if (Math.floor(Date.now() / 1000) >= exp) return null
    return { u: username, exp, iat }
  } catch {
    return null
  }
}

async function getSessionFromRequest(req: Request, env: Env): Promise<SessionPayload | null> {
  const token = parseCookies(req)[SESSION_COOKIE_NAME]
  if (!token) return null
  return verifySessionToken(env, token)
}

function buildSessionCookie(req: Request, token: string): string {
  const isSecure = new URL(req.url).protocol === 'https:'
  const parts = [
    `${SESSION_COOKIE_NAME}=${encodeURIComponent(token)}`,
    'Path=/',
    `Max-Age=${SESSION_TTL_SECONDS}`,
    'HttpOnly',
    'SameSite=Strict',
  ]
  if (isSecure) parts.push('Secure')
  return parts.join('; ')
}

function buildClearSessionCookie(req: Request): string {
  const isSecure = new URL(req.url).protocol === 'https:'
  const parts = [
    `${SESSION_COOKIE_NAME}=`,
    'Path=/',
    'Max-Age=0',
    'HttpOnly',
    'SameSite=Strict',
  ]
  if (isSecure) parts.push('Secure')
  return parts.join('; ')
}

async function isAdminAuthorized(req: Request, env: Env): Promise<boolean> {
  const session = await getSessionFromRequest(req, env)
  if (hasPasswordLoginConfigured(env)) {
    return Boolean(session && session.u === (env.ADMIN_USERNAME ?? '').trim())
  }

  const expected = (env.ADMIN_TOKEN ?? '').trim()
  const auth = req.headers.get('Authorization') ?? ''
  const token = auth.replace(/^Bearer\s+/i, '').trim()
  if (expected && token.length > 0 && token === expected) return true

  return Boolean(session)
}

async function sha256Hex(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

async function machineHashFromInput(machineIdInput: string): Promise<string> {
  if (SHA256_RE.test(machineIdInput)) {
    return machineIdInput.toLowerCase()
  }
  return sha256Hex(machineIdInput)
}

async function parseJsonBody<T>(req: Request): Promise<T | null> {
  try {
    return (await req.json()) as T
  } catch {
    return null
  }
}

async function upsertDevice(
  env: Env,
  machineHash: string,
  hint: string,
  machineId?: string,
  appVersion?: string,
  platform?: string,
): Promise<void> {
  const ts = nowIso()
  await env.LICENSE_DB.prepare(
    `
    INSERT INTO devices (
      machine_hash, machine_hint, machine_id, first_seen, last_seen, last_app_version, last_platform
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(machine_hash) DO UPDATE SET
      machine_hint = excluded.machine_hint,
      machine_id = excluded.machine_id,
      last_seen = excluded.last_seen,
      last_app_version = excluded.last_app_version,
      last_platform = excluded.last_platform
    `,
  )
    .bind(machineHash, hint, machineId ?? null, ts, ts, appVersion ?? null, platform ?? null)
    .run()
}

async function getActiveLicense(env: Env, machineHash: string): Promise<LicenseRow | null> {
  return env.LICENSE_DB.prepare(
    `
    SELECT id, machine_hash, plan_code, status, activated_at, expires_at, note, revoked_at, revoked_reason
    FROM licenses
    WHERE machine_hash = ? AND status = 'ACTIVE'
    ORDER BY id DESC
    LIMIT 1
    `,
  )
    .bind(machineHash)
    .first<LicenseRow>()
}

async function getLatestLicense(env: Env, machineHash: string): Promise<LicenseRow | null> {
  return env.LICENSE_DB.prepare(
    `
    SELECT id, machine_hash, plan_code, status, activated_at, expires_at, note, revoked_at, revoked_reason
    FROM licenses
    WHERE machine_hash = ?
    ORDER BY id DESC
    LIMIT 1
    `,
  )
    .bind(machineHash)
    .first<LicenseRow>()
}

function isExpired(expiresAt: string | null, referenceIso: string): boolean {
  if (!expiresAt) return false
  return new Date(expiresAt).getTime() <= new Date(referenceIso).getTime()
}

async function audit(env: Env, actor: string, action: string, machineHash?: string | null, detail?: unknown): Promise<void> {
  await env.LICENSE_DB.prepare(
    `
    INSERT INTO audit_logs (actor, action, machine_hash, detail_json, created_at)
    VALUES (?, ?, ?, ?, ?)
    `,
  )
    .bind(actor, action, machineHash ?? null, detail ? JSON.stringify(detail) : null, nowIso())
    .run()
}

async function handleDeviceCheck(req: Request, env: Env): Promise<Response> {
  const body = await parseJsonBody<{
    machine_id?: string
    app_version?: string
    platform?: string
  }>(req)
  const machineId = normalizeMachineId(body?.machine_id)
  if (!machineId || machineId.length < 8) {
    return json(req, env, { error: 'INVALID_MACHINE_ID' }, 400)
  }

  const hash = await machineHashFromInput(machineId)
  await upsertDevice(env, hash, machineHint(machineId), machineId, body?.app_version, body?.platform)

  const currentTime = nowIso()
  let active = await getActiveLicense(env, hash)

  if (active && isExpired(active.expires_at, currentTime)) {
    await env.LICENSE_DB.prepare(
      `
      UPDATE licenses
      SET status = 'EXPIRED'
      WHERE id = ? AND status = 'ACTIVE'
      `,
    ).bind(active.id).run()
    await audit(env, 'system', 'license_expired', hash, { license_id: active.id })
    active = null
  }

  if (active) {
    return json(req, env, {
      allowed: true,
      status: 'ACTIVE',
      plan_code: active.plan_code,
      plan_label: PLAN_LABEL[active.plan_code],
      activated_at: active.activated_at,
      expires_at: active.expires_at,
      revoked_reason: null,
      machine_hash: hash,
      server_time: currentTime,
    })
  }

  const latest = await getLatestLicense(env, hash)
  const fallbackStatus = latest?.status ?? 'PENDING'
  const message = fallbackStatus === 'REVOKED'
    ? latest?.revoked_reason
      ? `License đã bị thu hồi: ${latest.revoked_reason}`
      : 'License đã bị thu hồi. Liên hệ quản trị viên.'
    : fallbackStatus === 'EXPIRED'
      ? 'License đã hết hạn. Vui lòng gia hạn.'
      : 'Thiết bị chưa được active trong CMS.'

  return json(req, env, {
    allowed: false,
    status: fallbackStatus,
    plan_code: latest?.plan_code ?? null,
    plan_label: latest?.plan_code ? PLAN_LABEL[latest.plan_code] : null,
    activated_at: latest?.activated_at ?? null,
    expires_at: latest?.expires_at ?? null,
    revoked_reason: latest?.revoked_reason ?? null,
    machine_hash: hash,
    server_time: currentTime,
    message,
  })
}

async function handleAdminListDevices(req: Request, env: Env): Promise<Response> {
  const url = new URL(req.url)
  const limit = Math.max(1, Math.min(500, Number.parseInt(url.searchParams.get('limit') ?? '200', 10) || 200))
  const { results } = await env.LICENSE_DB.prepare(
    `
    SELECT
      d.machine_hash,
      d.machine_hint,
      d.machine_id,
      d.first_seen,
      d.last_seen,
      d.last_app_version,
      d.last_platform,
      l.plan_code,
      l.status AS license_status,
      l.activated_at,
      l.expires_at,
      l.revoked_at,
      l.revoked_reason
    FROM devices d
    LEFT JOIN licenses l ON l.id = (
      SELECT id FROM licenses
      WHERE machine_hash = d.machine_hash
      ORDER BY id DESC
      LIMIT 1
    )
    ORDER BY d.last_seen DESC
    LIMIT ?
    `,
  )
    .bind(limit)
    .all()

  return json(req, env, {
    items: results ?? [],
    total: results?.length ?? 0,
  })
}

async function handleAdminListLicenses(req: Request, env: Env): Promise<Response> {
  const url = new URL(req.url)
  const limit = Math.max(1, Math.min(1000, Number.parseInt(url.searchParams.get('limit') ?? '300', 10) || 300))
  const { results } = await env.LICENSE_DB.prepare(
    `
    SELECT
      id,
      machine_hash,
      plan_code,
      status,
      activated_at,
      expires_at,
      created_by,
      note,
      revoked_at,
      revoked_reason
    FROM licenses
    ORDER BY id DESC
    LIMIT ?
    `,
  )
    .bind(limit)
    .all()

  return json(req, env, {
    items: results ?? [],
    total: results?.length ?? 0,
  })
}

async function handleAdminActivate(req: Request, env: Env): Promise<Response> {
  const body = await parseJsonBody<{
    machine_id?: string
    plan?: string
    note?: string
    actor?: string
  }>(req)
  const machineId = normalizeMachineId(body?.machine_id)
  if (!machineId) return json(req, env, { error: 'MACHINE_ID_REQUIRED' }, 400)

  const plan = normalizePlan(body?.plan)
  if (!plan) return json(req, env, { error: 'INVALID_PLAN' }, 400)

  const hash = await machineHashFromInput(machineId)
  const hint = SHA256_RE.test(machineId) ? `${machineId.slice(0, 8)}...` : machineHint(machineId)
  const actor = (body?.actor?.trim() || req.headers.get('x-admin-user') || 'admin').slice(0, 120)
  const activatedAt = nowIso()
  const expiresAt = planExpiresAt(plan, activatedAt)

  await upsertDevice(env, hash, hint, machineId)
  await env.LICENSE_DB.prepare(
    `
    UPDATE licenses
    SET status = 'REVOKED', revoked_at = ?, revoked_reason = 'Replaced by new activation'
    WHERE machine_hash = ? AND status = 'ACTIVE'
    `,
  )
    .bind(activatedAt, hash)
    .run()

  const inserted = await env.LICENSE_DB.prepare(
    `
    INSERT INTO licenses (
      machine_hash, plan_code, status, activated_at, expires_at, created_by, note
    ) VALUES (?, ?, 'ACTIVE', ?, ?, ?, ?)
    RETURNING id, machine_hash, plan_code, status, activated_at, expires_at, created_by, note
    `,
  )
    .bind(hash, plan, activatedAt, expiresAt, actor, body?.note?.trim() || null)
    .first<Record<string, unknown>>()

  await audit(env, actor, 'license_activate', hash, {
    plan_code: plan,
    expires_at: expiresAt,
    note: body?.note ?? null,
  })

  return json(req, env, {
    ok: true,
    item: inserted,
  })
}

async function handleAdminRevoke(req: Request, env: Env): Promise<Response> {
  const body = await parseJsonBody<{
    machine_id?: string
    reason?: string
    actor?: string
  }>(req)
  const machineId = normalizeMachineId(body?.machine_id)
  if (!machineId) return json(req, env, { error: 'MACHINE_ID_REQUIRED' }, 400)

  const hash = await machineHashFromInput(machineId)
  const actor = (body?.actor?.trim() || req.headers.get('x-admin-user') || 'admin').slice(0, 120)
  const reason = body?.reason?.trim() || 'Revoked by admin'
  const revokedAt = nowIso()

  const result = await env.LICENSE_DB.prepare(
    `
    UPDATE licenses
    SET status = 'REVOKED', revoked_at = ?, revoked_reason = ?
    WHERE machine_hash = ? AND status = 'ACTIVE'
    `,
  )
    .bind(revokedAt, reason, hash)
    .run()

  await audit(env, actor, 'license_revoke', hash, {
    reason,
    changed: result.meta.changes,
  })

  return json(req, env, {
    ok: true,
    changed: result.meta.changes,
  })
}

async function handleAdminSession(req: Request, env: Env): Promise<Response> {
  const session = await getSessionFromRequest(req, env)
  if (!session) {
    return json(req, env, { authenticated: false })
  }
  return json(req, env, {
    authenticated: true,
    username: session.u,
  })
}

async function handleAdminLogin(req: Request, env: Env): Promise<Response> {
  if (!hasPasswordLoginConfigured(env)) {
    return json(req, env, { error: 'ADMIN_LOGIN_NOT_CONFIGURED' }, 503)
  }

  const body = await parseJsonBody<{ username?: string; password?: string }>(req)
  const username = (body?.username ?? '').trim()
  const password = (body?.password ?? '').trim()
  const expectedUsername = (env.ADMIN_USERNAME ?? '').trim()
  const expectedPassword = (env.ADMIN_PASSWORD ?? '').trim()

  if (!username || !password) {
    return json(req, env, { error: 'USERNAME_PASSWORD_REQUIRED' }, 400)
  }
  if (username !== expectedUsername || password !== expectedPassword) {
    return json(req, env, { error: 'INVALID_CREDENTIALS' }, 401)
  }

  const token = await createSessionToken(env, username)
  if (!token) {
    return json(req, env, { error: 'SESSION_SECRET_NOT_CONFIGURED' }, 503)
  }

  const headers = withCors(req, env)
  headers.set('Content-Type', JSON_CONTENT_TYPE)
  headers.append('Set-Cookie', buildSessionCookie(req, token))
  return new Response(JSON.stringify({ ok: true, username }), { status: 200, headers })
}

function handleAdminLogout(req: Request, env: Env): Response {
  const headers = withCors(req, env)
  headers.set('Content-Type', JSON_CONTENT_TYPE)
  headers.append('Set-Cookie', buildClearSessionCookie(req))
  return new Response(JSON.stringify({ ok: true }), { status: 200, headers })
}

function renderAdminHtml(): string {
  return `<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>FlowKit License CMS</title>
    <style>
      :root { --bg:#f4f6fb; --card:#fff; --text:#0f172a; --muted:#64748b; --line:#e2e8f0; --primary:#2563eb; --danger:#dc2626; --success:#166534; --warning:#a16207; }
      * { box-sizing: border-box; }
      body { margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; color:var(--text); background:var(--bg); }
      .hidden { display:none !important; }
      .wrap { max-width: 1280px; margin: 0 auto; padding: 20px; display:grid; gap:16px; }
      .login-wrap { min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
      .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; }
      .title { margin:0; font-size:20px; font-weight:700; letter-spacing:.01em; }
      .subtitle { margin:4px 0 0 0; color:var(--muted); font-size:13px; }
      .muted { color:var(--muted); font-size:12px; }
      .grid { display:grid; gap:10px; }
      .grid-2 { grid-template-columns: repeat(2, minmax(0,1fr)); }
      .grid-3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
      .grid-4 { grid-template-columns: repeat(4, minmax(0,1fr)); }
      @media (max-width: 1080px) { .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } }
      label { display:block; font-size:12px; margin-bottom:4px; color:var(--muted); font-weight:600; }
      input, select, button, textarea { width:100%; padding:9px 10px; border:1px solid var(--line); border-radius:8px; font-size:13px; }
      textarea { min-height: 70px; resize: vertical; }
      button { cursor:pointer; background:#fff; font-weight:600; }
      button.primary { background:var(--primary); color:#fff; border-color:var(--primary); }
      button.danger { background:var(--danger); color:#fff; border-color:var(--danger); }
      button.ghost { background:#fff; color:var(--text); }
      .row { display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end; }
      .row > * { flex: 1 1 180px; }
      .status { padding:10px 12px; border-radius:8px; font-size:12px; background:#eef2ff; color:#3730a3; border:1px solid #dbe4ff; }
      .topbar { display:flex; align-items:center; justify-content:space-between; gap:12px; }
      .topbar-actions { display:flex; gap:8px; }
      .stat-grid { display:grid; gap:10px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .stat { border:1px solid var(--line); border-radius:10px; padding:10px; background:#fff; }
      .stat-label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
      .stat-value { margin-top:4px; font-size:22px; font-weight:700; }
      .badge { display:inline-flex; align-items:center; padding:3px 8px; border-radius:999px; font-size:11px; border:1px solid var(--line); background:#fff; }
      .badge.active { color:var(--success); border-color:#bbf7d0; background:#f0fdf4; }
      .badge.revoked { color:#991b1b; border-color:#fecaca; background:#fef2f2; }
      .badge.pending { color:#334155; border-color:#cbd5e1; background:#f8fafc; }
      .badge.expired { color:var(--warning); border-color:#fde68a; background:#fffbeb; }
      .badge.error { color:#7e22ce; border-color:#ddd6fe; background:#f5f3ff; }
      table { width:100%; border-collapse:collapse; font-size:12px; }
      th, td { border-bottom:1px solid var(--line); padding:8px; text-align:left; vertical-align:top; }
      th { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
      tr.row-revoked { background:#fff7f7; }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:11px; }
      .copy-btn { width:auto; padding:4px 8px; font-size:11px; border-radius:6px; }
      .device-actions { display:flex; gap:6px; flex-wrap:wrap; }
      .mini-btn { width:auto; padding:4px 8px; font-size:11px; border-radius:6px; font-weight:700; }
      .mini-btn.active { border-color:#93c5fd; background:#eff6ff; color:#1d4ed8; }
      .mini-btn.revoked { border-color:#fca5a5; background:#fef2f2; color:#991b1b; }
      .filter-row { display:flex; gap:8px; flex-wrap:wrap; }
      .filter-row button { width:auto; padding:6px 10px; font-size:12px; }
      .filter-row button.active { background:var(--primary); border-color:var(--primary); color:#fff; }
      .login-card { width:100%; max-width:440px; padding:18px; }
      .error-msg { margin-top:8px; font-size:12px; color:#991b1b; }
    </style>
  </head>
  <body>
    <section id="loginView" class="login-wrap">
      <div class="card login-card">
        <h1 class="title">FlowKit License CMS</h1>
        <p class="subtitle">Đăng nhập quản trị để vào dashboard license thiết bị.</p>
        <div class="grid" style="margin-top:14px;">
          <div>
            <label>Username</label>
            <input id="username" autocomplete="username" placeholder="Nhập username admin" />
          </div>
          <div>
            <label>Password</label>
            <input id="password" type="password" autocomplete="current-password" placeholder="Nhập password admin" />
          </div>
          <button id="loginBtn" class="primary">Đăng nhập</button>
          <div id="loginError" class="error-msg hidden"></div>
        </div>
      </div>
    </section>

    <section id="dashboardView" class="hidden">
      <div class="wrap">
        <div class="card topbar">
          <div>
            <h1 class="title">FlowKit License Dashboard</h1>
            <p class="subtitle">Quản lý kích hoạt theo Machine ID và xử lý REVOKED rõ ràng.</p>
          </div>
          <div class="topbar-actions">
            <button id="reloadAll" class="ghost">Refresh dữ liệu</button>
            <button id="logoutBtn">Đăng xuất</button>
          </div>
        </div>

        <div id="status" class="status">Sẵn sàng.</div>

        <div id="summaryStats" class="stat-grid"></div>

        <div class="card grid">
          <h2 style="margin:0;font-size:16px;">Kích hoạt / Thu hồi</h2>
          <div class="grid grid-4">
            <div>
              <label>Machine ID</label>
              <input id="machineId" placeholder="Paste machine id từ app (ví dụ: FKM-...)" />
            </div>
            <div>
              <label>Gói</label>
              <select id="plan">
                <option value="TRIAL_3D">Trial - 3 ngày</option>
                <option value="1M">1 tháng</option>
                <option value="3M">3 tháng</option>
                <option value="6M">6 tháng</option>
                <option value="1Y">1 năm</option>
                <option value="LIFE">Trọn đời</option>
              </select>
            </div>
            <div>
              <label>Actor</label>
              <input id="actor" placeholder="admin" value="admin" />
            </div>
            <div>
              <label>Ghi chú kích hoạt</label>
              <input id="note" placeholder="optional" />
            </div>
          </div>
          <div class="grid grid-2">
            <div>
              <label>REVOKED reason</label>
              <input id="revokeReason" placeholder="Ví dụ: Chargeback / Suspicious activity / Requested by owner" value="Revoked from CMS" />
            </div>
            <div>
              <label>Preset reason</label>
              <select id="revokePreset">
                <option value="">-- chọn nhanh lý do --</option>
                <option value="Payment overdue">Payment overdue</option>
                <option value="Suspicious usage">Suspicious usage</option>
                <option value="User requested revoke">User requested revoke</option>
                <option value="Device changed">Device changed</option>
              </select>
            </div>
          </div>
          <div class="row">
            <button id="activate" class="primary">Active License</button>
            <button id="revoke" class="danger">Set REVOKED</button>
          </div>
        </div>

        <div class="card">
          <h2 style="margin:0 0 10px 0;font-size:16px;">Thiết bị</h2>
          <div style="overflow:auto">
            <table id="devicesTable">
              <thead>
                <tr>
                  <th>Machine ID</th>
                  <th>Status</th>
                  <th>Plan</th>
                  <th>REVOKED</th>
                  <th>Expires</th>
                  <th>Last Seen</th>
                  <th>Client</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="row" style="align-items:center;">
            <h2 style="margin:0;font-size:16px;flex:1 1 auto;">Lịch sử license</h2>
            <div class="filter-row">
              <button id="filterAll" class="active">All</button>
              <button id="filterActive">ACTIVE</button>
              <button id="filterRevoked">REVOKED</button>
              <button id="filterExpired">EXPIRED</button>
            </div>
          </div>
          <div style="overflow:auto; margin-top:8px;">
            <table id="licensesTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Machine Hash</th>
                  <th>Status</th>
                  <th>Plan</th>
                  <th>Activated</th>
                  <th>Expires</th>
                  <th>Revoked</th>
                  <th>Reason</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <script>
      const el = (id) => document.getElementById(id)
      const statusEl = el('status')
      const loginView = el('loginView')
      const dashboardView = el('dashboardView')
      const loginError = el('loginError')
      const summaryStats = el('summaryStats')
      let licensesCache = []
      let licenseFilter = 'ALL'

      function setStatus(text, kind) {
        if (!statusEl) return
        statusEl.textContent = text
        statusEl.style.background = kind === 'error' ? '#fee2e2' : kind === 'ok' ? '#dcfce7' : '#eef2ff'
        statusEl.style.color = kind === 'error' ? '#991b1b' : kind === 'ok' ? '#166534' : '#3730a3'
      }

      function setLoginError(text) {
        if (!loginError) return
        if (!text) {
          loginError.classList.add('hidden')
          loginError.textContent = ''
          return
        }
        loginError.textContent = text
        loginError.classList.remove('hidden')
      }

      function setView(authenticated) {
        if (authenticated) {
          loginView.classList.add('hidden')
          dashboardView.classList.remove('hidden')
        } else {
          dashboardView.classList.add('hidden')
          loginView.classList.remove('hidden')
        }
      }

      function escapeHtml(value) {
        const v = value == null ? '' : String(value)
        return v
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\"/g, '&quot;')
          .replace(/'/g, '&#039;')
      }

      function statusBadge(status) {
        const s = (status || 'PENDING').toUpperCase()
        const cls = s === 'ACTIVE' ? 'active'
          : s === 'REVOKED' ? 'revoked'
          : s === 'EXPIRED' ? 'expired'
          : s === 'ERROR' ? 'error'
          : 'pending'
        return '<span class="badge ' + cls + '">' + escapeHtml(s) + '</span>'
      }

      async function api(path, options) {
        const headers = Object.assign(
          { 'Content-Type': 'application/json' },
          (options && options.headers) || {}
        )
        const response = await fetch(path, Object.assign({}, options || {}, { headers, credentials: 'include' }))
        let data
        try { data = await response.json() } catch { data = null }
        if (!response.ok) {
          if (response.status === 401) {
            setView(false)
          }
          const msg = (data && (data.error || data.message)) || ('HTTP ' + response.status)
          throw new Error(msg)
        }
        return data
      }

      function fmt(v) {
        if (!v) return '-'
        const d = new Date(v)
        if (Number.isNaN(d.getTime())) return String(v)
        return d.toLocaleString()
      }

      function renderSummary(devices, licenses) {
        const totalDevices = devices.length
        const activeLicenses = licenses.filter((x) => (x.status || '').toUpperCase() === 'ACTIVE').length
        const revokedLicenses = licenses.filter((x) => (x.status || '').toUpperCase() === 'REVOKED').length
        const expiredLicenses = licenses.filter((x) => (x.status || '').toUpperCase() === 'EXPIRED').length

        summaryStats.innerHTML = [
          ['Total Devices', totalDevices],
          ['ACTIVE', activeLicenses],
          ['REVOKED', revokedLicenses],
          ['EXPIRED', expiredLicenses],
        ].map(([label, value]) => (
          '<div class="stat"><div class="stat-label">' + escapeHtml(label) + '</div><div class="stat-value">' + escapeHtml(value) + '</div></div>'
        )).join('')
      }

      function renderDevices(items) {
        const tbody = document.querySelector('#devicesTable tbody')
        tbody.innerHTML = ''
        for (const item of items) {
          const isRevoked = (item.license_status || '').toUpperCase() === 'REVOKED'
          const machineActionId = item.machine_id || item.machine_hash || ''
          const machineId = item.machine_id || item.machine_hint || machineActionId || '-'
          const revokedInfo = isRevoked
            ? ('<div>' + fmt(item.revoked_at) + '</div><div class="muted">' + escapeHtml(item.revoked_reason || '-') + '</div>')
            : '-'
          const actionButtons = machineActionId
            ? '<div class="device-actions" style="margin-top:6px;"><button class="mini-btn active" data-device-action="activate" data-machine="' + escapeHtml(machineActionId) + '">Active</button><button class="mini-btn revoked" data-device-action="revoke" data-machine="' + escapeHtml(machineActionId) + '">REVOKED</button></div>'
            : ''

          const tr = document.createElement('tr')
          if (isRevoked) tr.className = 'row-revoked'
          tr.innerHTML = [
            '<td><code>' + escapeHtml(machineId) + '</code><div style="margin-top:6px;"><button class="copy-btn" data-copy="' + escapeHtml(machineId) + '">Copy</button></div>' + actionButtons + '<div class="muted" style="margin-top:6px;"><code>' + escapeHtml((item.machine_hash || '').slice(0, 20)) + '...</code></div></td>',
            '<td>' + statusBadge(item.license_status || 'PENDING') + '</td>',
            '<td>' + escapeHtml(item.plan_code || '-') + '</td>',
            '<td>' + revokedInfo + '</td>',
            '<td>' + fmt(item.expires_at) + '</td>',
            '<td>' + fmt(item.last_seen) + '</td>',
            '<td>' + escapeHtml(item.last_platform || '-') + ' / ' + escapeHtml(item.last_app_version || '-') + '</td>',
          ].join('')
          tbody.appendChild(tr)
        }
      }

      async function activateLicense(machineId) {
        const normalizedMachineId = (machineId || '').trim()
        if (!normalizedMachineId) {
          setStatus('Thiếu Machine ID.', 'error')
          return
        }
        setStatus('Đang active license cho ' + normalizedMachineId + '...', 'info')
        await api('/v1/admin/licenses/activate', {
          method: 'POST',
          body: JSON.stringify({
            machine_id: normalizedMachineId,
            plan: el('plan').value,
            note: el('note').value || null,
            actor: el('actor').value || 'admin',
          }),
        })
        setStatus('Active thành công cho ' + normalizedMachineId + '.', 'ok')
        await reloadAll()
      }

      async function revokeLicense(machineId) {
        const normalizedMachineId = (machineId || '').trim()
        if (!normalizedMachineId) {
          setStatus('Thiếu Machine ID.', 'error')
          return
        }
        const revokeReason = (el('revokeReason').value || '').trim() || 'Revoked from CMS'
        setStatus('Đang revoke license cho ' + normalizedMachineId + '...', 'info')
        await api('/v1/admin/licenses/revoke', {
          method: 'POST',
          body: JSON.stringify({
            machine_id: normalizedMachineId,
            reason: revokeReason,
            actor: el('actor').value || 'admin',
          }),
        })
        setStatus('Đã chuyển trạng thái REVOKED cho ' + normalizedMachineId + '.', 'ok')
        await reloadAll()
      }

      function renderLicenses(items) {
        const tbody = document.querySelector('#licensesTable tbody')
        tbody.innerHTML = ''
        const filtered = items.filter((item) => {
          const status = (item.status || '').toUpperCase()
          if (licenseFilter === 'ALL') return true
          return status === licenseFilter
        })

        for (const item of filtered) {
          const isRevoked = (item.status || '').toUpperCase() === 'REVOKED'
          const tr = document.createElement('tr')
          if (isRevoked) tr.className = 'row-revoked'
          tr.innerHTML = [
            '<td>' + escapeHtml(item.id) + '</td>',
            '<td><code>' + escapeHtml((item.machine_hash || '').slice(0, 20)) + '...</code></td>',
            '<td>' + statusBadge(item.status || '-') + '</td>',
            '<td>' + escapeHtml(item.plan_code || '-') + '</td>',
            '<td>' + fmt(item.activated_at) + '</td>',
            '<td>' + fmt(item.expires_at) + '</td>',
            '<td>' + fmt(item.revoked_at) + '</td>',
            '<td>' + escapeHtml(item.revoked_reason || '-') + '</td>',
            '<td>' + escapeHtml(item.note || '-') + '</td>',
          ].join('')
          tbody.appendChild(tr)
        }
      }

      async function refreshSession() {
        try {
          const session = await api('/v1/admin/session', { method: 'GET' })
          if (session && session.authenticated) {
            setView(true)
            setLoginError('')
            return true
          }
        } catch (_) {}
        setView(false)
        return false
      }

      async function reloadAll() {
        try {
          setStatus('Đang tải dữ liệu...', 'info')
          const [devices, licenses] = await Promise.all([
            api('/v1/admin/devices?limit=300'),
            api('/v1/admin/licenses?limit=500')
          ])
          const deviceItems = devices.items || []
          const licenseItems = licenses.items || []
          licensesCache = licenseItems
          renderSummary(deviceItems, licenseItems)
          renderDevices(deviceItems)
          renderLicenses(licenseItems)
          setStatus('Đã tải dữ liệu mới nhất.', 'ok')
        } catch (err) {
          setStatus(err.message || String(err), 'error')
        }
      }

      function applyFilter(next) {
        licenseFilter = next
        ;['filterAll', 'filterActive', 'filterRevoked', 'filterExpired'].forEach((id) => {
          const node = el(id)
          if (!node) return
          node.classList.toggle('active', id === (
            next === 'ALL' ? 'filterAll'
              : next === 'ACTIVE' ? 'filterActive'
                : next === 'REVOKED' ? 'filterRevoked'
                  : 'filterExpired'
          ))
        })
        renderLicenses(licensesCache)
      }

      el('loginBtn').addEventListener('click', async () => {
        const username = (el('username').value || '').trim()
        const password = (el('password').value || '').trim()
        if (!username || !password) {
          setLoginError('Thiếu username/password.')
          return
        }
        try {
          setLoginError('')
          const result = await api('/v1/admin/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
          })
          setView(true)
          setStatus('Đăng nhập thành công.', 'ok')
          el('actor').value = result.username || username
          await reloadAll()
        } catch (err) {
          setLoginError(err.message || String(err))
        }
      })

      el('logoutBtn').addEventListener('click', async () => {
        try {
          await api('/v1/admin/logout', { method: 'POST' })
          setView(false)
          setLoginError('')
        } catch (err) {
          setStatus(err.message || String(err), 'error')
        }
      })

      el('reloadAll').addEventListener('click', reloadAll)
      el('revokePreset').addEventListener('change', (event) => {
        const value = event.target.value || ''
        if (value) el('revokeReason').value = value
      })

      el('activate').addEventListener('click', async () => {
        const machineId = (el('machineId').value || '').trim()
        try {
          await activateLicense(machineId)
        } catch (err) {
          setStatus(err.message || String(err), 'error')
        }
      })

      el('revoke').addEventListener('click', async () => {
        const machineId = (el('machineId').value || '').trim()
        try {
          await revokeLicense(machineId)
        } catch (err) {
          setStatus(err.message || String(err), 'error')
        }
      })

      el('filterAll').addEventListener('click', () => applyFilter('ALL'))
      el('filterActive').addEventListener('click', () => applyFilter('ACTIVE'))
      el('filterRevoked').addEventListener('click', () => applyFilter('REVOKED'))
      el('filterExpired').addEventListener('click', () => applyFilter('EXPIRED'))

      document.body.addEventListener('click', async (event) => {
        const actionButton = event.target.closest('[data-device-action]')
        if (actionButton) {
          const action = actionButton.getAttribute('data-device-action') || ''
          const machineId = (actionButton.getAttribute('data-machine') || '').trim()
          if (!machineId) {
            setStatus('Thiếu Machine ID trên dòng thiết bị.', 'error')
            return
          }
          el('machineId').value = machineId
          actionButton.disabled = true
          try {
            if (action === 'activate') {
              await activateLicense(machineId)
            } else if (action === 'revoke') {
              await revokeLicense(machineId)
            }
          } catch (err) {
            setStatus(err.message || String(err), 'error')
          } finally {
            actionButton.disabled = false
          }
          return
        }

        const button = event.target.closest('[data-copy]')
        if (!button) return
        const value = button.getAttribute('data-copy') || ''
        if (!value) return
        try {
          await navigator.clipboard.writeText(value)
          setStatus('Đã copy: ' + value, 'ok')
        } catch {
          setStatus('Copy thất bại. Giá trị: ' + value, 'error')
        }
      })

      ;(async () => {
        const isAuthed = await refreshSession()
        applyFilter('ALL')
        if (isAuthed) {
          await reloadAll()
        }
      })()
    </script>
  </body>
</html>`
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url)
    if (req.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: withCors(req, env) })
    }

    if (url.pathname === '/' || url.pathname === '/admin') {
      return html(req, env, renderAdminHtml())
    }

    if (url.pathname === '/v1/health' && req.method === 'GET') {
      return json(req, env, {
        ok: true,
        service: 'flowkit-license',
        time: nowIso(),
      })
    }

    if (url.pathname === '/v1/device/check' && req.method === 'POST') {
      return handleDeviceCheck(req, env)
    }

    if (!url.pathname.startsWith('/v1/admin/')) {
      return json(req, env, { error: 'NOT_FOUND' }, 404)
    }

    if (url.pathname === '/v1/admin/login' && req.method === 'POST') {
      return handleAdminLogin(req, env)
    }
    if (url.pathname === '/v1/admin/logout' && req.method === 'POST') {
      return handleAdminLogout(req, env)
    }
    if (url.pathname === '/v1/admin/session' && req.method === 'GET') {
      return handleAdminSession(req, env)
    }

    if (!(await isAdminAuthorized(req, env))) {
      return unauthorized(req, env)
    }

    if (url.pathname === '/v1/admin/devices' && req.method === 'GET') {
      return handleAdminListDevices(req, env)
    }
    if (url.pathname === '/v1/admin/licenses' && req.method === 'GET') {
      return handleAdminListLicenses(req, env)
    }
    if (url.pathname === '/v1/admin/licenses/activate' && req.method === 'POST') {
      return handleAdminActivate(req, env)
    }
    if (url.pathname === '/v1/admin/licenses/revoke' && req.method === 'POST') {
      return handleAdminRevoke(req, env)
    }

    return json(req, env, { error: 'NOT_FOUND' }, 404)
  },
}
