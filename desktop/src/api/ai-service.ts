/**
 * Unified AI Provider Service
 * Supports Gemini, Claude (Anthropic), and OpenAI with per-provider key management
 * and automatic key rotation on quota limits (429 / 503)
 */

export type ProviderType = 'gemini' | 'claude' | 'openai'

export interface APIKey {
    id: string
    label: string
    key: string
    status: 'active' | 'limited' | 'invalid'
    limitedAt?: number
}

export interface GeneralSettings {
    defaultProvider: ProviderType
    defaultLanguage: string
    defaultMaterial: string
    exportRootDir: string
}

// ─── localStorage helpers ──────────────────────────────────────
function storageKey(provider: ProviderType) { return `flowkit_keys_${provider}` }
const GENERAL_KEY = 'flowkit_general_settings'
const RATE_LIMIT_COOLDOWN_MS = 10 * 60 * 1000
const DEFAULT_AI_TIMEOUT_MS = 180000
const LONG_AI_TIMEOUT_MS = 420000
const LONG_STORY_THRESHOLD_CHARS = 9000
const LARGE_SCENE_THRESHOLD = 18

function timeoutSignal(timeoutMs?: number): AbortSignal {
    const normalized = Number.isFinite(timeoutMs) ? Math.max(30000, Number(timeoutMs)) : DEFAULT_AI_TIMEOUT_MS
    return AbortSignal.timeout(normalized)
}

function stripCodeFence(text: string): string {
    const trimmed = text.trim()
    const m = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i)
    return (m?.[1] ?? trimmed).trim()
}

function extractBalancedJson(text: string, start: number): string | null {
    const open = text[start]
    const close = open === '{' ? '}' : open === '[' ? ']' : ''
    if (!close) return null

    let depth = 0
    let inString = false
    let escape = false
    for (let i = start; i < text.length; i += 1) {
        const ch = text[i]
        if (escape) {
            escape = false
            continue
        }
        if (ch === '\\') {
            escape = true
            continue
        }
        if (ch === '"') {
            inString = !inString
            continue
        }
        if (inString) continue
        if (ch === open) depth += 1
        if (ch === close) {
            depth -= 1
            if (depth === 0) return text.slice(start, i + 1)
        }
    }
    return null
}

function parseJsonLoose<T>(raw: string): T {
    const text = stripCodeFence(raw)
    try {
        return JSON.parse(text) as T
    } catch {
        // fallback below
    }

    for (let i = 0; i < text.length; i += 1) {
        const ch = text[i]
        if (ch !== '{' && ch !== '[') continue
        const candidate = extractBalancedJson(text, i)
        if (!candidate) continue
        try {
            return JSON.parse(candidate) as T
        } catch {
            // keep scanning
        }
    }
    throw new Error('AI response is not valid JSON')
}

function normalizeProvider(value: unknown, fallback: ProviderType = 'gemini'): ProviderType {
    const raw = String(value ?? '').trim().toLowerCase()
    if (raw === 'gemini' || raw === 'claude' || raw === 'openai') return raw
    return fallback
}

function parseStoredArray(raw: string | null): unknown[] {
    if (!raw) return []
    try {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) return parsed
        if (parsed && typeof parsed === 'object') return [parsed]
        return []
    } catch {
        return []
    }
}

function normalizeStatus(value: unknown): APIKey['status'] {
    if (value === 'active' || value === 'limited' || value === 'invalid') return value
    return 'active'
}

function extractKeyValue(raw: any): string {
    // Legacy payloads may contain `key: 1` (index) and actual secret in `value`.
    // Never treat numbers as API keys.
    const candidates = [raw?.value, raw?.api_key, raw?.apiKey, raw?.token, raw?.key]
    for (const c of candidates) {
        if (typeof c === 'string' && c.trim()) return c.trim()
    }
    return ''
}

