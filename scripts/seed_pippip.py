"""
Seed script: "Pippip the Fish Merchant"
A chubby orange tabby cat sells fish at a bustling open market. 5 scenes, vertical.

Usage:
    python scripts/seed_pippip.py [--base-url http://127.0.0.1:8000]

Requires: server running + Chrome extension connected.
"""
import argparse
import httpx
import json
import sys

BASE = "http://127.0.0.1:8100/api"

PROJECT = {
    "name": "Pippip the Fish Merchant",
    "description": "A chubby orange tabby cat named Pippip runs a tiny fish stall in a bustling Southeast Asian open market. A charming day-in-the-life short.",
    "story": (
        "Pippip is a chubby orange tabby cat who wears a small blue apron and a tiny straw hat. "
        "Every morning he sets up his fish stall at the local open market. "
        "Scene 1: Pippip arranges fresh fish on ice at sunrise. "
        "Scene 2: His first customer, a curious little girl, arrives and Pippip proudly shows her his best fish. "
        "Scene 3: Midday rush — Pippip juggles fish to entertain the crowd. "
        "Scene 4: Only one golden fish left. Pippip stares at it, drooling, torn between selling and eating. "
        "Scene 5: Sunset — stall empty, SOLD OUT sign up. Pippip happily eats the golden fish with chopsticks."
    ),
    "language": "en",
    "characters": [
        # ── Characters ──
        {
            "name": "Pippip",
            "entity_type": "character",
            "description": (
                "Chubby orange tabby cat with big green eyes and expressive face. "
                "Wears a small blue apron and a tiny straw hat. Walks upright on two legs. "
                "Short fluffy tail, round belly, small pink nose. "
                "Pixar-style 3D animated character. Friendly, proud, slightly greedy."
            ),
        },
        {
            "name": "Mai",
            "entity_type": "character",
            "description": (
                "Small Southeast Asian girl, about 6 years old. Bright curious eyes, messy pigtails "
                "with red ribbons. Wears a simple yellow sundress and sandals. "
                "Missing front tooth, cheerful round face. "
                "Pixar-style 3D animated character."
            ),
        },
        # ── Locations ──
        {
            "name": "Fish Stall",
            "entity_type": "location",
            "description": (
                "Small rustic wooden market stall with a thatched bamboo roof. "
                "Crushed ice display area for fish, weathered wooden counter. "
                "Hanging brass scale, small chalkboard price signs, woven baskets underneath. "
                "A faded red cloth canopy over the front. Warm, lived-in feel."
            ),
        },
        {
            "name": "Open Market",
            "entity_type": "location",
            "description": (
                "Bustling Southeast Asian open-air morning market. "
                "Colorful fabric awnings in red, orange, and yellow. Hanging paper lanterns. "
                "Worn stone walkway between rows of vendor stalls. "
                "Tropical trees and potted plants. Warm humid atmosphere with soft haze."
            ),
        },
        # ── Visual Assets ──
        {
            "name": "Golden Fish",
            "entity_type": "visual_asset",
            "description": (
                "A magnificent golden koi fish, larger than the other market fish. "
                "Shimmering iridescent gold scales that catch and reflect light. "
                "Elegant flowing fins with a slight magical glow around it. "
                "The prized centerpiece fish — almost too beautiful to eat."
            ),
        },
    ],
}

VIDEO = {
    "title": "Pippip the Fish Merchant — Episode 1",
    "description": "A day in the life of Pippip, the cat who sells fish at the market.",
    "display_order": 0,
}

