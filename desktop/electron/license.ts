import { execFile } from 'child_process'
import { createHash } from 'crypto'
import { mkdir, readFile, writeFile } from 'fs/promises'
import os from 'os'
import { dirname } from 'path'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)
const SHA256_RE = /^[a-f0-9]{64}$/i
const MACHINE_ID_PREFIX = 'FKM'
const DEFAULT_TIMEOUT_MS = 7000

export const DEFAULT_LICENSE_API_BASE = 'https://flowkit-license.sitegrows.workers.dev'

export type LicenseStatus = 'ACTIVE' | 'EXPIRED' | 'REVOKED' | 'PENDING' | 'ERROR'

export interface LicenseConfig {
  apiBaseUrl: string
}

export interface LicenseCheckResult {
  allowed: boolean
  status: LicenseStatus
  machineId: string
  machineHash: string | null
  planCode: string | null
  planLabel: string | null
  activatedAt: string | null
  expiresAt: string | null
  revokedReason: string | null
  checkedAt: string
  serverTime: string | null
  source: 'remote' | 'cache'
  apiBaseUrl: string
  message: string
}

interface CachedLicenseRecord extends LicenseCheckResult {
  cacheSavedAt: string
}

let machineIdCache: string | null = null
let machineIdPromise: Promise<string> | null = null

function normalizeApiBaseUrl(raw: string): string {
  const value = (raw || '').trim()
  if (!value) return DEFAULT_LICENSE_API_BASE
  const normalized = value.replace(/\/+$/, '')
  if (/^https?:\/\//i.test(normalized)) return normalized
  return `https://${normalized}`
}

function nowIso(): string {
  return new Date().toISOString()
}

function sha256(input: string): string {
  return createHash('sha256').update(input).digest('hex')
}

function formatMachineId(hash: string): string {
  return `${MACHINE_ID_PREFIX}-${hash.slice(0, 8)}-${hash.slice(8, 16)}-${hash.slice(16, 24)}-${hash.slice(24, 32)}`.toUpperCase()
}

async function readText(path: string): Promise<string | null> {
  try {
    const data = await readFile(path, 'utf-8')
    const value = data.trim()
    return value.length > 0 ? value : null
  } catch {
    return null
  }
}

async function readCommand(command: string, args: string[]): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync(command, args, {
      timeout: 1500,
      maxBuffer: 256 * 1024,
      windowsHide: true,
    })
    const output = stdout.trim()
    return output.length > 0 ? output : null
  } catch {
    return null
  }
}

async function getDarwinSeed(): Promise<string | null> {
  const output = await readCommand('ioreg', ['-rd1', '-c', 'IOPlatformExpertDevice'])
  if (!output) return null
  const match = output.match(/"IOPlatformUUID"\s*=\s*"([^"]+)"/)
  return match?.[1]?.trim() ?? null
}

async function getWindowsSeed(): Promise<string | null> {
  const output = await readCommand('powershell.exe', ['-NoProfile', '-Command', '(Get-CimInstance Win32_ComputerSystemProduct).UUID'])
  if (!output) return null
  const value = output.split(/\r?\n/).map((line) => line.trim()).find((line) => !!line && line.toLowerCase() !== 'uuid')
  return value ?? null
}

async function getLinuxSeed(): Promise<string | null> {
  const fromMachineId = await readText('/etc/machine-id')
  if (fromMachineId) return fromMachineId
  return readText('/var/lib/dbus/machine-id')
}

function fallbackSeed(): string {
  const interfaces = os.networkInterfaces()
  const macs = Object.values(interfaces)
    .flatMap((items) => items ?? [])
    .filter((item) => !item.internal && item.mac && item.mac !== '00:00:00:00:00:00')
    .map((item) => item.mac.toLowerCase())
    .sort()

  return [
    os.platform(),
    os.arch(),
    os.hostname(),
    os.release(),
    macs.join('|'),
  ].join('::')
}

async function resolveMachineSeed(): Promise<string> {
  if (process.platform === 'darwin') {
    const value = await getDarwinSeed()
    if (value) return value
  }

  if (process.platform === 'win32') {
    const value = await getWindowsSeed()
    if (value) return value
  }

  if (process.platform === 'linux') {
    const value = await getLinuxSeed()
    if (value) return value
  }

  return fallbackSeed()
}

export async function getMachineId(): Promise<string> {
  if (machineIdCache) return machineIdCache
  if (machineIdPromise) return machineIdPromise

  machineIdPromise = (async () => {
    const seed = await resolveMachineSeed()
    const hash = sha256(seed)
    const machineId = formatMachineId(hash)
    machineIdCache = machineId
    return machineId
  })().finally(() => {
    machineIdPromise = null
  })

  return machineIdPromise
}