function isLikelyApiKey(value: string): boolean {
    const key = value.trim()
    if (!key) return false
    if (/^\d+$/.test(key)) return false
    if (key.length < 12) return false
    return true
}

function legacyStorageKeys(provider: ProviderType): string[] {
    if (provider === 'gemini') return ['flowkit_gemini_keys']
    return [`flowkit_${provider}_keys`]
}

function normalizeKeyList(rawItems: unknown[]): APIKey[] {
    const out: APIKey[] = []
    rawItems.forEach((raw, index) => {
        if (typeof raw === 'string') {
            const key = raw.trim()
            if (!key) return
            out.push({
                id: Math.random().toString(36).slice(2, 10),
                label: `Key ${out.length + 1}`,
                key,
                status: isLikelyApiKey(key) ? 'active' : 'invalid',
            })
            return
        }
        if (!raw || typeof raw !== 'object') return
        const key = extractKeyValue(raw)
        if (!key) return
        const limitedAt = Number((raw as any).limitedAt)
        const cooldownExpired = Number.isFinite(limitedAt) && (Date.now() - limitedAt > RATE_LIMIT_COOLDOWN_MS)
        const statusBase = normalizeStatus((raw as any).status)
        const status: APIKey['status'] = isLikelyApiKey(key)
            ? (statusBase === 'limited' && cooldownExpired ? 'active' : statusBase)
            : 'invalid'
        out.push({
            id: typeof (raw as any).id === 'string' && (raw as any).id.trim()
                ? (raw as any).id.trim()
                : Math.random().toString(36).slice(2, 10),
            label: typeof (raw as any).label === 'string' && (raw as any).label.trim()
                ? (raw as any).label.trim()
                : `Key ${index + 1}`,
            key,
            status,
            limitedAt: Number.isFinite(limitedAt) ? limitedAt : undefined,
        })
    })

    // de-dup by key string while preserving the latest occurrence
    // (important when user re-adds the same key to reactivate it)
    const seen = new Set<string>()
    const dedupedReversed: APIKey[] = []
    for (let i = out.length - 1; i >= 0; i -= 1) {
        const item = out[i]
        const sig = item.key
        if (seen.has(sig)) continue
        seen.add(sig)
        dedupedReversed.push(item)
    }
    return dedupedReversed.reverse()
}

function providerName(provider: ProviderType): string {
    return provider === 'gemini' ? 'Gemini' : provider === 'claude' ? 'Claude' : 'OpenAI'
}

function isInvalidKeyResponse(status: number, bodyText: string): boolean {
    if (status === 401 || status === 403) return true
    if (status !== 400) return false
    const text = bodyText.toLowerCase()
    return (
        text.includes('invalid api key') ||
        text.includes('api key not valid') ||
        text.includes('incorrect api key') ||
        text.includes('authentication') ||
        text.includes('x-api-key') ||
        text.includes('unauthorized')
    )
}

export function loadKeys(provider: ProviderType): APIKey[] {
    try {
        const normalizedProvider = normalizeProvider(provider)
        const primaryKey = storageKey(normalizedProvider)
        const primaryRaw = parseStoredArray(localStorage.getItem(primaryKey))
        const legacyRaw = legacyStorageKeys(normalizedProvider)
            .flatMap(k => parseStoredArray(localStorage.getItem(k)))
        const merged = normalizeKeyList([...legacyRaw, ...primaryRaw])

        // Persist migrated/sanitized shape back to canonical storage
        const canonicalRaw = JSON.stringify(primaryRaw)
        const canonicalNormalized = JSON.stringify(merged)
        if (canonicalRaw !== canonicalNormalized) {
            localStorage.setItem(primaryKey, canonicalNormalized)
        }
        return merged
    } catch {
        return []
    }
}

export function saveKeys(provider: ProviderType, keys: APIKey[]) {
    const normalizedProvider = normalizeProvider(provider)
    const normalized = normalizeKeyList(keys ?? [])
    localStorage.setItem(storageKey(normalizedProvider), JSON.stringify(normalized))
}

