# Camera Guide — Cinematic Video Prompts (Veo 3)

Reference for writing video prompts optimized for Google Veo 3. Veo 3 generates native audio (dialogue, SFX, ambient) from text — no audio upload needed.

## Prompt Fundamentals

- **Optimal length:** 100–150 words (3–6 sentences)
- **Style:** Natural prose — write like briefing a film director
- **Camera movement:** Always a **separate sentence** — never embed in action description
- **Audio:** Always describe at end of prompt with `Audio:`, `SFX:`, `Music:` labels
- **Negative prompt:** Always append `Negative: subtitles, watermark, text overlay`

### 5-Component Structure

```
[Camera/Shot] + [Subject] + [Action] + [Setting] + [Style & Audio]
```

| Component | Role | Rule |
|-----------|------|------|
| Camera | Shot type, angle, movement | Write as **separate sentence** |
| Subject | Character, object | Detailed: age, clothing, hair, identifying features |
| Action | Motion, emotion, dialogue | Can sequence multiple emotions in one prompt |
| Setting | Location, time, weather | Background + environment + props |
| Style & Audio | Visual aesthetic + sound | Audio labels at end of prompt, separated |

**Critical rule — camera as separate sentence:**
- Wrong: `A woman walks down the street as the camera dollies in with warm lighting`
- Right: `A woman walks down the street. The camera slowly dollies in.`

---

## Shot Types

| Shot | Keywords | Shows |
|------|----------|-------|
| **Extreme wide (EWS)** | `extreme wide shot` | Vast landscape, subject tiny |
| **Wide (WS)** | `wide shot` | Full subject + environment |
| **Medium (MS)** | `medium shot` | Waist up |
| **Close-up (CU)** | `close-up` | Face or detail |
| **Extreme close-up (ECU)** | `extreme close-up` | Eyes, hands, texture |
| **Macro** | `macro shot` | Microscopic detail |

## Camera Movements

| Movement | Keywords | Effect |
|----------|----------|--------|
| **Dolly in/out** | `dolly in`, `dolly out` | Move camera toward/away |
| **Pan** | `pan left`, `pan right` | Horizontal rotation |
| **Tilt** | `tilt up`, `tilt down` | Vertical rotation |
| **Tracking** | `tracking shot` | Follow subject |
| **Crane** | `crane up`, `crane down` | Raise/lower camera |
| **Gimbal glide** | `gimbal glide` | Smooth stabilized movement |
| **Handheld** | `handheld` | Natural shake, raw feel |
| **Whip pan** | `whip pan` | Ultra-fast horizontal snap |
| **Arc shot** | `arc shot` | Orbit around subject |
| **POV** | `POV shot` | First-person perspective |
| **Static** | `locked-off static` | Camera completely fixed |
| **Rack focus** | `rack focus` | Shift focus between subjects |
| **180-degree arc** | `180-degree arc` | Half-orbit around subject |

**Rule:** Write camera movement as its own sentence. One movement per shot.

## Camera Angles

| Angle | Keywords | Effect |
|-------|----------|--------|
| **Eye level** | `eye level shot` | Neutral, natural |
| **Low angle** | `low angle shot, looking up` | Power, dominance |
| **High angle** | `high angle shot, looking down` | Vulnerability |
| **Bird's eye** | `top-down overhead shot` | Scale, patterns |
| **Dutch angle** | `tilted Dutch angle` | Tension, unease |
| **Over-the-shoulder** | `over-the-shoulder shot` | Dialogue connection |
| **Worm's eye** | `extreme low angle from ground` | Dramatic, towering |

## Lens & Focal Length

| Lens | Keywords | Effect |
|------|----------|--------|
| **18mm wide-angle** | `18mm wide-angle` | Exaggerated perspective |
| **35mm** | `35mm` | Classic film look |
| **50mm** | `50mm` | Natural eye perspective |
| **85mm telephoto** | `85mm telephoto` | Compressed perspective, beautiful bokeh |
| **Anamorphic** | `anamorphic lens` | Cinematic widescreen, signature lens flares |

## Depth of Field & Focus

| Technique | Keywords | Effect |
|-----------|----------|--------|
| **Shallow DOF** | `shallow depth of field, soft bokeh` | Subject isolation |
| **Deep focus** | `deep focus, everything sharp` | Full context |
| **Rack focus** | `rack focus from foreground to background` | Shift attention |
| **Tilt-shift** | `tilt-shift, miniature look` | Whimsical, toylike |

---

## Lighting

Lighting creates the biggest difference in output quality. **Always include lighting description.**

