import { app, BrowserWindow, dialog, ipcMain, Tray, Menu, nativeImage, shell, session, screen, safeStorage } from 'electron'
import { dirname, join } from 'path'
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'fs'
import { sidecar } from './sidecar'
import { checkLicense, DEFAULT_LICENSE_API_BASE, getMachineId, loadLicenseConfig, saveLicenseConfig, type LicenseCheckResult } from './license'

let mainWindow: BrowserWindow | null = null
let flowWindow: BrowserWindow | null = null
let flowSidebarWindow: BrowserWindow | null = null
let tray: Tray | null = null
let flowExtensionId: string | null = null
let flowSessionPartition = ''
let appQuitting = false
let licenseEnforceTimer: ReturnType<typeof setInterval> | null = null
let licenseEnforceInFlight = false
let licenseRevokedLockdown = false
let licenseRevokedNotified = false
let extensionAutoReconnectTimer: ReturnType<typeof setTimeout> | null = null
let extensionAutoReconnectInFlight = false
let extensionAutoReconnectAttempts = 0

// Ensure unique app identity in dev mode to avoid collisions with generic Electron apps.
app.setName('FlowKit')
app.setPath('userData', join(app.getPath('appData'), 'FlowKit'))

const gotSingleInstanceLock = app.requestSingleInstanceLock()
if (!gotSingleInstanceLock) {
    app.quit()
    process.exit(0)
}

const ICON_PATH = join(__dirname, '../../resources/icon.png')
const EXTENSION_PATH = join(process.resourcesPath ?? join(__dirname, '../../..'), 'extension')
const FLOW_URL = 'https://labs.google/fx/tools/flow'
const FLOW_SIDEBAR_RATIO = 0.28
const FLOW_SIDEBAR_MIN = 360
const FLOW_SIDEBAR_MAX = 480
const FLOW_SIDEBAR_GAP = 8
const FLOW_SIDEBAR_MIN_HEIGHT = 560
const FLOW_ACCOUNT_DEFAULT_ID = 'default'
const FLOW_ACCOUNT_DEFAULT_LABEL = 'Tài khoản mặc định'
const FLOW_ACCOUNT_PARTITION_PREFIX = 'persist:flowkit-flow-'
const FLOW_ACCOUNTS_CONFIG_PATH = join(app.getPath('userData'), 'flow-accounts.json')
const FLOW_UI_CONFIG_PATH = join(app.getPath('userData'), 'flow-ui.json')
const LICENSE_CONFIG_PATH = join(app.getPath('userData'), 'license-config.json')
const LICENSE_CACHE_PATH = join(app.getPath('userData'), 'license-cache.json')
const DEFAULT_LICENSE_API = process.env.FLOWKIT_LICENSE_API_BASE ?? DEFAULT_LICENSE_API_BASE
const LICENSE_REVOKE_POLL_MS = 5000
const EXTENSION_AUTO_RECONNECT_MAX_ATTEMPTS = 8

let lastLicenseCheck: LicenseCheckResult | null = null
const refererPatchedPartitions = new Set<string>()
const extensionIdByPartition = new Map<string, string>()

type FlowAccount = {
    id: string
    label: string
    email: string
    passwordEnc: string
    partition: string
    createdAt: string
    updatedAt: string
}

type FlowAccountsConfig = {
    activeAccountId: string
    accounts: FlowAccount[]
}

type FlowUIConfig = {
    sidebarVisible: boolean
}

function nowIso(): string {
    return new Date().toISOString()
}