export function loadGeneralSettings(): GeneralSettings {
    try {
        const raw = JSON.parse(localStorage.getItem(GENERAL_KEY) ?? '{}')
        return {
            defaultProvider: normalizeProvider(raw.defaultProvider),
            defaultLanguage: typeof raw.defaultLanguage === 'string' && raw.defaultLanguage.trim() ? raw.defaultLanguage : 'vi',
            defaultMaterial: typeof raw.defaultMaterial === 'string' && raw.defaultMaterial.trim() ? raw.defaultMaterial : 'realistic',
            exportRootDir: typeof raw.exportRootDir === 'string' ? raw.exportRootDir.trim() : '',
        }
    } catch {
        return { defaultProvider: 'gemini', defaultLanguage: 'vi', defaultMaterial: 'realistic', exportRootDir: '' }
    }
}

export function saveGeneralSettings(s: Partial<GeneralSettings>) {
    const current = loadGeneralSettings()
    const merged = { ...current, ...s }
    localStorage.setItem(GENERAL_KEY, JSON.stringify({
        defaultProvider: normalizeProvider(merged.defaultProvider, current.defaultProvider),
        defaultLanguage: merged.defaultLanguage || current.defaultLanguage,
        defaultMaterial: merged.defaultMaterial || current.defaultMaterial,
        exportRootDir: typeof merged.exportRootDir === 'string' ? merged.exportRootDir.trim() : current.exportRootDir,
    }))
}

// ─── Provider implementations ─────────────────────────────────

