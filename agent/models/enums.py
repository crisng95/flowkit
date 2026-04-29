from typing import Literal

RequestType = Literal[
    "GENERATE_IMAGE", "REGENERATE_IMAGE", "EDIT_IMAGE",
    "GENERATE_VIDEO", "REGENERATE_VIDEO", "GENERATE_VIDEO_REFS", "UPSCALE_VIDEO", "UPSCALE_VIDEO_LOCAL",
    "GENERATE_CHARACTER_IMAGE", "REGENERATE_CHARACTER_IMAGE", "EDIT_CHARACTER_IMAGE",
]

Orientation = Literal["VERTICAL", "HORIZONTAL"]

StatusType = Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]

ChainType = Literal["ROOT", "CONTINUATION", "INSERT"]

SceneSource = Literal["root", "user", "system"]

ProjectStatus = Literal["ACTIVE", "ARCHIVED", "DELETED"]

VideoStatus = Literal["DRAFT", "PROCESSING", "COMPLETED", "FAILED"]

PaygateTier = Literal["PAYGATE_TIER_ONE", "PAYGATE_TIER_TWO"]

EntityType = Literal["character", "location", "creature", "visual_asset", "generic_troop", "faction"]