function normalizeFlowAccountId(raw: unknown): string {
    const cleaned = String(raw ?? '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^[-_]+|[-_]+$/g, '')
    if (!cleaned) return ''
    if (!/^[a-z0-9]/.test(cleaned)) return ''
    return cleaned.slice(0, 40)
}

function deriveFlowAccountId(label: string): string {
    const base = normalizeFlowAccountId(label) || 'account'
    return base
}

function partitionForAccountId(accountId: string): string {
    return `${FLOW_ACCOUNT_PARTITION_PREFIX}${accountId}`
}

function encodeSecret(secret: string): string {
    const plain = String(secret ?? '')
    if (!plain) return ''
    try {
        if (safeStorage.isEncryptionAvailable()) {
            const encrypted = safeStorage.encryptString(plain)
            return `safe:${encrypted.toString('base64')}`
        }
    } catch (err) {
        console.warn('[main] safeStorage encrypt failed, fallback plain:', err)
    }
    return `plain:${Buffer.from(plain, 'utf-8').toString('base64')}`
}

function decodeSecret(cipher: string | null | undefined): string {
    const raw = String(cipher ?? '').trim()
    if (!raw) return ''
    if (raw.startsWith('safe:')) {
        const b64 = raw.slice('safe:'.length).trim()
        if (!b64) return ''
        try {
            const buf = Buffer.from(b64, 'base64')
            if (safeStorage.isEncryptionAvailable()) {
                return safeStorage.decryptString(buf)
            }
        } catch (err) {
            console.warn('[main] safeStorage decrypt failed:', err)
            return ''
        }
        return ''
    }
    if (raw.startsWith('plain:')) {
        const b64 = raw.slice('plain:'.length).trim()
        if (!b64) return ''
        try {
            return Buffer.from(b64, 'base64').toString('utf-8')
        } catch {
            return ''
        }
    }
    // Backward compatibility for old plain values.
    return raw
}

function normalizeFlowAccount(raw: any, index = 0): FlowAccount | null {
    const id = normalizeFlowAccountId(raw?.id) || (index === 0 ? FLOW_ACCOUNT_DEFAULT_ID : '')
    if (!id) return null
    const labelRaw = String(raw?.label ?? '').trim()
    const label = labelRaw || (id === FLOW_ACCOUNT_DEFAULT_ID ? FLOW_ACCOUNT_DEFAULT_LABEL : `Tài khoản ${index + 1}`)
    const email = String(raw?.email ?? '').trim()
    const partitionRaw = String(raw?.partition ?? '').trim()
    const partition = partitionRaw.startsWith('persist:')
        ? partitionRaw
        : partitionForAccountId(id)
    const passwordEnc = String(raw?.passwordEnc ?? '').trim()
    const createdAt = String(raw?.createdAt ?? '').trim() || nowIso()
    const updatedAt = String(raw?.updatedAt ?? '').trim() || createdAt
    return { id, label, email, passwordEnc, partition, createdAt, updatedAt }
}

function defaultFlowAccountsConfig(): FlowAccountsConfig {
    const createdAt = nowIso()
    return {
        activeAccountId: FLOW_ACCOUNT_DEFAULT_ID,
        accounts: [{
            id: FLOW_ACCOUNT_DEFAULT_ID,
            label: FLOW_ACCOUNT_DEFAULT_LABEL,
            email: '',
            passwordEnc: '',
            partition: partitionForAccountId(FLOW_ACCOUNT_DEFAULT_ID),
            createdAt,
            updatedAt: createdAt,
        }],
    }
}

function defaultFlowUIConfig(): FlowUIConfig {
    return { sidebarVisible: true }
}

function normalizeFlowUIConfig(raw: any): FlowUIConfig {
    return {
        sidebarVisible: raw?.sidebarVisible !== false,
    }
}

function normalizeFlowAccountsConfig(raw: any): FlowAccountsConfig {
    const listRaw = Array.isArray(raw?.accounts) ? raw.accounts : []
    const dedup = new Map<string, FlowAccount>()
    listRaw.forEach((row: any, idx: number) => {
        const normalized = normalizeFlowAccount(row, idx)
        if (!normalized) return
        dedup.set(normalized.id, normalized)
    })
    if (!dedup.has(FLOW_ACCOUNT_DEFAULT_ID)) {
        const fallback = defaultFlowAccountsConfig().accounts[0]
        dedup.set(FLOW_ACCOUNT_DEFAULT_ID, fallback)
    }
    const accounts = Array.from(dedup.values())
    const activeCandidate = normalizeFlowAccountId(raw?.activeAccountId)
    const activeAccountId = accounts.some((a) => a.id === activeCandidate)
        ? activeCandidate
        : accounts[0].id
    return { activeAccountId, accounts }
}

function loadFlowAccountsConfig(): FlowAccountsConfig {
    try {
        mkdirSync(dirname(FLOW_ACCOUNTS_CONFIG_PATH), { recursive: true })
        if (!existsSync(FLOW_ACCOUNTS_CONFIG_PATH)) {
            const seeded = defaultFlowAccountsConfig()
            writeFileSync(FLOW_ACCOUNTS_CONFIG_PATH, JSON.stringify(seeded, null, 2), 'utf-8')
            return seeded
        }
        const raw = JSON.parse(readFileSync(FLOW_ACCOUNTS_CONFIG_PATH, 'utf-8'))
        const normalized = normalizeFlowAccountsConfig(raw)
        writeFileSync(FLOW_ACCOUNTS_CONFIG_PATH, JSON.stringify(normalized, null, 2), 'utf-8')
        return normalized
    } catch (err) {
        console.error('[main] Failed to load flow accounts config, fallback default:', err)
        const fallback = defaultFlowAccountsConfig()
        try {
            writeFileSync(FLOW_ACCOUNTS_CONFIG_PATH, JSON.stringify(fallback, null, 2), 'utf-8')
        } catch {
            // no-op
        }
        return fallback
    }
}

let flowAccountsConfig: FlowAccountsConfig = loadFlowAccountsConfig()

function loadFlowUIConfig(): FlowUIConfig {
    try {
        mkdirSync(dirname(FLOW_UI_CONFIG_PATH), { recursive: true })
        if (!existsSync(FLOW_UI_CONFIG_PATH)) {
            const seeded = defaultFlowUIConfig()
            writeFileSync(FLOW_UI_CONFIG_PATH, JSON.stringify(seeded, null, 2), 'utf-8')
            return seeded
        }
        const raw = JSON.parse(readFileSync(FLOW_UI_CONFIG_PATH, 'utf-8'))
        const normalized = normalizeFlowUIConfig(raw)
        writeFileSync(FLOW_UI_CONFIG_PATH, JSON.stringify(normalized, null, 2), 'utf-8')
        return normalized
    } catch (err) {
        console.error('[main] Failed to load flow ui config, fallback default:', err)
        const fallback = defaultFlowUIConfig()
        try {
            writeFileSync(FLOW_UI_CONFIG_PATH, JSON.stringify(fallback, null, 2), 'utf-8')
        } catch {
            // no-op
        }
        return fallback
    }
}

let flowUIConfig: FlowUIConfig = loadFlowUIConfig()
let flowSidebarVisible = flowUIConfig.sidebarVisible

function saveFlowUIConfig(next: FlowUIConfig): FlowUIConfig {
    const normalized = normalizeFlowUIConfig(next)
    flowUIConfig = normalized
    flowSidebarVisible = normalized.sidebarVisible
    mkdirSync(dirname(FLOW_UI_CONFIG_PATH), { recursive: true })
    writeFileSync(FLOW_UI_CONFIG_PATH, JSON.stringify(normalized, null, 2), 'utf-8')
    return normalized
}

function saveFlowAccountsConfig(next: FlowAccountsConfig): FlowAccountsConfig {
    const normalized = normalizeFlowAccountsConfig(next)
    flowAccountsConfig = normalized
    mkdirSync(dirname(FLOW_ACCOUNTS_CONFIG_PATH), { recursive: true })
    writeFileSync(FLOW_ACCOUNTS_CONFIG_PATH, JSON.stringify(normalized, null, 2), 'utf-8')
    return normalized
}

function getFlowAccountById(accountId?: string | null): FlowAccount {
    const desired = normalizeFlowAccountId(accountId ?? '') || flowAccountsConfig.activeAccountId
    return flowAccountsConfig.accounts.find((a) => a.id === desired)
        ?? flowAccountsConfig.accounts[0]
}

function isFlowSidebarActuallyVisible(): boolean {
    return Boolean(flowSidebarWindow && !flowSidebarWindow.isDestroyed() && flowSidebarWindow.isVisible())
}

function getFlowPanelStatePayload() {
    const sidebarAlive = Boolean(flowSidebarWindow && !flowSidebarWindow.isDestroyed())
    const sidebarShown = isFlowSidebarActuallyVisible()
    return {
        // Reflect actual on-screen state (not only requested config state).
        visible: sidebarShown,
        sidebarReady: sidebarAlive,
        flowReady: Boolean(flowWindow && !flowWindow.isDestroyed()),
        requestedVisible: flowSidebarVisible,
    }
}

function emitFlowPanelStateChanged() {
    mainWindow?.webContents.send('flow-panel-state-changed', getFlowPanelStatePayload())
}

// In dev mode, use local extension path
const extensionPath = app.isPackaged
    ? EXTENSION_PATH
    : join(__dirname, '../../../extension')

function patchRefererHeaderForSession(ses: Electron.Session, partitionKey: string) {
    if (refererPatchedPartitions.has(partitionKey)) return
    ses.webRequest.onBeforeSendHeaders(
        { urls: ['https://aisandbox-pa.googleapis.com/*'] },
        (details, callback) => {
            const headers = { ...details.requestHeaders }
            headers['Referer'] = 'https://labs.google/'
            callback({ requestHeaders: headers })
        }
    )
    refererPatchedPartitions.add(partitionKey)
}

function getExtensionsHost(ses: Electron.Session): any {
    return (ses as any).extensions ?? ses
}

async function ensureExtensionLoadedForPartition(ses: Electron.Session, partitionKey: string): Promise<string> {
    const cached = extensionIdByPartition.get(partitionKey)
    if (cached) return cached
    const extHost = getExtensionsHost(ses)
    try {
        const loaded = await extHost.loadExtension(extensionPath, { allowFileAccess: true })
        const id = (loaded as any)?.id ?? ''
        if (!id) throw new Error('Missing extension id')
        extensionIdByPartition.set(partitionKey, id)
        return id
    } catch (err) {
        const all = typeof extHost.getAllExtensions === 'function'
            ? await extHost.getAllExtensions()
            : []
        const existing = Array.isArray(all)
            ? all.find((ext: any) => {
                const p = String(ext?.path ?? '')
                const n = String(ext?.name ?? '').toLowerCase()
                return n.includes('flow kit') || p.includes('/extension') || p.endsWith('\\extension')
            })
            : null
        const id = String(existing?.id ?? '')
        if (id) {
            extensionIdByPartition.set(partitionKey, id)
            return id
        }
        throw err
    }
}

async function unloadExtensionForPartition(partitionKey: string) {
    const id = extensionIdByPartition.get(partitionKey)
    if (!id) return
    try {
        const ses = session.fromPartition(partitionKey)
        const extHost = getExtensionsHost(ses)
        if (typeof extHost.removeExtension === 'function') {
            await extHost.removeExtension(id)
        }
    } catch (err) {
        console.warn('[main] removeExtension failed:', { partitionKey, id, err })
    } finally {
        extensionIdByPartition.delete(partitionKey)
    }
}

async function prepareFlowRuntimeForAccount(accountId?: string | null): Promise<{ account: FlowAccount; flowSession: Electron.Session; extensionId: string }> {
    const account = getFlowAccountById(accountId)
    const partitionKey = account.partition
    const flowSession = session.fromPartition(partitionKey)
    patchRefererHeaderForSession(flowSession, partitionKey)
    const extensionId = await ensureExtensionLoadedForPartition(flowSession, partitionKey)

    if (flowSessionPartition && flowSessionPartition !== partitionKey) {
        await unloadExtensionForPartition(flowSessionPartition)
    }

    flowSessionPartition = partitionKey
    flowExtensionId = extensionId
    if (flowAccountsConfig.activeAccountId !== account.id) {
        saveFlowAccountsConfig({
            ...flowAccountsConfig,
            activeAccountId: account.id,
        })
    }

    return { account, flowSession, extensionId }
}

function calcFlowSidebarWidth(totalWidth: number): number {
    const byRatio = Math.floor(totalWidth * FLOW_SIDEBAR_RATIO)
    return Math.max(FLOW_SIDEBAR_MIN, Math.min(FLOW_SIDEBAR_MAX, byRatio))
}

function layoutFlowWindows() {
    if (!flowWindow || flowWindow.isDestroyed()) return
    if (!flowSidebarWindow || flowSidebarWindow.isDestroyed()) return

    if (!flowSidebarVisible) {
        if (flowSidebarWindow.isVisible()) flowSidebarWindow.hide()
        return
    }

    const flowBounds = flowWindow.getBounds()
    const display = screen.getDisplayMatching(flowBounds)
    const workArea = display.workArea
    const sidebarWidth = calcFlowSidebarWidth(flowBounds.width)
    const sidebarHeight = Math.max(FLOW_SIDEBAR_MIN_HEIGHT, flowBounds.height)
    const rightX = flowBounds.x + flowBounds.width + FLOW_SIDEBAR_GAP
    const leftX = flowBounds.x - sidebarWidth - FLOW_SIDEBAR_GAP
    const canFitRight = rightX + sidebarWidth <= workArea.x + workArea.width
    const canFitLeft = leftX >= workArea.x

    // Prefer non-overlap. If no room beside Flow window, dock as floating window in work area.
    if (!canFitRight && !canFitLeft) {
        const x = Math.max(workArea.x, workArea.x + workArea.width - sidebarWidth)
        const y = Math.max(workArea.y, Math.min(flowBounds.y, workArea.y + workArea.height - sidebarHeight))
        flowSidebarWindow.setBounds({ x, y, width: sidebarWidth, height: sidebarHeight })
        if (flowWindow.isVisible() && !flowSidebarWindow.isVisible()) {
            if (typeof flowSidebarWindow.showInactive === 'function') flowSidebarWindow.showInactive()
            else flowSidebarWindow.show()
        }
        return
    }
    const x = canFitRight ? rightX : leftX

    let y = flowBounds.y
    if (y + sidebarHeight > workArea.y + workArea.height) {
        y = Math.max(workArea.y, workArea.y + workArea.height - sidebarHeight)
    }

    flowSidebarWindow.setBounds({ x, y, width: sidebarWidth, height: sidebarHeight })
    if (flowWindow.isVisible() && !flowSidebarWindow.isVisible()) {
        if (typeof flowSidebarWindow.showInactive === 'function') flowSidebarWindow.showInactive()
        else flowSidebarWindow.show()
    }
}

function createFlowSidebarWindow(showOnReady = false) {
    if (!flowExtensionId) {
        flowSidebarWindow = null
        console.warn('[main] Flow extension ID unavailable — sidebar window disabled')
        return null
    }
    if (flowSidebarWindow && !flowSidebarWindow.isDestroyed()) {
        layoutFlowWindows()
        if (showOnReady && flowSidebarVisible && !flowSidebarWindow.isVisible()) {
            if (typeof flowSidebarWindow.showInactive === 'function') flowSidebarWindow.showInactive()
            else flowSidebarWindow.show()
        }
        return flowSidebarWindow
    }

    flowSidebarWindow = new BrowserWindow({
        width: FLOW_SIDEBAR_MIN,
        height: 900,
        minWidth: FLOW_SIDEBAR_MIN,
        minHeight: FLOW_SIDEBAR_MIN_HEIGHT,
        title: 'Flow Agent',
        backgroundColor: '#0a0f1f',
        autoHideMenuBar: true,
        show: false,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            session: session.fromPartition(flowSessionPartition || getFlowAccountById().partition),
        }
    })
    flowSidebarWindow.setMenuBarVisibility(false)
    flowSidebarWindow.webContents.setWindowOpenHandler(({ url }) => {
        void shell.openExternal(url)
        return { action: 'deny' }
    })

    const sidePanelUrl = `chrome-extension://${flowExtensionId}/side_panel.html`
    flowSidebarWindow.webContents.loadURL(sidePanelUrl).catch((err) => {
        console.error('[main] Failed to load extension sidebar window:', err)
    })
    flowSidebarWindow.webContents.on('did-finish-load', () => {
        console.log('[main] Flow sidebar window loaded:', flowSidebarWindow?.webContents.getURL())
    })
    flowSidebarWindow.webContents.on('did-fail-load', (_e, code, desc, url) => {
        console.error('[main] Flow sidebar window failed:', { code, desc, url })
    })

    flowSidebarWindow.on('close', (event) => {
        if (appQuitting) return
        event.preventDefault()
        flowSidebarWindow?.hide()
        emitFlowPanelStateChanged()
    })

    flowSidebarWindow.on('show', () => emitFlowPanelStateChanged())
    flowSidebarWindow.on('hide', () => emitFlowPanelStateChanged())

    flowSidebarWindow.on('closed', () => {
        flowSidebarWindow = null
        emitFlowPanelStateChanged()
    })

    layoutFlowWindows()
    if (showOnReady && flowSidebarVisible) {
        if (typeof flowSidebarWindow.showInactive === 'function') flowSidebarWindow.showInactive()
        else flowSidebarWindow.show()
    }
    return flowSidebarWindow
}