async function callGemini(key: string, prompt: string, systemPrompt?: string, timeoutMs?: number): Promise<Response> {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key}`
    const body: any = {
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: { responseMimeType: 'application/json', temperature: 0.3 },
    }
    if (systemPrompt) body.system_instruction = { parts: [{ text: systemPrompt }] }
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: timeoutSignal(timeoutMs),
    })
}

async function callClaude(key: string, prompt: string, systemPrompt?: string, timeoutMs?: number): Promise<Response> {
    return fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': key,
            'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
            model: 'claude-3-5-haiku-20241022',
            max_tokens: 8192,
            system: (systemPrompt ?? '') + '\n\nAlways respond with valid JSON only, no markdown or explanation.',
            messages: [{ role: 'user', content: prompt }],
        }),
        signal: timeoutSignal(timeoutMs),
    })
}

async function callOpenAI(key: string, prompt: string, systemPrompt?: string, timeoutMs?: number): Promise<Response> {
    return fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
        body: JSON.stringify({
            model: 'gpt-4o-mini',
            response_format: { type: 'json_object' },
            temperature: 0.3,
            max_tokens: 4096,
            messages: [
                ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
                { role: 'user', content: prompt },
            ],
        }),
        signal: timeoutSignal(timeoutMs),
    })
}

async function parseResponse(res: Response, provider: ProviderType): Promise<string> {
    const data = await res.json()
    if (provider === 'gemini') return data.candidates?.[0]?.content?.parts?.[0]?.text ?? '{}'
    if (provider === 'claude') return data.content?.[0]?.text ?? '{}'
    if (provider === 'openai') return data.choices?.[0]?.message?.content ?? '{}'
    return '{}'
}

// ─── Main generate function ────────────────────────────────────

export async function aiGenerate<T = unknown>(
    prompt: string,
    systemPrompt?: string,
    providerOverride?: ProviderType,
    options?: { timeoutMs?: number }
): Promise<T> {
    const provider = normalizeProvider(providerOverride ?? loadGeneralSettings().defaultProvider)
    const allKeys = loadKeys(provider)
    const activeKeys = allKeys.filter(k => k.status !== 'invalid' && isLikelyApiKey(k.key))

    if (activeKeys.length === 0) {
        const name = providerName(provider)
        if (allKeys.length > 0) {
            throw new Error(`${name} key không hợp lệ trong Settings. Vui lòng nhập lại key đúng định dạng ở Cài đặt → ${name}.`)
        }
        throw new Error(`No ${name} API keys configured. Go to Settings → ${name}.`)
    }

    const callers: Record<ProviderType, typeof callGemini> = {
        gemini: callGemini, claude: callClaude, openai: callOpenAI,
    }

    let lastError: Error | null = null
    for (const keyObj of activeKeys) {
        try {
            const res = await callers[provider](keyObj.key.trim(), prompt, systemPrompt, options?.timeoutMs)

            if (res.status === 429 || res.status === 503) {
                const updated = loadKeys(provider).map(k =>
                    k.id === keyObj.id ? { ...k, status: 'limited' as const, limitedAt: Date.now() } : k
                )
                saveKeys(provider, updated)
                lastError = new Error(`Key "${keyObj.label}" hit quota — rotating to next key`)
                continue
            }

            if (!res.ok) {
                const errText = await res.text().catch(() => '')
                if (isInvalidKeyResponse(res.status, errText)) {
                    const updated = loadKeys(provider).map(k =>
                        k.id === keyObj.id ? { ...k, status: 'invalid' as const } : k
                    )
                    saveKeys(provider, updated)
                    lastError = new Error(`Key "${keyObj.label}" is invalid (HTTP ${res.status})`)
                    continue
                }
                throw new Error(`AI API error ${res.status}: ${errText || res.statusText}`)
            }

            const text = await parseResponse(res, provider)
            return parseJsonLoose<T>(text)
        } catch (err) {
            if (err instanceof Error && (err.message.includes('quota') || err.message.includes('rotating'))) continue
            throw err
        }
    }
    throw lastError ?? new Error('All API keys exhausted')
}

// ─── Prompt templates ──────────────────────────────────────────

const SYSTEM_PROMPT = `You are a creative AI assistant for AI video documentary generation.
Always respond with valid JSON only, no markdown, no explanation.`

export interface ResearchResult {
    summary: string
    key_facts: string[]
    suggested_story_angle: string
    suggested_characters: { name: string; role: string }[]
}

function languageLabel(language: string): string {
    if (language === 'vi') return 'Vietnamese'
    if (language === 'en') return 'English'
    if (language === 'es') return 'Spanish'
    return language
}

export async function researchTopic(topic: string, language: string, provider?: ProviderType): Promise<ResearchResult> {
    const prompt = `Research this topic for an AI video documentary: "${topic}"

Language for output: ${languageLabel(language)}

Return JSON:
{
  "summary": "2-3 paragraph summary of the topic with key facts",
  "key_facts": ["fact 1", "fact 2", "fact 3", "fact 4", "fact 5"],
  "suggested_story_angle": "Suggested narrative angle for a compelling documentary",
  "suggested_characters": [
    {"name": "Person/Entity name", "role": "Their role in the story"}
  ]
}

Base on your knowledge. Include specific dates, names, numbers when available.`
    return aiGenerate<ResearchResult>(prompt, SYSTEM_PROMPT, provider)
}

export interface ExtractedProject {
    description: string
    characters: {
        name: string
        entity_type: 'character' | 'location' | 'creature' | 'visual_asset' | 'generic_troop' | 'faction'
        description: string
        voice_description?: string
    }[]
    scenes: {
        prompt: string
        video_prompt: string
        narrator_text: string
        character_names: string[]
    }[]
}

type ExtractedScene = ExtractedProject['scenes'][number]
type ExtractedCharacter = ExtractedProject['characters'][number]

const ENTITY_TYPES: ExtractedCharacter['entity_type'][] = [
    'character',
    'location',
    'creature',
    'visual_asset',
    'generic_troop',
    'faction',
]

const VIDEO_PROMPT_VARIETY_RULES = `
VIDEO PROMPT DIVERSITY RULES:
- Do NOT reuse one rigid timing motif across all scenes.
- Mix these structures across the episode:
  1) [00:00-00:02] ... [00:02-00:05] ... [00:05-00:08] ...
  2) 0-4s ... 4-8s ...
  3) One continuous 8-second single-take camera instruction.