# Scene prompts: ACTION + COMPOSITION of reference materials.
# Character/location/asset appearance comes from reference images (mediaId via imageInputs).
# Reference entities by NAME only — describe what they DO and where they are in the frame.
SCENES = [
    {
        "display_order": 0,
        "prompt": (
            "Pippip stands behind Fish Stall, carefully arranging fresh colorful fish on the ice display. "
            "Early sunrise, golden warm light streaming down the Open Market corridor. "
            "Other stalls visible in the background, lanterns still glowing. "
            "Pippip's paws gently placing a red snapper next to a row of mackerel. "
            "Pixar-style 3D animation, cinematic golden hour lighting, shallow depth of field."
        ),
        "character_names": ["Pippip", "Fish Stall", "Open Market"],
        "chain_type": "ROOT",
    },
    {
        "display_order": 1,
        "prompt": (
            "Pippip proudly holds up a big shiny silver fish with both paws across Fish Stall counter, "
            "presenting it to Mai who stands on the other side reaching up excitedly. "
            "Mai pointing at the fish with sparkling eyes, bouncing on her toes. "
            "Open Market bustling behind them, morning crowd walking past. "
            "Pixar-style 3D animation, warm cheerful mood, soft morning light."
        ),
        "character_names": ["Pippip", "Mai", "Fish Stall", "Open Market"],
        "chain_type": "CONTINUATION",
    },
    {
        "display_order": 2,
        "prompt": (
            "Pippip stands on Fish Stall counter juggling three colorful fish high in the air. "
            "A small crowd of amazed customers gathered in the Open Market watching and clapping. "
            "Fish spinning in a perfect arc above Pippip's head. "
            "Midday sun casting sharp shadows, market banners fluttering in the breeze. "
            "Pixar-style 3D animation, dynamic action, energetic and fun, wide shot."
        ),
        "character_names": ["Pippip", "Fish Stall", "Open Market"],
        "chain_type": "CONTINUATION",
    },
    {
        "display_order": 3,
        "prompt": (
            "Close-up: Pippip leans over Fish Stall counter, staring intensely at Golden Fish "
            "sitting alone on the now-empty ice display. Drooling, wide eyes, paws gripping the counter edge. "
            "Golden Fish glowing softly, dramatic spotlight on it. "
            "Open Market darkened and blurred in background, all focus on Pippip and Golden Fish. "
            "Pixar-style 3D animation, comedic tension, dramatic chiaroscuro lighting."
        ),
        "character_names": ["Pippip", "Fish Stall", "Golden Fish", "Open Market"],
        "chain_type": "CONTINUATION",
    },
    {
        "display_order": 4,
        "prompt": (
            "Pippip sits contentedly on a wooden stool behind Fish Stall, eyes closed in bliss, "
            "eating Golden Fish with chopsticks. Bones of the fish on a small plate beside him. "
            "A hand-painted 'SOLD OUT' sign hangs from Fish Stall's canopy. "
            "Open Market at sunset, warm orange and pink glow washing over the scene. "
            "Empty stalls closing up around, peaceful evening atmosphere. "
            "Pixar-style 3D animation, cozy satisfying ending, golden hour lighting."
        ),
        "character_names": ["Pippip", "Fish Stall", "Golden Fish", "Open Market"],
        "chain_type": "CONTINUATION",
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    client = httpx.Client(timeout=60)

    # 1. Create project (also creates Pippip character + calls Google Flow)
    print("Creating project...")
    r = client.post(f"{base}/projects", json=PROJECT)
    if r.status_code not in (200, 201):
        print(f"FAILED to create project: {r.status_code} {r.text}")
        sys.exit(1)
    project = r.json()
    pid = project["id"]
    print(f"  Project: {project['name']} (id={pid})")

    # 2. Get characters linked to project
    print("Fetching characters...")
    r = client.get(f"{base}/projects/{pid}/characters")
    characters = r.json()
    for c in characters:
        print(f"  Character: {c['name']} (id={c['id']}, media_id={c.get('media_id')})")

    # 3. Create video
    print("Creating video...")
    video_data = {**VIDEO, "project_id": pid}
    r = client.post(f"{base}/videos", json=video_data)
    if r.status_code not in (200, 201):
        print(f"FAILED to create video: {r.status_code} {r.text}")
        sys.exit(1)
    video = r.json()
    vid = video["id"]
    print(f"  Video: {video['title']} (id={vid})")

    # 4. Create scenes (chained)
    print("Creating scenes...")
    prev_scene_id = None
    for i, scene_data in enumerate(SCENES):
        payload = {**scene_data, "video_id": vid}
        if prev_scene_id and scene_data["chain_type"] == "CONTINUATION":
            payload["parent_scene_id"] = prev_scene_id

        r = client.post(f"{base}/scenes", json=payload)
        if r.status_code not in (200, 201):
            print(f"  FAILED scene {i+1}: {r.status_code} {r.text}")
            continue
        scene = r.json()
        prev_scene_id = scene["id"]
        print(f"  Scene {i+1}: {scene['prompt'][:60]}... (id={scene['id']}, chain={scene['chain_type']})")

    print(f"\nDone! Project '{project['name']}' ready.")
    print(f"  Project ID: {pid}")
    print(f"  Video ID:   {vid}")
    print(f"  Scenes:     {len(SCENES)}")
    print("\nNext: start generation via POST /api/flow/generate-images or the worker queue.")


if __name__ == "__main__":
    main()
