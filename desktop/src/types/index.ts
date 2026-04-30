// Enums
export type RequestType = 'GENERATE_IMAGE' | 'REGENERATE_IMAGE' | 'EDIT_IMAGE' | 'GENERATE_VIDEO' | 'REGENERATE_VIDEO' | 'GENERATE_VIDEO_REFS' | 'UPSCALE_VIDEO' | 'UPSCALE_VIDEO_LOCAL' | 'GENERATE_CHARACTER_IMAGE' | 'REGENERATE_CHARACTER_IMAGE' | 'EDIT_CHARACTER_IMAGE'
export type StatusType = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
export type Orientation = 'VERTICAL' | 'HORIZONTAL'
export type ChainType = 'ROOT' | 'CONTINUATION' | 'INSERT'
export type EntityType = 'character' | 'location' | 'creature' | 'visual_asset' | 'generic_troop' | 'faction'
export type ProjectStatus = 'ACTIVE' | 'ARCHIVED' | 'DELETED'

// Models — match the Python models exactly
export interface Project {
  id: string
  name: string
  description: string | null
  story: string | null
  thumbnail_url: string | null
  language: string
  status: ProjectStatus
  user_paygate_tier: string | null
  material: string
  orientation: Orientation  // 9:16=VERTICAL 16:9=HORIZONTAL
  allow_music?: boolean
  allow_voice?: boolean
  narrator_voice: string | null
  narrator_ref_audio: string | null
  created_at: string
  updated_at: string
}

export interface Character {
  id: string
  name: string
  entity_type: EntityType
  description: string | null
  image_prompt: string | null
  voice_description: string | null
  reference_image_url: string | null
  media_id: string | null
  created_at: string
  updated_at: string
}

export interface Video {
  id: string
  project_id: string
  title: string
  description: string | null
  display_order: number
  status: string
  orientation: Orientation | null
  vertical_url: string | null
  horizontal_url: string | null
  thumbnail_url: string | null
  duration: number | null
  resolution: string | null
  youtube_id?: string | null
  privacy?: string
  tags?: string | null
  created_at: string
  updated_at: string
}

export interface Scene {
  id: string
  video_id: string
  display_order: number
  prompt: string | null
  image_prompt: string | null
  video_prompt: string | null
  character_names: string[] | null
  parent_scene_id: string | null
  chain_type: ChainType
  source: string | null
  vertical_image_url: string | null
  vertical_image_media_id: string | null
  vertical_image_status: StatusType
  vertical_video_url: string | null
  vertical_video_media_id: string | null
  vertical_video_status: StatusType
  vertical_upscale_url: string | null
  vertical_upscale_media_id: string | null
  vertical_upscale_status: StatusType
  horizontal_image_url: string | null
  horizontal_image_media_id: string | null
  horizontal_image_status: StatusType
  horizontal_video_url: string | null
  horizontal_video_media_id: string | null
  horizontal_video_status: StatusType
  horizontal_upscale_url: string | null
  horizontal_upscale_media_id: string | null
  horizontal_upscale_status: StatusType
  narrator_text: string | null
  tts_status?: StatusType
  tts_audio_path?: string | null
  trim_start: number | null
  trim_end: number | null
  duration: number | null
  created_at: string
  updated_at: string
}

export interface Request {
  id: string
  project_id: string | null
  video_id: string | null
  scene_id: string | null
  character_id: string | null
  type: RequestType
  orientation: Orientation | null
  status: StatusType
  request_id: string | null
  media_id: string | null
  output_url: string | null
  error_message: string | null
  retry_count: number
  created_at: string
  updated_at: string
}

// WebSocket event
export interface WSEvent {
  type: string
  data: Record<string, unknown>
  timestamp: string
}
