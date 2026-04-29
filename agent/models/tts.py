"""Pydantic models for TTS endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class TTSGenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    instruct: Optional[str] = Field(None, max_length=200)
    ref_audio: Optional[str] = Field(None, max_length=500)
    ref_text: Optional[str] = None
    voice_id: Optional[str] = Field(None, min_length=1, max_length=128)
    model_id: Optional[str] = Field(None, min_length=1, max_length=128)
    speed: float = Field(1.0, ge=0.5, le=3.0)


class TTSGenerateResponse(BaseModel):
    audio_path: str
    duration: Optional[float] = None
    sample_rate: int = 24000


class NarrateVideoRequest(BaseModel):
    project_id: str
    orientation: Literal["HORIZONTAL", "VERTICAL"] = "HORIZONTAL"
    speed: float = Field(1.0, ge=0.5, le=3.0)
    instruct: Optional[str] = Field(None, max_length=200)
    ref_audio: Optional[str] = Field(None, max_length=500)  # Path to voice template WAV
    ref_text: Optional[str] = None   # Transcript of ref_audio (auto-resolved from template)
    template: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9_-]{1,64}$")  # Voice template name
    voice_id: Optional[str] = Field(None, min_length=1, max_length=128)
    model_id: Optional[str] = Field(None, min_length=1, max_length=128)
    mix: bool = True
    sfx_volume: float = Field(0.4, ge=0.0, le=2.0)
    from_scene: Optional[int] = Field(None, ge=0)  # Start display_order (inclusive)
    to_scene: Optional[int] = Field(None, ge=0)    # End display_order (inclusive)


class SceneNarrationResult(BaseModel):
    scene_id: str
    display_order: int
    narrator_text: Optional[str] = None
    audio_path: Optional[str] = None
    duration: Optional[float] = None
    status: str  # COMPLETED, SKIPPED, FAILED
    error: Optional[str] = None


class NarrateVideoResponse(BaseModel):
    video_id: str
    project_id: str
    scenes: list[SceneNarrationResult]
    scenes_narrated: int
    scenes_skipped: int
    scenes_failed: int
    total_narration_duration: Optional[float] = None


class VoiceTemplateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)  # Sample text to generate voice template
    instruct: str = Field(..., max_length=200)  # Voice design: "male, low pitch, young adult"
    name: str = Field("voice_template_1", pattern=r"^[a-zA-Z0-9_-]{1,64}$")  # Template name for saving
    voice_id: Optional[str] = Field(None, min_length=1, max_length=128)
    model_id: Optional[str] = Field(None, min_length=1, max_length=128)
    speed: float = Field(1.0, ge=0.5, le=3.0)


class VoiceTemplateImportRequest(BaseModel):
    """Import an existing local audio file as a reusable voice template."""
    name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    audio_path: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1, max_length=5000)
    instruct: str = Field("", max_length=200)
    voice_id: Optional[str] = Field(None, min_length=1, max_length=128)
    model_id: Optional[str] = Field(None, min_length=1, max_length=128)
    copy_audio: bool = True


class VoiceTemplateResponse(BaseModel):
    name: str
    audio_path: str
    text: str
    instruct: str
    voice_id: Optional[str] = None
    model_id: Optional[str] = None
    duration: Optional[float] = None
    sample_rate: int = 24000


class VoiceTemplateListItem(BaseModel):
    name: str
    audio_path: str
    voice_id: Optional[str] = None
    model_id: Optional[str] = None
    duration: Optional[float] = None


class TTSSettingsResponse(BaseModel):
    provider: Literal["elevenlabs", "omnivoice"]
    elevenlabs_api_base: str
    elevenlabs_model_id: str
    elevenlabs_default_voice_id: str
    elevenlabs_timeout_sec: float
    elevenlabs_max_retries: int
    elevenlabs_api_key_set: bool
    elevenlabs_api_key_masked: str = ""


class TTSSettingsUpdateRequest(BaseModel):
    provider: Optional[Literal["elevenlabs", "omnivoice"]] = None
    elevenlabs_api_base: Optional[str] = Field(None, max_length=300)
    elevenlabs_api_key: Optional[str] = Field(None, max_length=300)
    clear_elevenlabs_api_key: bool = False
    elevenlabs_model_id: Optional[str] = Field(None, max_length=128)
    elevenlabs_default_voice_id: Optional[str] = Field(None, max_length=128)
    elevenlabs_timeout_sec: Optional[float] = Field(None, ge=5, le=300)
    elevenlabs_max_retries: Optional[int] = Field(None, ge=0, le=10)


class TTSModelOption(BaseModel):
    model_id: str
    name: str
    description: str = ""
    language_count: int = 0


class TTSVoiceOption(BaseModel):
    voice_id: str
    name: str
    category: str = ""
    preview_url: Optional[str] = None
    labels: dict[str, str] = Field(default_factory=dict)


class TTSCatalogResponse(BaseModel):
    provider: Literal["elevenlabs", "omnivoice"]
    source: Literal["api", "fallback", "mixed"] = "fallback"
    models: list[TTSModelOption] = Field(default_factory=list)
    voices: list[TTSVoiceOption] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