function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
        backgroundColor: '#eef3fb',
        show: false,
        webPreferences: {
            preload: join(__dirname, '../preload/preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        }
    })

    // Load renderer
    if (process.env.ELECTRON_RENDERER_URL) {
        mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
    } else {
        // electron-vite outputs renderer assets to out/renderer in preview/production
        mainWindow.loadFile(join(__dirname, '../renderer/index.html'), { hash: '/' })
    }

    mainWindow.once('ready-to-show', () => {
        mainWindow?.show()
        mainWindow?.focus()
    })

    // Safety net: ensure dashboard is visible even if ready-to-show is delayed.
    setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed() && !mainWindow.isVisible()) {
            console.warn('[main] Forcing main window show after startup timeout')
            mainWindow.show()
            mainWindow.focus()
        }
    }, 2500)

    mainWindow.webContents.on('did-finish-load', () => {
        console.log('[main] Main window renderer loaded:', mainWindow?.webContents.getURL())
        emitFlowPanelStateChanged()
    })

    mainWindow.webContents.on('did-fail-load', (_e, code, desc, url) => {
        console.error('[main] Main window failed to load:', { code, desc, url })
    })

    mainWindow.on('closed', () => {
        mainWindow = null
    })
}

function createFlowWindow(flowSession: Electron.Session, account: FlowAccount, opts: { focusOnShow?: boolean; revealOnReady?: boolean } = {}) {
    console.log('[main] Creating Flow window')
    const focusOnShow = opts.focusOnShow === true
    const revealOnReady = opts.revealOnReady !== false
    flowWindow = new BrowserWindow({
        width: 1420,
        height: 900,
        minWidth: 1080,
        minHeight: 680,
        title: account?.label ? `Google Flow • ${account.label}` : 'Google Flow',
        backgroundColor: '#0a0f1f',
        show: false,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            session: flowSession,
        }
    })

    flowWindow.loadURL(FLOW_URL).catch((err) => {
        console.error('[main] Failed to load Flow URL:', err)
    })
    flowWindow.webContents.on('did-finish-load', () => {
        console.log('[main] Flow content loaded:', flowWindow?.webContents.getURL())
    })
    flowWindow.webContents.on('did-fail-load', (_e, code, desc, url) => {
        console.error('[main] Flow content failed:', { code, desc, url })
    })
    flowWindow.webContents.setWindowOpenHandler(({ url }) => {
        void shell.openExternal(url)
        return { action: 'deny' }
    })
    flowWindow.once('ready-to-show', () => {
        if (!flowWindow || flowWindow.isDestroyed() || !revealOnReady) return
        if (focusOnShow) {
            flowWindow.show()
            createFlowSidebarWindow(true)
            layoutFlowWindows()
            flowWindow.focus()
            return
        }
        if (typeof flowWindow.showInactive === 'function') flowWindow.showInactive()
        else flowWindow.show()
        createFlowSidebarWindow(true)
        layoutFlowWindows()
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus()
    })

    createFlowSidebarWindow(false)

    layoutFlowWindows()
    flowWindow.on('move', layoutFlowWindows)
    flowWindow.on('resize', layoutFlowWindows)
    flowWindow.on('maximize', layoutFlowWindows)
    flowWindow.on('unmaximize', layoutFlowWindows)
    flowWindow.on('enter-full-screen', layoutFlowWindows)
    flowWindow.on('leave-full-screen', layoutFlowWindows)

    flowWindow.on('close', (event) => {
        if (appQuitting) return
        // Keep Flow session alive for token/captcha; hide instead of destroying.
        event.preventDefault()
        flowWindow?.hide()
        if (flowSidebarWindow && !flowSidebarWindow.isDestroyed()) {
            flowSidebarWindow.hide()
        }
        emitFlowPanelStateChanged()
    })

    flowWindow.on('closed', () => {
        if (flowSidebarWindow && !flowSidebarWindow.isDestroyed()) {
            flowSidebarWindow.destroy()
        }
        flowSidebarWindow = null
        flowWindow = null
        emitFlowPanelStateChanged()
    })

    flowWindow.on('show', () => emitFlowPanelStateChanged())
    flowWindow.on('hide', () => emitFlowPanelStateChanged())
}

