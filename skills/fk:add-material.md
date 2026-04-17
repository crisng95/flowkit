# fk:add-material — Image Material System

Image Material controls the **visual style** of every image generated in a project — both entity reference images and scene images. Set it once at project creation; it applies automatically to all generations.

## What Is Image Material?

Each material is a named style profile with:
- **style_instruction** — appended to entity image prompts (controls how characters/locations look)
- **scene_prefix** — prepended to scene prompts automatically at scene creation time
- **negative_prompt** — tells the model what to avoid
- **lighting** — lighting descriptor for entity images

The `scene_prefix` is baked into each scene's `prompt` field when the scene is created. You never need to add style language to scene prompts manually.

---

## Built-In Materials

| ID | Display Name | Style |
|----|-------------|-------|
| `realistic` | Photorealistic | RAW photography, Canon EOS R5, natural light |
| `3d_pixar` | 3D Pixar | Pixar/Disney 3D animation, studio rendering |
| `anime` | Anime | Japanese anime cel-shaded, vibrant colors |
| `ghibli` | Studio Ghibli | Hand-painted watercolor backgrounds, Miyazaki aesthetic, magical realism |
| `stop_motion` | Felt & Wood Stop Motion | Handcrafted felt/wood puppets, miniature sets (Laika/Wes Anderson) |
| `minecraft` | Minecraft | Blocky voxel style, pixel textures, cubic world |
| `oil_painting` | Oil Painting | Classical oil painting, visible brushstrokes, canvas texture |
| `watercolor` | Watercolor | Soft wet brushwork, translucent washes, ink outlines |
| `comic_book` | Comic Book | Bold ink outlines, flat colors, halftone shading (Marvel/DC) |
| `cyberpunk` | Cyberpunk | Neon-lit dark urban, holographic, Blade Runner aesthetic |
| `claymation` | Claymation | Clay puppets with fingerprint textures (Wallace & Gromit/Aardman) |
| `lego` | LEGO | Minifigure characters, brick-built worlds, ABS plastic |
| `retro_vhs` | Retro VHS | 1980s analog VHS, scan lines, CRT curvature, warm grain |

---

## List All Materials

```bash
curl -s http://127.0.0.1:8100/api/materials
```

Returns built-in + any custom materials you've added.

---

## Create a Custom Material

```bash
curl -X POST http://127.0.0.1:8100/api/materials \
  -H "Content-Type: application/json" \
  -d '{
    "id": "watercolor",
    "name": "Watercolor",
    "style_instruction": "Soft watercolor painting, loose wet brushwork, translucent color washes, white paper showing through, delicate ink outlines. Impressionistic and dreamy.",
    "negative_prompt": "NOT photorealistic, NOT 3D render, NOT digital art, NOT anime, NOT sharp edges.",
    "scene_prefix": "Watercolor painting style, soft wet brushwork, translucent color washes, delicate ink outlines.",
    "lighting": "Soft diffused natural light, watercolor wash"
  }'
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (lowercase, underscores). Cannot conflict with built-in IDs. |
| `name` | Yes | Human-readable display name |
| `style_instruction` | Yes | Appended to entity image prompts. Describe the art style in detail. |
| `negative_prompt` | No | What to exclude. Start each item with "NOT". |
| `scene_prefix` | No | Auto-prepended to scene prompts. Keep concise (1-2 sentences). |
| `lighting` | No | Lighting descriptor for entity images. Defaults to "Studio lighting, highly detailed". |

---

## Delete a Custom Material

```bash
curl -X DELETE http://127.0.0.1:8100/api/materials/watercolor
```

**Note:** Built-in materials (`realistic`, `3d_pixar`, `anime`, `stop_motion`, `minecraft`, `oil_painting`) cannot be deleted.

---

## Use Material in Project Creation

The `material` field is **required** when creating a project:

```bash
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Animated Story",
    "description": "A short animated film",
    "story": "...",
    "material": "3d_pixar",
    "characters": [
      {"name": "Luna", "entity_type": "character", "description": "Young girl with curly red hair..."},
      {"name": "Forest", "entity_type": "location", "description": "Ancient enchanted forest..."}
    ]
  }'
```

The material ID propagates to:
1. Entity image generation — `style_instruction` is included in every entity's `image_prompt`
2. Scene creation — `scene_prefix` is automatically prepended to every scene's `prompt`

---

## Tips for Custom Materials

**style_instruction** — what makes a good one:
- Be specific about the medium: "watercolor on cold-press paper" vs just "watercolor"
- Name reference studios/artists when applicable: "Laika Studios stop-motion", "Studio Ghibli anime"
- Include texture words: "visible brushstrokes", "pixel textures", "felt fabric"
- Include rendering quality: "highly detailed", "studio-quality rendering"
- Length: 2-4 sentences is ideal — enough to anchor the style, not so much it overrides content

**scene_prefix** — keep it short:
- 1-2 sentences max — it's prepended to every scene prompt
- Include the key style signal and lighting mood: `"Watercolor style, soft washes, natural light."`
- Don't repeat the full style_instruction — just the essential identifier

**negative_prompt** — be explicit:
- List competing styles as "NOT X": `"NOT photorealistic, NOT 3D render, NOT anime"`
- The more styles you exclude, the more consistent results you get

**Avoid:**
- Mixing incompatible style signals (e.g. "photorealistic anime")
- Describing character appearance in style_instruction (that belongs in entity descriptions)
- Adding style text to scene prompts manually — scene_prefix handles this automatically