async function readJsonFile<T>(path: string): Promise<T | null> {
  try {
    const raw = await readFile(path, 'utf-8')
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

async function writeJsonFile(path: string, data: unknown): Promise<void> {
  const folder = dirname(path)
  await mkdir(folder, { recursive: true })
  await writeFile(path, JSON.stringify(data, null, 2), 'utf-8')
}

export async function loadLicenseConfig(configPath: string, defaultApiBase: string): Promise<LicenseConfig> {
  const file = await readJsonFile<Partial<LicenseConfig>>(configPath)
  return {
    apiBaseUrl: normalizeApiBaseUrl(file?.apiBaseUrl || defaultApiBase),
  }
}

export async function saveLicenseConfig(configPath: string, apiBaseUrl: string, defaultApiBase: string): Promise<LicenseConfig> {
  const config: LicenseConfig = { apiBaseUrl: normalizeApiBaseUrl(apiBaseUrl || defaultApiBase) }
  await writeJsonFile(configPath, config)
  return config
}

function parseStatus(raw: unknown, allowed: boolean): LicenseStatus {
  const upper = typeof raw === 'string' ? raw.trim().toUpperCase() : ''
  if (upper === 'ACTIVE' || upper === 'EXPIRED' || upper === 'REVOKED' || upper === 'PENDING' || upper === 'ERROR') {
    return upper
  }
  return allowed ? 'ACTIVE' : 'PENDING'
}

function isCacheStillValid(cache: CachedLicenseRecord | null): boolean {
  if (!cache || !cache.allowed || cache.status !== 'ACTIVE') return false
  if (!cache.expiresAt) return true
  const expires = new Date(cache.expiresAt).getTime()
  if (Number.isNaN(expires)) return false
  return expires > Date.now()
}

async function readCache(cachePath: string): Promise<CachedLicenseRecord | null> {
  const cache = await readJsonFile<CachedLicenseRecord>(cachePath)
  if (!cache) return null
  if (cache.status !== 'ACTIVE') return null
  return cache
}

async function saveCache(cachePath: string, result: LicenseCheckResult): Promise<void> {
  if (!result.allowed || result.status !== 'ACTIVE') return
  const payload: CachedLicenseRecord = {
    ...result,
    cacheSavedAt: nowIso(),
  }
  await writeJsonFile(cachePath, payload)
}

function normalizeMachineHash(raw: unknown): string | null {
  if (typeof raw !== 'string') return null
  const value = raw.trim().toLowerCase()
  return SHA256_RE.test(value) ? value : null
}

export async function checkLicense(options: {
  apiBaseUrl: string
  machineId: string
  cachePath: string
  appVersion: string
  platform: string
}): Promise<LicenseCheckResult> {
  const apiBaseUrl = normalizeApiBaseUrl(options.apiBaseUrl)
  const checkedAt = nowIso()
  const body = {
    machine_id: options.machineId,
    app_version: options.appVersion,
    platform: options.platform,
  }

  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)
    let response: Response
    try {
      response = await fetch(`${apiBaseUrl}/v1/device/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
    } finally {
      clearTimeout(timeout)
    }

    const data = await response.json() as Record<string, unknown>
    if (!response.ok) {
      throw new Error(typeof data?.error === 'string' ? data.error : `HTTP_${response.status}`)
    }

    const allowed = Boolean(data.allowed)
    const status = parseStatus(data.status, allowed)
    const result: LicenseCheckResult = {
      allowed,
      status,
      machineId: options.machineId,
      machineHash: normalizeMachineHash(data.machine_hash),
      planCode: typeof data.plan_code === 'string' ? data.plan_code : null,
      planLabel: typeof data.plan_label === 'string' ? data.plan_label : null,
      activatedAt: typeof data.activated_at === 'string' ? data.activated_at : null,
      expiresAt: typeof data.expires_at === 'string' ? data.expires_at : null,
      revokedReason: typeof data.revoked_reason === 'string' ? data.revoked_reason : null,
      checkedAt,
      serverTime: typeof data.server_time === 'string' ? data.server_time : null,
      source: 'remote',
      apiBaseUrl,
      message: typeof data.message === 'string'
        ? data.message
        : allowed
          ? 'License đang hoạt động.'
          : 'Thiết bị chưa được kích hoạt.',
    }

    if (result.allowed && result.status === 'ACTIVE') {
      await saveCache(options.cachePath, result)
    }

    return result
  } catch (error) {
    const cached = await readCache(options.cachePath)
    if (isCacheStillValid(cached)) {
      return {
        ...cached,
        revokedReason: cached.revokedReason ?? null,
        checkedAt,
        source: 'cache',
        apiBaseUrl,
        message: 'Không kết nối được license server. Đang dùng giấy phép đã cache cục bộ.',
      }
    }

    return {
      allowed: false,
      status: 'ERROR',
      machineId: options.machineId,
      machineHash: null,
      planCode: null,
      planLabel: null,
      activatedAt: null,
      expiresAt: null,
      revokedReason: null,
      checkedAt,
      serverTime: null,
      source: 'remote',
      apiBaseUrl,
      message: error instanceof Error ? error.message : 'LICENSE_SERVER_UNREACHABLE',
    }
  }
}
