from typing import Literal

RequestType = Literal[
    "GENERATE_IMAGES", "GENERATE_VIDEO", "GENERATE_VIDEO_REFS",
    "UPSCALE_VIDEO", "UPSCALE_IMAGE", "GENERATE_CHARACTER_IMAGE",
    "UPLOAD_IMAGE", "CHECK_STATUS"
]

Orientation = Literal["VERTICAL", "HORIZONTAL"]

StatusType = Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]

ChainType = Literal["ROOT", "CONTINUATION", "INSERT"]

ProjectStatus = Literal["ACTIVE", "ARCHIVED", "DELETED"]

VideoStatus = Literal["DRAFT", "PROCESSING", "COMPLETED", "FAILED"]

PaygateTier = Literal["PAYGATE_TIER_ONE", "PAYGATE_TIER_TWO"]

EntityType = Literal["character", "location", "creature", "visual_asset", "generic_troop", "faction"]