- Vary shot intent between adjacent scenes: establishing, reaction, detail insert, reveal, transition, climax, release.
- Vary camera language: static, tracking, dolly in/out, pan, tilt, overhead, handheld, arc, rack focus.
- Keep prompts action-focused; do not describe character appearance.
- Keep each video_prompt concise and production-ready.`

const FALLBACK_VIDEO_PATTERNS: string[] = [
    '[00:00-00:02] Establish environment and immediate action. [00:02-00:05] Slow dolly-in as the action intensifies. [00:05-00:08] Hold a clean transition beat into the next scene.',
    '0-4s: Medium framing follows the main action with steady tracking. 4-8s: Shift to a wider reveal and end with directional motion for the next cut.',
    '[00:00-00:03] Close detail on the key action. [00:03-00:06] Pan to reveal context and secondary movement. [00:06-00:08] Brief still moment that resolves tension.',
    'Single-take over 8 seconds: handheld documentary movement follows the subject naturally, then eases into a stable frame for the transition.',
    '[00:00-00:02] Wide establishing shot. [00:02-00:06] Arc movement around the action for depth. [00:06-00:08] Cut on motion toward the next narrative beat.',
    '0-2s: Top-down or high-angle setup to orient geography. 2-6s: Drop to eye-level and track the action. 6-8s: End on a reaction beat that bridges to next scene.',
]

function normalizeStringArray(raw: unknown, limit = 20): string[] {
    if (!Array.isArray(raw)) return []
    return raw
        .filter((item): item is string => typeof item === 'string')
        .map(item => item.trim())
        .filter(Boolean)
        .slice(0, limit)
}

function buildFallbackVideoPrompt(index: number): string {
    return FALLBACK_VIDEO_PATTERNS[index % FALLBACK_VIDEO_PATTERNS.length]
}

function normalizeScene(raw: any, index = 0): ExtractedScene | null {
    if (!raw || typeof raw !== 'object') return null
    const prompt = typeof raw.prompt === 'string' ? raw.prompt.trim() : ''
    const videoPrompt = typeof raw.video_prompt === 'string' ? raw.video_prompt.trim() : ''
    const narrator = typeof raw.narrator_text === 'string' ? raw.narrator_text.trim() : ''
    const characterNames = Array.isArray(raw.character_names)
        ? raw.character_names
            .filter((v: unknown): v is string => typeof v === 'string')
            .map((v: string) => v.trim())
            .filter((v: string) => Boolean(v))
        : []

    if (!prompt && !videoPrompt && !narrator) return null

    return {
        prompt: prompt || 'Cinematic continuation shot in the same setting, keeping action continuity.',
        video_prompt: videoPrompt || buildFallbackVideoPrompt(index),
        narrator_text: narrator,
        character_names: characterNames,
    }
}

function normalizeSceneArray(rawScenes: unknown): ExtractedScene[] {
    if (!Array.isArray(rawScenes)) return []
    return rawScenes
        .map((scene, index) => normalizeScene(scene, index))
        .filter((scene): scene is ExtractedScene => Boolean(scene))
}

function normalizeCharacters(rawChars: unknown): ExtractedCharacter[] {
    if (!Array.isArray(rawChars)) return []
    return rawChars
        .map((raw): ExtractedCharacter | null => {
            if (!raw || typeof raw !== 'object') return null
            const name = typeof (raw as any).name === 'string' ? (raw as any).name.trim() : ''
            if (!name) return null
            const entityTypeRaw = typeof (raw as any).entity_type === 'string' ? (raw as any).entity_type.trim() : ''
            const entityType = ENTITY_TYPES.includes(entityTypeRaw as ExtractedCharacter['entity_type'])
                ? (entityTypeRaw as ExtractedCharacter['entity_type'])
                : 'character'
            return {
                name,
                entity_type: entityType,
                description: typeof (raw as any).description === 'string' ? (raw as any).description.trim() : '',
                voice_description: typeof (raw as any).voice_description === 'string'
                    ? (raw as any).voice_description.trim()
                    : undefined,
            }
        })
        .filter((char): char is ExtractedCharacter => Boolean(char))
}

function buildFallbackScene(index: number, total: number): ExtractedScene {
    const n = index + 1
    return {
        prompt: `Cinematic continuation scene ${n}/${total}. Keep setting and story continuity.`,
        video_prompt: buildFallbackVideoPrompt(index),
        narrator_text: '',
        character_names: [],
    }
}

function shouldUseChunkedStoryAnalysis(story: string, sceneCount: number): boolean {
    return story.trim().length >= LONG_STORY_THRESHOLD_CHARS || sceneCount >= LARGE_SCENE_THRESHOLD
}

function compactStoryForPrompt(story: string, maxChars = 22000): string {
    const text = story.trim()
    if (text.length <= maxChars) return text
    const cut = Math.max(4000, Math.floor((maxChars - 128) / 2))
    return `${text.slice(0, cut)}\n\n[...TRUNCATED ${text.length - (cut * 2)} CHARS...]\n\n${text.slice(-cut)}`
}

function sceneBatchSize(sceneCount: number): number {
    if (sceneCount >= 60) return 10
    if (sceneCount >= 32) return 8
    if (sceneCount >= 20) return 7
    return 6
}

function pickArcBeatsForRange(arcBeats: string[], startIndex: number, endIndex: number, totalScenes: number): string[] {
    if (arcBeats.length <= 6) return arcBeats
    const fromRatio = startIndex / Math.max(1, totalScenes)
    const toRatio = endIndex / Math.max(1, totalScenes)
    const selected = arcBeats.filter((_, idx) => {
        const beatRatio = idx / Math.max(1, arcBeats.length - 1)
        return beatRatio >= (fromRatio - 0.2) && beatRatio <= (toRatio + 0.2)
    })
    return selected.length > 0 ? selected.slice(0, 8) : arcBeats.slice(0, 8)
}

interface StoryBlueprint {
    description: string
    characters: ExtractedCharacter[]
    arcBeats: string[]
    visualLanguage: string[]
    pacingNotes: string[]
}

async function buildStoryBlueprint(story: string, language: string, provider?: ProviderType): Promise<StoryBlueprint> {
    const lang = languageLabel(language)
    const prompt = `Create a compact production blueprint for a long-form AI video project.