function createTray() {
    try {
        const rawIcon = nativeImage.createFromPath(ICON_PATH)
        if (rawIcon.isEmpty()) {
            console.warn('[main] Tray icon is invalid/empty, skipping tray creation:', ICON_PATH)
            return
        }

        const icon = rawIcon.resize({ width: 16, height: 16 })
        tray = new Tray(icon)
        tray.setToolTip('FlowKit')
    } catch (err) {
        console.error('[main] Failed to create tray, continue without tray:', err)
        tray = null
        return
    }

    const updateMenu = (agentStatus: string) => {
        const menu = Menu.buildFromTemplate([
            { label: `FlowKit — ${agentStatus}`, enabled: false },
            { type: 'separator' },
            { label: 'Open Dashboard', click: () => { mainWindow?.show(); mainWindow?.focus() } },
            { label: 'Open Google Flow', click: () => { void openFlowWindow({ focus: true, reveal: true }) } },
            { type: 'separator' },
            { label: 'Quit', click: () => app.quit() }
        ])
        tray?.setContextMenu(menu)
    }

    updateMenu('Starting...')

    // Update tray when agent status changes
    sidecar.on('status', (status: string) => updateMenu(status))

    tray.on('click', () => {
        mainWindow?.show()
        mainWindow?.focus()
    })
}

