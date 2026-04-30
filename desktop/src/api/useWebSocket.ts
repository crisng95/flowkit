import { useState, useEffect, useRef, useCallback } from 'react'
import type { WSEvent } from '../types'

// Fixed URL for Electron — no window.location.host in file:// context
const WS_URL = 'ws://127.0.0.1:8100/ws/dashboard'

export function useWebSocket() {
    const [isConnected, setIsConnected] = useState(false)
    const [lastEvent, setLastEvent] = useState<WSEvent | null>(null)
    const wsRef = useRef<WebSocket | null>(null)
    const retriesRef = useRef(0)

    const connect = useCallback(() => {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
            setIsConnected(true)
            retriesRef.current = 0
        }

        ws.onmessage = (e) => {
            try {
                const event: WSEvent = JSON.parse(e.data)
                setLastEvent(event)
            } catch { }
        }

        ws.onclose = () => {
            setIsConnected(false)
            wsRef.current = null
            const delay = Math.min(1000 * 2 ** retriesRef.current, 30000)
            retriesRef.current++
            setTimeout(connect, delay)
        }

        ws.onerror = () => ws.close()
    }, [])

    useEffect(() => {
        connect()
        return () => { wsRef.current?.close() }
    }, [connect])

    return { isConnected, lastEvent }
}
