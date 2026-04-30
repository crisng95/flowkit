// Electron IPC bridge — exposed via preload.ts contextBridge
export type LicenseStatus = 'ACTIVE' | 'EXPIRED' | 'REVOKED' | 'PENDING' | 'ERROR'

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

export interface FlowAccount {
    id: string
    label: string
    email: string
    partition: string
    createdAt: string
    updatedAt: string
}

export interface FlowAccountsPayload {
    activeAccountId: string
    accounts: FlowAccount[]
}

export interface FlowPanelState {
    visible: boolean
    sidebarReady: boolean
    flowReady: boolean
    requestedVisible?: boolean
}

export interface ElectronAPI {
    openFlowTab: (options?: { focus?: boolean; reveal?: boolean; accountId?: string }) => Promise<FlowPanelState>
    getFlowPanelState: () => Promise<FlowPanelState>
    setFlowPanelVisible: (visible: boolean, options?: { revealFlowIfNeeded?: boolean }) => Promise<FlowPanelState>
    toggleFlowPanel: () => Promise<FlowPanelState>
    flowAccountsList: () => Promise<FlowAccountsPayload>
    flowAccountsCreate: (payload?: { id?: string; label?: string; email?: string; setActive?: boolean }) => Promise<FlowAccountsPayload>
    flowAccountsUpdate: (payload: { id: string; label?: string; email?: string }) => Promise<FlowAccountsPayload>
    flowAccountsDelete: (id: string) => Promise<FlowAccountsPayload>
    flowAccountsSetActive: (payload: { id: string; openFlow?: boolean; focus?: boolean }) => Promise<FlowAccountsPayload>
    flowAccountsLogout: (payload: { id: string; reopenFlow?: boolean; focus?: boolean }) => Promise<FlowAccountsPayload>
    getAppInfo: () => Promise<{ name: string; version: string }>
    getMachineId: () => Promise<string>
    getLicenseConfig: () => Promise<{ apiBaseUrl: string }>
    setLicenseConfig: (apiBaseUrl: string) => Promise<{ apiBaseUrl: string }>
    getLicenseStatus: (force?: boolean) => Promise<LicenseCheckResult>
    getHealth: () => Promise<{ status: string; extension_connected: boolean; version?: string }>
    reconnectExtension: () => Promise<{ ok: boolean; method?: string; error?: string }>
    pickImageFile: () => Promise<string | null>
    pickFile: (kind?: 'image' | 'audio' | 'video' | 'any') => Promise<string | null>
    pickDirectory: () => Promise<string | null>
    openPath: (targetPath: string) => Promise<{ ok: boolean; error?: string }>
    onAgentStatus: (callback: (status: string) => void) => () => void
    onFlowPanelStateChanged: (callback: (state: FlowPanelState) => void) => () => void
    onLicenseStatusChanged: (callback: (status: LicenseCheckResult) => void) => () => void
    platform: NodeJS.Platform
    windowMinimize: () => Promise<void>
    windowToggleMaximize: () => Promise<boolean>
    windowClose: () => Promise<void>
    isWindowMaximized: () => Promise<boolean>
}

declare global {
    interface Window {
        electron?: ElectronAPI
    }
}

export const isElectron = typeof window !== 'undefined' && !!window.electron