function destroyFlowWindowsForAccountSwitch() {
    const sidebar = flowSidebarWindow
    flowSidebarWindow = null
    if (sidebar && !sidebar.isDestroyed()) {
        try { sidebar.removeAllListeners('close') } catch { }
        try { sidebar.close() } catch { }
        try { sidebar.destroy() } catch { }
    }

    const flow = flowWindow
    flowWindow = null
    if (flow && !flow.isDestroyed()) {
        try { flow.removeAllListeners('close') } catch { }
        try { flow.close() } catch { }
        try { flow.destroy() } catch { }
    }
}

async function openFlowWindow(options: { focus?: boolean; reveal?: boolean; accountId?: string; forceRecreate?: boolean } = {}) {
    console.log('[main] openFlowWindow invoked')
    const focus = options.focus === true
    const reveal = options.reveal !== false
    const requestedAccount = getFlowAccountById(options.accountId)
    const desiredPartition = requestedAccount.partition
    const previousPartition = flowSessionPartition

    try {
        await prepareFlowRuntimeForAccount(requestedAccount.id)
    } catch (err) {
        console.error('[main] Failed to prepare Flow runtime:', err)
        throw err
    }

    const sessionChanged = previousPartition !== '' && previousPartition !== desiredPartition
    if (sessionChanged || options.forceRecreate) {
        destroyFlowWindowsForAccountSwitch()
    }

    if (flowWindow && !flowWindow.isDestroyed()) {
        if (!reveal) return
        if (!flowWindow.isVisible()) {
            if (!focus && typeof flowWindow.showInactive === 'function') flowWindow.showInactive()
            else flowWindow.show()
        }
        createFlowSidebarWindow(true)
        layoutFlowWindows()
        if (focus) flowWindow.focus()
        else if (mainWindow && !mainWindow.isDestroyed()) mainWindow.focus()
    } else {
        const activeAccount = getFlowAccountById(requestedAccount.id)
        const flowSession = session.fromPartition(activeAccount.partition)
        createFlowWindow(flowSession, activeAccount, { focusOnShow: focus, revealOnReady: reveal })
    }
}

async function setFlowPanelVisibility(visible: boolean, options?: { persist?: boolean; revealFlowIfNeeded?: boolean }) {
    flowSidebarVisible = visible
    if (options?.persist !== false) {
        saveFlowUIConfig({
            ...flowUIConfig,
            sidebarVisible: visible,
        })
    }

    if (!visible) {
        if (flowSidebarWindow && !flowSidebarWindow.isDestroyed()) {
            flowSidebarWindow.hide()
        }
        emitFlowPanelStateChanged()
        return getFlowPanelStatePayload()
    }

    // Ensure extension/session is prepared before trying to show panel.
    try {
        await prepareFlowRuntimeForAccount(flowAccountsConfig.activeAccountId)
    } catch (err) {
        console.error('[main] Failed to prepare Flow runtime while showing panel:', err)
    }

    if ((!flowWindow || flowWindow.isDestroyed()) && options?.revealFlowIfNeeded) {
        await openFlowWindow({
            focus: false,
            reveal: true,
            accountId: flowAccountsConfig.activeAccountId,
        })
    }

    if (flowWindow && !flowWindow.isDestroyed()) {
        // If Flow window exists but hidden, reveal it to anchor sidebar layout.
        if (!flowWindow.isVisible()) {
            if (typeof flowWindow.showInactive === 'function') flowWindow.showInactive()
            else flowWindow.show()
        }
        createFlowSidebarWindow(true)
        layoutFlowWindows()
        if (flowSidebarWindow && !flowSidebarWindow.isDestroyed() && !flowSidebarWindow.isVisible()) {
            if (typeof flowSidebarWindow.showInactive === 'function') flowSidebarWindow.showInactive()
            else flowSidebarWindow.show()
        }
    }
    emitFlowPanelStateChanged()
    return getFlowPanelStatePayload()
}

function getCurrentFlowSession(): Electron.Session {
    const account = getFlowAccountById()
    const partitionKey = flowSessionPartition || account.partition
    return session.fromPartition(partitionKey)
}

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
}

type ExtensionReconnectResult = {
    ok: boolean
    method?: string
    error?: string
}

async function waitForWebContentsReady(webContents: Electron.WebContents | null | undefined, timeoutMs = 8000): Promise<boolean> {
    if (!webContents || webContents.isDestroyed()) return false
    if (!webContents.isLoadingMainFrame()) return true
    return await new Promise<boolean>((resolve) => {
        let settled = false
        const finish = (ok: boolean) => {
            if (settled) return
            settled = true
            clearTimeout(timer)
            try { webContents.removeListener('did-finish-load', onFinish) } catch { }
            try { webContents.removeListener('did-fail-load', onFail) } catch { }
            resolve(ok)
        }
        const onFinish = () => finish(true)
        const onFail = () => finish(false)
        const timer = setTimeout(() => finish(!webContents.isLoadingMainFrame()), timeoutMs)
        webContents.once('did-finish-load', onFinish)
        webContents.once('did-fail-load', onFail)
    })
}

async function waitForExtensionConnected(timeoutMs = 12000): Promise<boolean> {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        try {
            const res = await fetch('http://127.0.0.1:8100/health', { signal: AbortSignal.timeout(1500) })
            if (res.ok) {
                const health = await res.json() as { extension_connected?: boolean }
                if (Boolean(health?.extension_connected)) return true
            }
        } catch {
            // retry
        }
        await sleep(500)
    }
    return false
}

async function requestExtensionReconnectViaSidebar(): Promise<boolean> {
    const sidebar = createFlowSidebarWindow(false)
    if (!sidebar || sidebar.webContents.isDestroyed()) return false
    const ready = await waitForWebContentsReady(sidebar.webContents, 6000)
    if (!ready) return false
    try {
        const viaSidePanel = await sidebar.webContents.executeJavaScript(`
            new Promise((resolve) => {
                try {
                    chrome.runtime.sendMessage({ type: 'RECONNECT' }, (resp) => {
                        const err = chrome.runtime.lastError;
                        if (err) {
                            resolve({ ok: false, error: err.message || 'runtime_send_failed' });
                            return;
                        }
                        resolve({ ok: !!(resp && resp.ok), raw: resp || null });
                    });
                } catch (e) {
                    resolve({ ok: false, error: e?.message || String(e) });
                }
            });
        `, true) as { ok?: boolean; error?: string } | undefined
        return Boolean(viaSidePanel?.ok)
    } catch (err) {
        console.warn('[main] reconnect via side-panel failed:', err)
        return false
    }
}

function clearExtensionAutoReconnectTimer() {
    if (extensionAutoReconnectTimer) {
        clearTimeout(extensionAutoReconnectTimer)
        extensionAutoReconnectTimer = null
    }
}