| Technique | Keywords | Mood |
|-----------|----------|------|
| **Golden hour** | `golden hour light` | Warmth, nostalgia, romance |
| **High-key** | `high-key lighting` | Bright, even, upbeat |
| **Low-key** | `low-key lighting` | Dark, high contrast, dramatic |
| **Noir** | `noir lighting` | Strong shadows, mysterious |
| **Backlight / rim light** | `backlit, rim light` | Separates subject from background |
| **Soft natural** | `soft natural light` | Gentle, even |
| **Motivated** | `motivated lighting` | Light source logical in scene |
| **Warm/cool practicals** | `warm practicals`, `neon-lit` | In-scene light sources (lamps, neon) |
| **Tungsten** | `tungsten` | Warm yellow incandescent |
| **Fluorescent** | `fluorescent` | Cool greenish office light |
| **Neon** | `neon-lit` | Colorful, vibrant |
| **Candlelight** | `candlelight` | Warm, flickering, intimate |
| **Volumetric** | `volumetric light, god rays` | Ethereal, sacred |
| **Chiaroscuro** | `chiaroscuro, strong contrast` | Drama, film noir |
| **Blue hour** | `blue hour, twilight` | Mystery, melancholy |

---

## Audio — Veo 3's Native Audio Generation

Veo 3 generates all audio from text. Three layers, each with its own label at the end of the prompt:

### Layer 1: Dialogue

```
Character says: "We need to leave now." (no subtitles)
```

**Dialogue rules:**
- Use `:` format to avoid subtitles: `Character says: dialogue text`
- Or use `""` but always add `(no subtitles)`
- Keep dialogue short — must fit in ~8 seconds
- Too long → character speaks unnaturally fast
- Describe voice quality: `in a deep, gravelly voice`, `whispering`, `shouting`
- Delivery verbs: `says`, `whispers`, `shouts`, `asks`, `replies`, `murmurs`, `exclaims`, `gasps`

### Layer 2: Sound Effects (SFX)

Specific, discrete sounds occurring in the scene:

```
SFX: the crack of a bat hitting a ball, crowd roaring
SFX: footsteps on gravel, a door creaking open
```

### Layer 3: Ambient / Background

Continuous background noise creating location realism:

```
Audio: distant city traffic, soft rain on windows
Audio: quiet hum of an office, keyboard typing
```

### Audio Placement

Always at the **end** of the prompt, with clear labels:

```
[Visual description...]

Audio: soft café chatter, espresso machine hissing.
SFX: ceramic cup placed on saucer.
Music: faint lo-fi jazz in background.
```

---

## Style Keywords

| Category | Keywords |
|----------|----------|
| **Film genre** | `cinematic`, `documentary`, `film noir`, `horror`, `rom-com` |
| **Camera feel** | `handheld`, `steadicam`, `found footage`, `security camera` |
| **Color grade** | `desaturated`, `teal and orange`, `warm vintage`, `cool blue` |
| **Film stock** | `35mm grain`, `16mm`, `Super 8`, `IMAX` |
| **Art style** | `anime`, `stop-motion`, `LEGO bricks`, `8-bit pixel art`, `watercolor` |
| **Era** | `1970s`, `retro VHS`, `Y2K aesthetic`, `futuristic` |
| **Override** | `In the style of...` → overrides default aesthetic |

## Speed & Time

| Technique | Keywords | Effect |
|-----------|----------|--------|
| **Slow motion** | `slow motion, time slows` | Dramatic emphasis |
| **Timelapse** | `timelapse, time passing` | Passage of time |
| **Speed ramp** | `speed ramp` | Dynamic rhythm change |

---

## Multi-Shot Prompting

### Method A: Inline Prose (simple, recommended)

Use `then cut to`, `finally` in flowing prose:

```
Wide establishing shot of a rainy city intersection at night,
neon signs reflecting on wet asphalt. Then cut to medium shot
of a woman under a red umbrella, waiting at the crosswalk.
Finally, close-up on her face as she checks her phone,
expression shifting from worry to relief.

The camera movement is smooth and deliberate. Cinematic,
desaturated teal and orange color grade.

Audio: rain pattering on pavement, distant traffic.
SFX: phone notification chime.
Negative: subtitles, watermark, text overlay.
```

### Method B: Timestamp Prompting (precise)

Split clip into timed segments:

```
[00:00–00:02] Medium shot from behind a young explorer as she
pushes aside a jungle vine, leather satchel visible, messy
brown ponytail.

[00:02–00:04] Reverse shot of her freckled face, expression
filled with awe, ancient moss-covered ruins in background.

[00:04–00:06] Tracking shot following her as she steps into
the clearing, runs her hand over carvings on a crumbling
stone wall.

SFX: dense leaves rustling, distant exotic bird calls.
Audio: humid jungle ambience, faint water dripping.
Negative: subtitles, watermark, text overlay.
```

### Multi-Shot Rules

1. **2–3 shots optimal** in one 8-second clip — never more
2. Use **match-action cues** at transitions: `continues turning right` — helps model connect motion between shots
3. Keep **character description consistent** across all shots (repeat identifying features)
4. Create a **scene bible**: lock environment, lighting, color grade → copy into every prompt

---

## Character Consistency

Since we use reference images via `imageInputs`, **don't describe character appearance** in prompts — write ACTION only. The reference image handles visual consistency.

