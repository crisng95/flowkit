// Gemini API key management — stored in localStorage
// Supports multiple keys with automatic rotation on quota limit (429)

export interface GeminiKey {
    id: string
    label: string
    key: string
    status: 'active' | 'limited' | 'invalid'
    limitedAt?: number  // timestamp
}

const STORAGE_KEY = 'flowkit_gemini_keys'
const ACTIVE_IDX_KEY = 'flowkit_gemini_active'

export function loadKeys(): GeminiKey[] {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    } catch { return [] }
}

export function saveKeys(keys: GeminiKey[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keys))
}

export function getActiveIndex(): number {
    return parseInt(localStorage.getItem(ACTIVE_IDX_KEY) ?? '0', 10)
}

export function setActiveIndex(idx: number) {
    localStorage.setItem(ACTIVE_IDX_KEY, String(idx))
}

function getNextActiveKey(keys: GeminiKey[]): GeminiKey | null {
    const active = keys.filter(k => k.status === 'active')
    return active[0] ?? null
}

export class GeminiService {
    private static call(key: string, prompt: string, systemPrompt?: string) {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key}`
        const contents: any[] = [{ role: 'user', parts: [{ text: prompt }] }]
        const body: any = { contents }
        if (systemPrompt) {
            body.system_instruction = { parts: [{ text: systemPrompt }] }
        }
        body.generationConfig = { responseMimeType: 'application/json', temperature: 0.3 }
        return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    }

    /**
     * Call Gemini with auto key rotation on 429 quota limits.
     * Returns parsed JSON from the model response.
     */
    static async generate<T = unknown>(prompt: string, systemPrompt?: string): Promise<T> {
        const keys = loadKeys()
        if (keys.length === 0) throw new Error('No Gemini API keys configured. Go to Settings → API Keys.')

        const active = keys.filter(k => k.status !== 'invalid')
        if (active.length === 0) throw new Error('All Gemini API keys are invalid or rate-limited.')

        let lastError: Error | null = null
        for (const keyObj of active) {
            try {
                const res = await this.call(keyObj.key, prompt, systemPrompt)

                if (res.status === 429 || res.status === 503) {
                    // Mark this key as limited, try next
                    const updated = loadKeys().map(k =>
                        k.id === keyObj.id ? { ...k, status: 'limited' as const, limitedAt: Date.now() } : k
                    )
                    saveKeys(updated)
                    lastError = new Error(`Key "${keyObj.label}" hit quota limit — rotated to next key`)
                    continue
                }

                if (res.status === 400 || res.status === 401 || res.status === 403) {
                    // Mark key as invalid
                    const updated = loadKeys().map(k =>
                        k.id === keyObj.id ? { ...k, status: 'invalid' as const } : k
                    )
                    saveKeys(updated)
                    lastError = new Error(`Key "${keyObj.label}" is invalid (${res.status})`)
                    continue
                }

                if (!res.ok) {
                    throw new Error(`Gemini API error ${res.status}: ${await res.text()}`)
                }

                const data = await res.json()
                const text = data.candidates?.[0]?.content?.parts?.[0]?.text ?? '{}'
                return JSON.parse(text) as T
            } catch (err) {
                if (err instanceof Error && err.message.includes('quota')) continue
                throw err
            }
        }

        throw lastError ?? new Error('All Gemini API keys exhausted')
    }
}

// ─── Project Analysis Prompt ──────────────────────────────────

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

const SYSTEM_PROMPT = `You are a creative AI assistant that analyzes story scripts and extracts structured data for AI video generation. Always return valid JSON only, no markdown.`

export async function analyzeStory(story: string, language: string, sceneCount?: number): Promise<ExtractedProject> {
    const count = sceneCount ?? 8
    const languageLabel = language === 'vi'
        ? 'Vietnamese'
        : language === 'en'
            ? 'English'
            : language === 'es'
                ? 'Spanish'
                : language
    const prompt = `Analyze this story/script and extract structured data for AI video generation.

STORY:
${story}

LANGUAGE: ${language}

Return JSON with this exact schema:
{
  "description": "One-line project description in the story's language",
  "characters": [
    {
      "name": "Character/entity name",
      "entity_type": "character|location|creature|visual_asset|generic_troop|faction",
      "description": "Physical appearance and role description (2-3 sentences). For characters: describe clothing, age, physical features. For locations: describe the place.",
      "voice_description": "Voice style for TTS (only for characters/creatures who speak)"
    }
  ],
  "scenes": [
    {
      "prompt": "Visual scene image prompt describing ACTION and SETTING only. Never describe character appearance (that comes from ref images). Max 2 sentences.",
      "video_prompt": "8-second video motion description: '0-3s: [camera/action]. 3-6s: [action]. 6-8s: [closing shot].'",
      "narrator_text": "Narrator voiceover text for this scene (in ${languageLabel})",
      "character_names": ["Names of characters appearing in this scene"]
    }
  ]
}

Rules:
- Extract ${count} scenes total that tell the full story arc
- Identify ALL named characters, key locations, and important objects/creatures
- narrator_text must be in the same language as the story (${languageLabel})
- scene prompts in English for best AI image generation results
- entity_type: use "character" for people, "location" for places, "creature" for animals/monsters, "visual_asset" for objects
- Return ONLY the JSON object, no markdown`

    return GeminiService.generate<ExtractedProject>(prompt, SYSTEM_PROMPT)
}