STORY:
${compactStoryForPrompt(story)}

Return JSON only:
{
  "description": "One-line project description in ${lang}",
  "characters": [
    {
      "name": "Name",
      "entity_type": "character|location|creature|visual_asset|generic_troop|faction",
      "description": "Physical appearance for entities only, concise",
      "voice_description": "TTS voice style for speaking characters"
    }
  ],
  "arc_beats": ["Beat 1", "Beat 2", "Beat 3"],
  "visual_language": ["cinematic style rule 1", "style rule 2"],
  "pacing_notes": ["pacing note 1", "pacing note 2"]
}

RULES:
- Keep arc_beats concise and chronological
- Include all important entities in characters
- Output valid JSON only`

    const raw = await aiGenerate<{
        description?: unknown
        characters?: unknown
        arc_beats?: unknown
        visual_language?: unknown
        pacing_notes?: unknown
    }>(prompt, SYSTEM_PROMPT, provider, { timeoutMs: LONG_AI_TIMEOUT_MS })

    return {
        description: typeof raw?.description === 'string' ? raw.description.trim() : '',
        characters: normalizeCharacters(raw?.characters),
        arcBeats: normalizeStringArray(raw?.arc_beats, 20),
        visualLanguage: normalizeStringArray(raw?.visual_language, 12),
        pacingNotes: normalizeStringArray(raw?.pacing_notes, 12),
    }
}

async function generateScenesInBatches(
    story: string,
    language: string,
    sceneCount: number,
    blueprint: StoryBlueprint,
    provider?: ProviderType
): Promise<ExtractedScene[]> {
    const lang = languageLabel(language)
    const batch = sceneBatchSize(sceneCount)
    const generated: ExtractedScene[] = []
    const totalBatches = Math.ceil(sceneCount / batch)
    const storySnippet = compactStoryForPrompt(story, 12000)

    for (let batchIndex = 0; batchIndex < totalBatches; batchIndex += 1) {
        const start = batchIndex * batch
        const end = Math.min(sceneCount, start + batch)
        const count = end - start
        const sceneFrom = start + 1
        const sceneTo = end
        const previousContext = generated.slice(-2).map((scene, idx) => {
            const no = start - Math.max(0, generated.slice(-2).length - idx) + 1
            return `Scene ${no}: narrator="${scene.narrator_text}" | prompt="${scene.prompt}"`
        }).join('\n')
        const arcBeats = pickArcBeatsForRange(blueprint.arcBeats, start, end, sceneCount)
        const prompt = `Create scenes ${sceneFrom}-${sceneTo} of ${sceneCount} for one coherent episode.

