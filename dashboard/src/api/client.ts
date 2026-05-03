const BASE = ''  // same origin, proxied by Vite in dev

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
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

export async function postAPI<T>(path: string, body: Record<string, unknown>): Promise<T> {
  return fetchAPI<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

export async function putAPI<T>(path: string, body: Record<string, unknown>): Promise<T> {
  return fetchAPI<T>(path, { method: 'PUT', body: JSON.stringify(body) })
}

export async function deleteAPI<T>(path: string): Promise<T> {
  return fetchAPI<T>(path, { method: 'DELETE' })
}