async function performExtensionReconnect(): Promise<ExtensionReconnectResult> {
    try {
        // Ensure Flow window (and extension side panel) is alive.
        await openFlowWindow({ focus: false, reveal: false })
        createFlowSidebarWindow(false)
        await waitForWebContentsReady(flowSidebarWindow?.webContents, 6000)
        await waitForWebContentsReady(flowWindow?.webContents, 6000)

        for (let i = 0; i < 3; i += 1) {
            const sent = await requestExtensionReconnectViaSidebar()
            if (sent) {
                const connected = await waitForExtensionConnected(3500)
                if (connected) return { ok: true, method: 'runtimeMessage' }
            }
            await sleep(600)
        }

        // Find the extension background service worker webContents
        const allContents = (session.defaultSession as any).getAllWebContents?.()
            ?? require('electron').webContents.getAllWebContents()
        const bgContents = allContents.find((wc: Electron.WebContents) => {
            const url = wc.getURL?.() ?? ''
            return flowExtensionId
                ? url.includes(`chrome-extension://${flowExtensionId}`) && url.includes('background')
                : url.startsWith('chrome-extension://') && url.includes('background')
        })
        if (bgContents && !bgContents.isDestroyed()) {
            try {
                await bgContents.executeJavaScript(`
                    try {
                        manualDisconnect = false;
                        connectToAgent();
                    } catch(e) {}
                `)
                const connected = await waitForExtensionConnected(4500)
                if (connected) return { ok: true, method: 'executeJavaScript' }
            } catch (err) {
                console.warn('[main] reconnect via background worker failed:', err)
            }
        }

        // Fallback: reload extension via session
        if (flowExtensionId) {
            const flowSession = getCurrentFlowSession()
            const extHost = getExtensionsHost(flowSession)
            if (typeof extHost.reloadExtension === 'function') {
                await extHost.reloadExtension(flowExtensionId)
                // Ensure side panel points to the latest extension runtime.
                if (flowSidebarWindow && !flowSidebarWindow.webContents.isDestroyed()) {
                    const sidePanelUrl = `chrome-extension://${flowExtensionId}/side_panel.html`
                    await flowSidebarWindow.webContents.loadURL(sidePanelUrl)
                    await waitForWebContentsReady(flowSidebarWindow.webContents, 6000)
                }
                const sent = await requestExtensionReconnectViaSidebar()
                const connected = sent ? await waitForExtensionConnected(5000) : false
                if (connected) return { ok: true, method: 'reloadExtension' }
            }
        }
        return { ok: false, error: 'Extension vẫn OFF sau nhiều lần reconnect' }
    } catch (e: any) {
        return { ok: false, error: e?.message ?? String(e) }
    }
}

function scheduleExtensionAutoReconnect(reason: string, delayMs = 800) {
    if (licenseRevokedLockdown) return
    if (extensionAutoReconnectInFlight) return
    if (extensionAutoReconnectTimer) return
    if (extensionAutoReconnectAttempts >= EXTENSION_AUTO_RECONNECT_MAX_ATTEMPTS) {
        console.warn('[main] Extension auto-reconnect reached max attempts, stop scheduling.')
        return
    }

    extensionAutoReconnectTimer = setTimeout(async () => {
        extensionAutoReconnectTimer = null
        if (extensionAutoReconnectInFlight || licenseRevokedLockdown) return
        extensionAutoReconnectInFlight = true
        try {
            try {
                const healthRes = await fetch('http://127.0.0.1:8100/health', { signal: AbortSignal.timeout(1500) })
                if (healthRes.ok) {
                    const health = await healthRes.json() as { extension_connected?: boolean }
                    if (Boolean(health?.extension_connected)) {
                        extensionAutoReconnectAttempts = 0
                        return
                    }
                }
            } catch {
                // health probe failed, continue reconnect attempts
            }

            extensionAutoReconnectAttempts += 1
            const result = await performExtensionReconnect()
            if (result.ok) {
                extensionAutoReconnectAttempts = 0
                console.log('[main] Extension auto-reconnect success via', result.method)
                return
            }

            const backoffMs = Math.min(12000, 1200 * extensionAutoReconnectAttempts)
            console.warn('[main] Extension auto-reconnect failed:', {
                reason,
                attempt: extensionAutoReconnectAttempts,
                error: result.error,
                retryInMs: backoffMs,
            })
            scheduleExtensionAutoReconnect('retry', backoffMs)
        } finally {
            extensionAutoReconnectInFlight = false
        }
    }, Math.max(0, delayMs))
}

async function getLicenseConfig() {
    return loadLicenseConfig(LICENSE_CONFIG_PATH, DEFAULT_LICENSE_API)
}

async function performLicenseCheck(force = false): Promise<LicenseCheckResult> {
    if (!force && lastLicenseCheck) {
        const elapsed = Date.now() - new Date(lastLicenseCheck.checkedAt).getTime()
        if (elapsed < 5000) {
            return lastLicenseCheck
        }
    }

    const machineId = await getMachineId()
    const config = await getLicenseConfig()
    const result = await checkLicense({
        apiBaseUrl: config.apiBaseUrl,
        machineId,
        cachePath: LICENSE_CACHE_PATH,
        appVersion: app.getVersion(),
        platform: process.platform,
    })
    lastLicenseCheck = result
    return result
}

function stopLicenseEnforcer() {
    if (licenseEnforceTimer) {
        clearInterval(licenseEnforceTimer)
        licenseEnforceTimer = null
    }
}

function pushLicenseStatusToRenderer(result: LicenseCheckResult) {
    mainWindow?.webContents.send('license-status-changed', result)
}

async function enforceLicenseRevocation(source: 'startup' | 'poll'): Promise<void> {
    if (licenseEnforceInFlight) return
    licenseEnforceInFlight = true
    try {
        const result = await performLicenseCheck(true)
        pushLicenseStatusToRenderer(result)

        if (result.status === 'REVOKED') {
            if (!licenseRevokedLockdown) {
                console.error('[license] Device revoked. Locking app until re-activated.', {
                    source,
                    machineId: result.machineId,
                    reason: result.revokedReason ?? null,
                })
            }
            licenseRevokedLockdown = true
            clearExtensionAutoReconnectTimer()
            extensionAutoReconnectAttempts = 0
            sidecar.stop()

            if (!licenseRevokedNotified) {
                licenseRevokedNotified = true
                const reasonLine = result.revokedReason
                    ? `\nLý do: ${result.revokedReason}`
                    : ''
                void dialog.showMessageBox(mainWindow ?? undefined, {
                    type: 'warning',
                    title: 'FlowKit license đã bị thu hồi (REVOKED)',
                    message: `Thiết bị này không còn quyền sử dụng FlowKit.${reasonLine}`,
                    detail: 'Ứng dụng vẫn mở để bạn sao chép Machine ID và yêu cầu admin Active lại.',
                    buttons: ['Đã hiểu'],
                    defaultId: 0,
                })
            }
            return
        }

        if (licenseRevokedLockdown) {
            console.log('[license] Device re-activated. Resuming sidecar.')
            licenseRevokedLockdown = false
            extensionAutoReconnectAttempts = 0
            sidecar.start()
        }
        licenseRevokedNotified = false
    } catch (err) {
        console.error('[license] Revoke enforcement check failed:', err)
    } finally {
        licenseEnforceInFlight = false
    }
}

