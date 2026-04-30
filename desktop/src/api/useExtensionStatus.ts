import { useState, useEffect, useCallback } from 'react'
import { fetchAPI } from './client'

interface HealthStatus {
    status: string
    extension_connected: boolean
}

interface FlowRuntimeStatus {
    connected?: boolean
    runtime_connected?: boolean
    state?: string
    manual_disconnect?: boolean
    flow_tab_id?: number | null
    flow_tab_url?: string | null
}

let _cached: boolean | null = null
const _listeners = new Set<(v: boolean) => void>()

// Broadcast to all mounted hooks
function broadcast(v: boolean) {
    _cached = v
    _listeners.forEach(fn => fn(v))
}

// Single background poll shared across hook instances
let _pollInterval: ReturnType<typeof setInterval> | null = null
let _mountCount = 0

async function doCheck() {
    try {
        const [health, runtime] = await Promise.all([
            fetchAPI<HealthStatus>('/health').catch(() => ({ status: 'error', extension_connected: false })),
            fetchAPI<FlowRuntimeStatus>('/api/flow/status').catch(() => ({})),
        ])
        const wsConnected = !!health.extension_connected
        const runtimeConnected =
            runtime.runtime_connected !== undefined
                ? !!runtime.runtime_connected
                : (!!runtime.connected && runtime.state !== 'off' && runtime.manual_disconnect !== true)
        const hasFlowTab =
            runtime.flow_tab_id === undefined
                ? true
                : ((runtime.flow_tab_id !== null && runtime.flow_tab_id !== undefined) || !!runtime.flow_tab_url)
        const connected = wsConnected && runtimeConnected && hasFlowTab
        broadcast(connected)
        return connected
    } catch {
        broadcast(false)
        return false
    }
}

export function useExtensionStatus() {
    const [connected, setConnected] = useState<boolean>(_cached ?? false)

    const check = useCallback(() => doCheck(), [])

    useEffect(() => {
        _listeners.add(setConnected)
        _mountCount++

        // If we already have a cached value, apply it immediately
        if (_cached !== null) setConnected(_cached)

        // Start shared poll only if not already running
        if (!_pollInterval) {
            doCheck() // immediate
            _pollInterval = setInterval(doCheck, 5000)
        } else {
            doCheck() // refresh on mount
        }

        return () => {
            _listeners.delete(setConnected)
            _mountCount--
            if (_mountCount === 0 && _pollInterval) {
                clearInterval(_pollInterval)
                _pollInterval = null
            }
        }
    }, [])

    return { connected, check }
}