However, for Veo 3 specifics:
- Save establishing shot as Element → reference for subsequent shots
- First-and-last-frame: define start + end frame → model generates motion between them
- `voice_description` on characters (max ~30 words) — auto-appended to video prompts by the worker

---

## Negative Prompt

Veo 3 supports negative prompts — list keywords to exclude (no instructive language):

- Wrong: `no walls, don't show cars`
- Right: `Negative: subtitles, watermark, text overlay`

**Standard negative (always include):**
```
Negative: subtitles, captions, watermark, text on screen, logo, blurry faces, distorted hands
```

**Situational additions:**

| Problem | Add to negative |
|---------|----------------|
| Subtitles appearing | `subtitles, captions` |
| Text overlay | `text overlays, watermarks` |
| Laugh track | `studio audience laughter` |
| Unwanted music | `background music` |
| Over-cinematic | `editorial narration` |

---

## Prompt Template

```
[Shot type] of [subject with detailed description], [action/emotion].
[Camera movement as separate sentence]. [Setting + time of day + weather].
[Lighting description]. [Style/aesthetic].

[Optional dialogue]: Character says: "..." (no subtitles)

Audio: [ambient sounds].
SFX: [specific sound effects].
Music: [background music description].

Negative: subtitles, watermark, text overlay, [other unwanted elements]
```

---

## Examples

### Documentary/Military Scene
```
Medium shot of a soldier in olive fatigues sprinting across a barren
autumn road, military jeep smoking in the background. The camera tracks
him with handheld movement, slight shake. Overcast grey sky, cold
diffused light, breath visible in freezing air. Then cut to close-up
of his face, determined, sweat and dirt streaking his brow, eyes locked
on a concrete barrier ahead. Shallow depth of field, dramatic side
lighting from the overcast sky.

Audio: boots pounding on asphalt, heavy breathing, distant engine rumble.
SFX: gravel crunching underfoot.
Negative: subtitles, watermark, text overlay, blurry faces.
```

### Emotional Discovery Scene
```
Over-the-shoulder shot of Luna kneeling at the edge of a chocolate river,
dipping a paw into the flowing chocolate. Soft diffused golden hour light,
shallow depth of field. Luna gasps: "What is this place?" (no subtitles)
Then cut to close-up of her paw lifting chocolate, slow motion drip catching
the warm backlight. The camera slowly dollies in. Finally, wide crane up
revealing the vast chocolate landscape behind her, cotton candy clouds
towering above, arms raised in wonder.

Audio: gentle river flowing, warm breeze through candy trees.
SFX: chocolate dripping, soft gasp.
Negative: subtitles, watermark, text overlay.
```

### Action Sequence
```
Low angle shot of a hero charging across a castle bridge at dawn, sword
raised high, golden light catching the blade. The camera tracks alongside
with handheld energy. Warm golden hour, long shadows on ancient stone.
Then cut to medium shot as he raises the sword overhead, light bursting
from the blade, wind whipping his cloak. The camera slowly dollies in.
Close-up on his face, jaw set with determination, reflected golden glow
in his eyes, castle gate looming behind.

Audio: wind howling across stone bridge, distant horns.
SFX: sword ringing, boots on stone, cloak snapping in wind.
Negative: subtitles, watermark, text overlay, blurry faces.
```

---

## Quality Checklist

Before submitting any video prompt, verify:

- [ ] Prompt is 100–150 words, 3–6 sentences
- [ ] Subject described with detail (age, clothing, hair, features) — unless ref image handles it
- [ ] Camera movement written as **separate sentence**
- [ ] Lighting/color temperature described
- [ ] Audio / SFX / Music labels at end of prompt
- [ ] Dialogue short (fits in ~8s), uses `:` format or `(no subtitles)`
- [ ] Multi-shot: max 2–3, with match-action cues at transitions
- [ ] Character description consistent across multi-prompt sequences
- [ ] Negative prompt included (at minimum: `subtitles, watermark`)
- [ ] No abstract words — everything is visual/audible and specific
- [ ] Reference characters appear consistently across shots (action only, not appearance)

## Common Mistakes

| Wrong | Right |
|-------|-------|
| Prompt < 50 words, too generic | 100–150 words, specific per component |
| Camera movement embedded in action sentence | Camera movement = separate sentence |
| Dialogue too long for 8s | Keep dialogue short, fits in clip duration |
| Using `"quotes"` for dialogue → subtitles appear | Use `:` format or add `(no subtitles)` |
| No audio description → silent or weird audio | Always write `Audio:` / `SFX:` at end |
| Using `no`, `don't` in negative prompt | List keywords: `subtitles, watermark` |
| Character changes between shots | Repeat exact identifying features every prompt |
| More than 3 shots in 8s | Max 2–3 shots per clip |
| Missing lighting description | Always include lighting + color temperature |
| Vague words like `"cinematic"` alone | Specify: `shallow DOF + golden hour + dolly in` |
| `"Camera zooms"` — too vague | `The camera slowly dollies in.` (separate sentence) |
| No negative prompt | Always: `Negative: subtitles, watermark, text overlay` |