function startLicenseEnforcer() {
    if (licenseEnforceTimer) return
    void enforceLicenseRevocation('startup')
    licenseEnforceTimer = setInterval(() => {
        void enforceLicenseRevocation('poll')
    }, LICENSE_REVOKE_POLL_MS)
}

function listFlowAccountsPayload() {
    return {
        activeAccountId: flowAccountsConfig.activeAccountId,
        accounts: flowAccountsConfig.accounts.map((account) => ({
            id: account.id,
            label: account.label,
            email: account.email,
            partition: account.partition,
            createdAt: account.createdAt,
            updatedAt: account.updatedAt,
        })),
    }
}

function createFlowAccount(payload?: { id?: string; label?: string; email?: string; setActive?: boolean }) {
    const label = String(payload?.label ?? '').trim() || `Tài khoản ${flowAccountsConfig.accounts.length + 1}`
    let id = normalizeFlowAccountId(payload?.id) || deriveFlowAccountId(label)
    if (!id) id = `account-${flowAccountsConfig.accounts.length + 1}`
    if (id === FLOW_ACCOUNT_DEFAULT_ID && flowAccountsConfig.accounts.some((a) => a.id === FLOW_ACCOUNT_DEFAULT_ID)) {
        id = `account-${flowAccountsConfig.accounts.length + 1}`
    }
    while (flowAccountsConfig.accounts.some((a) => a.id === id)) {
        const suffix = Math.floor(Math.random() * 9000) + 1000
        id = `${id.slice(0, 30)}-${suffix}`
    }
    const createdAt = nowIso()
    const nextAccount: FlowAccount = {
        id,
        label,
        email: String(payload?.email ?? '').trim(),
        partition: partitionForAccountId(id),
        createdAt,
        updatedAt: createdAt,
    }
    const shouldSetActive = payload?.setActive !== false
    saveFlowAccountsConfig({
        activeAccountId: shouldSetActive ? nextAccount.id : flowAccountsConfig.activeAccountId,
        accounts: [...flowAccountsConfig.accounts, nextAccount],
    })
    return listFlowAccountsPayload()
}

function updateFlowAccount(payload?: { id?: string; label?: string; email?: string }) {
    const id = normalizeFlowAccountId(payload?.id)
    if (!id) throw new Error('ID tài khoản không hợp lệ')
    const index = flowAccountsConfig.accounts.findIndex((a) => a.id === id)
    if (index < 0) throw new Error('Không tìm thấy tài khoản')
    const current = flowAccountsConfig.accounts[index]
    const next: FlowAccount = {
        ...current,
        label: String(payload?.label ?? '').trim() || current.label,
        email: String(payload?.email ?? '').trim(),
        updatedAt: nowIso(),
    }
    const accounts = [...flowAccountsConfig.accounts]
    accounts[index] = next
    saveFlowAccountsConfig({ ...flowAccountsConfig, accounts })
    return listFlowAccountsPayload()
}

async function clearFlowAccountSession(accountId?: string | null) {
    const account = getFlowAccountById(accountId)
    const ses = session.fromPartition(account.partition)
    await ses.clearStorageData({
        storages: ['cookies', 'serviceworkers', 'localstorage', 'indexeddb', 'cachestorage'],
    })
    await ses.clearCache()
    await ses.clearAuthCache()
    if (typeof ses.clearHostResolverCache === 'function') await ses.clearHostResolverCache()
    if (typeof ses.flushStorageData === 'function') ses.flushStorageData()
}

async function deleteFlowAccount(accountId?: string | null) {
    const id = normalizeFlowAccountId(accountId)
    if (!id) throw new Error('ID tài khoản không hợp lệ')
    if (flowAccountsConfig.accounts.length <= 1) {
        throw new Error('Cần giữ ít nhất một tài khoản')
    }
    const target = flowAccountsConfig.accounts.find((a) => a.id === id)
    if (!target) throw new Error('Không tìm thấy tài khoản')
    const remaining = flowAccountsConfig.accounts.filter((a) => a.id !== id)
    const nextActive = flowAccountsConfig.activeAccountId === id
        ? remaining[0].id
        : flowAccountsConfig.activeAccountId

    if (flowSessionPartition === target.partition) {
        destroyFlowWindowsForAccountSwitch()
        flowSessionPartition = ''
        flowExtensionId = null
    }
    await unloadExtensionForPartition(target.partition)
    saveFlowAccountsConfig({ activeAccountId: nextActive, accounts: remaining })
    return listFlowAccountsPayload()
}

async function setActiveFlowAccount(accountId?: string | null, options?: { openFlow?: boolean; focus?: boolean }) {
    const account = getFlowAccountById(accountId)
    saveFlowAccountsConfig({
        ...flowAccountsConfig,
        activeAccountId: account.id,
    })
    if (options?.openFlow) {
        await openFlowWindow({
            accountId: account.id,
            reveal: true,
            focus: options.focus ?? true,
            forceRecreate: true,
        })
    }
    return listFlowAccountsPayload()
}

// ─── IPC Handlers ────────────────────────────────────────────