PROJECT DESCRIPTION:
${blueprint.description || 'Documentary-style visual storytelling'}

ARC BEATS TO COVER IN THIS BATCH:
${arcBeats.map((beat, idx) => `${idx + 1}. ${beat}`).join('\n') || '- Keep continuity from previous beats'}

VISUAL LANGUAGE:
${blueprint.visualLanguage.map((item, idx) => `${idx + 1}. ${item}`).join('\n') || '- Cinematic, documentary realism'}

PACING NOTES:
${blueprint.pacingNotes.map((item, idx) => `${idx + 1}. ${item}`).join('\n') || '- Rhythmic pacing with clear transitions'}

SHORT STORY CONTEXT:
${storySnippet}

LAST GENERATED SCENES (continuity anchor):
${previousContext || 'None (this is the first batch)'}

Return JSON:
{
  "scenes": [
    {
      "prompt": "IMAGE PROMPT in English, action + setting only, max 2 sentences",
      "video_prompt": "Detailed motion plan optimized for Veo",
      "narrator_text": "Narration in ${lang}, 1-2 sentences",
      "character_names": ["character names"]
    }
  ]
}

RULES:
- Return exactly ${count} scenes for this batch
- Keep strict continuity with previous scenes
- Image prompt must avoid character appearance details
${VIDEO_PROMPT_VARIETY_RULES}`

        const raw = await aiGenerate<{ scenes?: unknown }>(prompt, SYSTEM_PROMPT, provider, { timeoutMs: LONG_AI_TIMEOUT_MS })
        let batchScenes = normalizeSceneArray(raw?.scenes)
        batchScenes = ensureExactSceneCount(batchScenes, count)
        generated.push(...batchScenes)
    }

    return generated.slice(0, sceneCount)
}

function ensureExactSceneCount(scenes: ExtractedScene[], targetCount: number): ExtractedScene[] {
    if (targetCount <= 0) return []
    const out = [...scenes]
    if (out.length > targetCount) return out.slice(0, targetCount)
    while (out.length < targetCount) {
        out.push(buildFallbackScene(out.length, targetCount))
    }
    return out
}

async function rebalanceScenesWithAI(
    story: string,
    language: string,
    sceneCount: number,
    sourceScenes: ExtractedScene[],
    provider?: ProviderType
): Promise<ExtractedScene[] | null> {
    const lang = languageLabel(language)
    const prompt = `Rewrite the scenes below to exactly ${sceneCount} scenes for one coherent episode.

STORY:
${story}

