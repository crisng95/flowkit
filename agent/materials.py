"""Material registry — built-in and custom visual styles for image generation."""

_BUILTIN_IDS: frozenset[str] = frozenset({
    "realistic", "3d_pixar", "anime", "stop_motion", "minecraft", "oil_painting"
})

MATERIALS: dict[str, dict] = {
    "realistic": {
        "id": "realistic",
        "name": "Photorealistic",
        "style_instruction": (
            "Photorealistic RAW photograph, shot on Canon EOS R5, 35mm lens, "
            "natural available light, real footage."
        ),
        "negative_prompt": (
            "NOT 3D render, NOT CGI, NOT digital art, NOT illustration, "
            "NOT anime, NOT painting, NOT cartoon."
        ),
        "scene_prefix": (
            "Real RAW photograph, shot on Canon EOS R5, 35mm lens, "
            "natural available light."
        ),
        "lighting": "Studio lighting, highly detailed",
    },
    "3d_pixar": {
        "id": "3d_pixar",
        "name": "3D Pixar",
        "style_instruction": (
            "3D animated style, Pixar-quality rendering, Disney-Pixar aesthetic. "
            "Smooth subsurface scattering skin, expressive cartoon eyes, "
            "stylized proportions, vibrant saturated colors."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT photograph, NOT live action, NOT anime, "
            "NOT flat 2D."
        ),
        "scene_prefix": (
            "3D animated Pixar-quality rendering, vibrant colors, "
            "cinematic lighting."
        ),
        "lighting": "Studio lighting, global illumination, highly detailed",
    },
    "anime": {
        "id": "anime",
        "name": "Anime",
        "style_instruction": (
            "Japanese anime style, cel-shaded rendering, vibrant saturated colors, "
            "clean sharp linework, large expressive eyes, stylized anatomy. "
            "High-quality anime production, studio Ghibli meets modern anime aesthetic."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT oil painting, "
            "NOT sketch, NOT watercolor, NOT Western cartoon."
        ),
        "scene_prefix": (
            "Anime style, cel-shaded, vibrant colors, clean linework, "
            "dramatic anime lighting."
        ),
        "lighting": "Anime-style dramatic lighting, highly detailed",
    },
    "stop_motion": {
        "id": "stop_motion",
        "name": "Felt & Wood Stop Motion",
        "style_instruction": (
            "Stop-motion animation style with handcrafted felt and wood puppets. "
            "Visible felt fabric texture, wooden joints and dowels, "
            "miniature handmade set pieces, warm craft workshop lighting. "
            "Laika Studios / Wes Anderson stop-motion aesthetic."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT digital, NOT anime, "
            "NOT smooth surfaces, NOT plastic."
        ),
        "scene_prefix": (
            "Stop-motion style, handcrafted felt and wood puppets, "
            "miniature set, warm workshop lighting."
        ),
        "lighting": "Warm practical miniature lighting, macro photography detail",
    },
    "minecraft": {
        "id": "minecraft",
        "name": "Minecraft",
        "style_instruction": (
            "Minecraft voxel art style, blocky cubic geometry, pixel textures, "
            "16x16 texture resolution aesthetic, square heads and bodies. "
            "Everything made of cubes and rectangular prisms. "
            "Minecraft game screenshot aesthetic."
        ),
        "negative_prompt": (
            "NOT smooth, NOT round, NOT photorealistic, NOT anime, "
            "NOT organic curves, NOT high-poly."
        ),
        "scene_prefix": (
            "Minecraft style, blocky voxel world, pixel textures, "
            "cubic geometry, game screenshot aesthetic."
        ),
        "lighting": "Minecraft-style ambient lighting, block shadows",
    },
    "oil_painting": {
        "id": "oil_painting",
        "name": "Oil Painting",
        "style_instruction": (
            "Classical oil painting on canvas, visible thick brushstrokes, "
            "rich impasto texture, warm color palette, chiaroscuro lighting. "
            "Renaissance masters meets impressionist technique. "
            "Museum-quality fine art painting."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT digital art, NOT 3D render, NOT anime, "
            "NOT flat colors, NOT cartoon."
        ),
        "scene_prefix": (
            "Oil painting style, visible brushstrokes, rich impasto texture, "
            "warm palette, dramatic chiaroscuro lighting."
        ),
        "lighting": "Dramatic chiaroscuro lighting, rich tonal depth",
    },
}


def get_material(material_id: str) -> dict | None:
    """Get built-in or custom material by ID."""
    return MATERIALS.get(material_id)


def list_materials() -> list[dict]:
    """List all available materials (built-in + custom)."""
    return list(MATERIALS.values())


def register_material(material: dict) -> None:
    """Register a custom material at runtime."""
    if material["id"] in _BUILTIN_IDS:
        raise ValueError(f"Cannot override built-in material '{material['id']}'")
    MATERIALS[material["id"]] = material
