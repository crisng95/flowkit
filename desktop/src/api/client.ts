// Always use absolute URL to the agent — works in both Electron and browser
const AGENT_BASE = 'http://127.0.0.1:8100'

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${AGENT_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        ...options,
    })
    if (!res.ok) {
        const err = await res.text().catch(() => res.statusText)
        throw new Error(`API ${res.status}: ${err}`)
    }
    return res.json()
}

export async function patchAPI<T>(path: string, body: Record<string, unknown>): Promise<T> {
    return fetchAPI<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
}