CURRENT SCENES JSON:
${JSON.stringify(sourceScenes)}

Return JSON only:
{
  "scenes": [
    {
      "prompt": "IMAGE PROMPT in English, action + setting only, max 2 sentences",
      "video_prompt": "Detailed motion plan optimized for Veo",
      "narrator_text": "Narration in ${lang}, 1-2 sentences",
      "character_names": ["character names"]
    }
  ]
}

RULES:
- Exactly ${sceneCount} scenes
- Keep story continuity and full arc
- Do not describe character appearance in image prompt
${VIDEO_PROMPT_VARIETY_RULES}`

    const repaired = await aiGenerate<{ scenes?: unknown }>(prompt, SYSTEM_PROMPT, provider, { timeoutMs: LONG_AI_TIMEOUT_MS })
    const scenes = normalizeSceneArray(repaired?.scenes)
    return scenes.length > 0 ? scenes : null
}

export async function analyzeStory(story: string, language: string, sceneCount = 8, provider?: ProviderType): Promise<ExtractedProject> {
    const lang = languageLabel(language)
    const prompt = `Analyze this story for AI video generation. Extract exactly ${sceneCount} scenes.

STORY:
${compactStoryForPrompt(story)}

Return JSON with this schema:
{
  "description": "One-line project description in ${lang}",
  "characters": [
    {
      "name": "Name",
      "entity_type": "character|location|creature|visual_asset|generic_troop|faction",
      "description": "Physical appearance only (2-3 sentences). For characters: age, clothing, hair, build. For locations: atmosphere and setting details.",
      "voice_description": "TTS voice style (only for speaking characters)"
    }
  ],
  "scenes": [
    {
      "prompt": "IMAGE PROMPT: Scene visual in English. Describe ACTION and SETTING only. Never describe character appearance (ref images handle that). Max 2 sentences.",
      "video_prompt": "VIDEO MOTION: Detailed cinematic motion plan optimized for Veo",
      "narrator_text": "Narrator voiceover in ${lang} for this scene. 1-2 sentences.",
      "character_names": ["Names of characters in this scene"]
    }
  ]
}

RULES:
- Extract ALL named characters, key locations, creatures, important objects
- Exactly ${sceneCount} scenes covering the full story arc
- Image prompts in English for best AI generation
- Narrator text in ${lang}
- Scene prompts reference actions NOT appearance
${VIDEO_PROMPT_VARIETY_RULES}`

    let raw: ExtractedProject | null = null
    const useChunked = shouldUseChunkedStoryAnalysis(story, sceneCount)

    if (useChunked) {
        try {
            const blueprint = await buildStoryBlueprint(story, language, provider)
            const scenes = await generateScenesInBatches(story, language, sceneCount, blueprint, provider)
            raw = {
                description: blueprint.description,
                characters: blueprint.characters,
                scenes,
            }
        } catch {
            // fallback to one-shot mode below
        }
    }

    if (!raw) {
        raw = await aiGenerate<ExtractedProject>(prompt, SYSTEM_PROMPT, provider, {
            timeoutMs: useChunked ? LONG_AI_TIMEOUT_MS : DEFAULT_AI_TIMEOUT_MS,
        })
    }

    const description = typeof raw?.description === 'string' ? raw.description.trim() : ''
    const characters = normalizeCharacters(raw?.characters)
    let scenes = normalizeSceneArray(raw?.scenes)

    if (scenes.length !== sceneCount) {
        try {
            const repaired = await rebalanceScenesWithAI(story, language, sceneCount, scenes, provider)
            if (repaired && repaired.length > 0) scenes = repaired
        } catch {
            // Keep best-effort local normalization below.
        }
    }

    scenes = ensureExactSceneCount(scenes, sceneCount)
    if (scenes.length === 0) {
        throw new Error('AI did not return any valid scenes')
    }

    return {
        description,
        characters,
        scenes,
    }
}