ipcMain.handle('open-flow-tab', async (_event, payload?: { focus?: boolean; reveal?: boolean; accountId?: string }) => {
    await openFlowWindow({
        focus: payload?.focus,
        reveal: payload?.reveal,
        accountId: payload?.accountId,
    })
    return getFlowPanelStatePayload()
})
ipcMain.handle('flow-panel-get-state', () => getFlowPanelStatePayload())
ipcMain.handle('flow-panel-set-visible', async (_event, payload?: { visible?: boolean; persist?: boolean; revealFlowIfNeeded?: boolean }) => {
    return await setFlowPanelVisibility(Boolean(payload?.visible), {
        persist: payload?.persist !== false,
        revealFlowIfNeeded: payload?.revealFlowIfNeeded === true,
    })
})
ipcMain.handle('flow-panel-toggle', async () => {
    const currentlyVisible = isFlowSidebarActuallyVisible()
    const nextVisible = !currentlyVisible
    return await setFlowPanelVisibility(nextVisible, {
        persist: true,
        revealFlowIfNeeded: nextVisible,
    })
})
ipcMain.handle('flow-accounts-list', () => listFlowAccountsPayload())
ipcMain.handle('flow-accounts-create', (_event, payload?: { id?: string; label?: string; email?: string; setActive?: boolean }) =>
    createFlowAccount(payload)
)
ipcMain.handle('flow-accounts-update', (_event, payload?: { id?: string; label?: string; email?: string }) =>
    updateFlowAccount(payload)
)
ipcMain.handle('flow-accounts-delete', async (_event, accountId?: string) =>
    await deleteFlowAccount(accountId)
)
ipcMain.handle('flow-accounts-set-active', async (_event, payload?: { id?: string; openFlow?: boolean; focus?: boolean }) =>
    await setActiveFlowAccount(payload?.id, { openFlow: payload?.openFlow, focus: payload?.focus })
)
ipcMain.handle('flow-accounts-logout', async (_event, payload?: { id?: string; reopenFlow?: boolean; focus?: boolean }) => {
    const account = getFlowAccountById(payload?.id)
    if (flowSessionPartition === account.partition) {
        destroyFlowWindowsForAccountSwitch()
    }
    await clearFlowAccountSession(account.id)
    await unloadExtensionForPartition(account.partition)
    flowSessionPartition = ''
    flowExtensionId = null
    if (payload?.reopenFlow !== false) {
        await openFlowWindow({
            accountId: account.id,
            reveal: true,
            focus: payload?.focus ?? true,
            forceRecreate: true,
        })
    }
    return listFlowAccountsPayload()
})
ipcMain.handle('get-app-info', () => ({
    name: app.getName(),
    version: app.getVersion(),
}))
ipcMain.handle('get-health', async () => {
    try {
        const res = await fetch('http://127.0.0.1:8100/health')
        return res.json()
    } catch {
        return { status: 'error', extension_connected: false }
    }
})
ipcMain.handle('get-machine-id', async () => getMachineId())
ipcMain.handle('get-license-config', async () => getLicenseConfig())
ipcMain.handle('set-license-config', async (_event, apiBaseUrl: string) => {
    const config = await saveLicenseConfig(LICENSE_CONFIG_PATH, apiBaseUrl, DEFAULT_LICENSE_API)
    lastLicenseCheck = null
    return config
})
ipcMain.handle('check-license', async (_event, payload?: { force?: boolean }) => {
    const result = await performLicenseCheck(Boolean(payload?.force))
    pushLicenseStatusToRenderer(result)
    return result
})
ipcMain.handle('pick-image-file', async () => {
    const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
        properties: ['openFile'],
        filters: [
            { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] },
            { name: 'All Files', extensions: ['*'] },
        ],
    })
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
})
ipcMain.handle('pick-file', async (_event, kind: 'image' | 'audio' | 'video' | 'any' = 'any') => {
    const filters = kind === 'image'
        ? [
            { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] },
            { name: 'All Files', extensions: ['*'] },
        ]
        : kind === 'audio'
            ? [
                { name: 'Audio', extensions: ['wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg'] },
                { name: 'All Files', extensions: ['*'] },
            ]
            : kind === 'video'
                ? [
                    { name: 'Video', extensions: ['mp4', 'mov', 'mkv', 'webm'] },
                    { name: 'All Files', extensions: ['*'] },
                ]
                : [{ name: 'All Files', extensions: ['*'] }]
    const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
        properties: ['openFile'],
        filters,
    })
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
})
ipcMain.handle('pick-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
        properties: ['openDirectory', 'createDirectory'],
    })
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
})
ipcMain.handle('open-path', async (_event, targetPath: string) => {
    if (!targetPath) return { ok: false, error: 'Path is required' }
    const error = await shell.openPath(targetPath)
    if (error) return { ok: false, error }
    return { ok: true }
})
ipcMain.handle('window-minimize', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return
    mainWindow.minimize()
})
ipcMain.handle('window-toggle-maximize', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return false
    if (mainWindow.isMaximized()) mainWindow.unmaximize()
    else mainWindow.maximize()
    return mainWindow.isMaximized()
})
ipcMain.handle('window-close', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return
    mainWindow.close()
})
ipcMain.handle('window-is-maximized', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return false
    return mainWindow.isMaximized()
})

ipcMain.on('agent-ready', () => {
    // Forward to renderer
    mainWindow?.webContents.send('agent-status', 'ready')
})

ipcMain.handle('reconnect-extension', async () => {
    const result = await performExtensionReconnect()
    if (result.ok) {
        extensionAutoReconnectAttempts = 0
        clearExtensionAutoReconnectTimer()
    }
    return result
})

// ─── App Lifecycle ───────────────────────────────────────────

app.whenReady().then(async () => {
    // Send status while loading
    try {
        await prepareFlowRuntimeForAccount(flowAccountsConfig.activeAccountId)
    } catch (err) {
        console.error('[main] Failed to prepare default Flow runtime:', err)
    }
    createMainWindow()
    createTray()
    // Keep Flow window available for captcha/token flows.
    try {
        await openFlowWindow({ focus: false, reveal: false, accountId: flowAccountsConfig.activeAccountId })
    } catch (err) {
        console.error('[main] Failed to auto-open Flow window:', err)
    }

    startLicenseEnforcer()

    // Start Python sidecar
    sidecar.start()

    sidecar.on('status', (status: string) => {
        mainWindow?.webContents.send('agent-status', status)
        if (status === 'Ready' && !licenseRevokedLockdown) {
            scheduleExtensionAutoReconnect('sidecar-ready', 500)
        }
    })
})

app.on('second-instance', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
        if (mainWindow.isMinimized()) mainWindow.restore()
        mainWindow.show()
        mainWindow.focus()
    } else {
        createMainWindow()
    }
})

app.on('render-process-gone', (_event, webContents, details) => {
    console.error('[main] render-process-gone:', {
        reason: details.reason,
        exitCode: details.exitCode,
        url: webContents.getURL(),
    })
})

app.on('child-process-gone', (_event, details) => {
    console.error('[main] child-process-gone:', details)
})

app.on('window-all-closed', () => {
    // Keep running in tray
    if (process.platform !== 'darwin') {
        // On Windows, only quit when tray is exited
    }
})

app.on('before-quit', () => {
    appQuitting = true
    stopLicenseEnforcer()
    clearExtensionAutoReconnectTimer()
    sidecar.stop()
})

app.on('activate', () => {
    if (!mainWindow) createMainWindow()
    else {
        mainWindow.show()
        mainWindow.focus()
    }
})
