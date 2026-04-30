import { useState, useEffect, useCallback, useRef, type ChangeEvent } from "react";
import {
  Plus,
  Trash2,
  ChevronRight,
  Users,
  Image,
  Film,
  Zap,
  Music,
  Star,
  Mic,
  Download,
  FolderOpen,
  FileText,
  Link2,
  Tv2,
  Wrench,
  RefreshCw,
  Sparkles,
  ImageIcon,
  Upload,
  Bot,
  BookOpen,
  Boxes,
  Wifi,
  WifiOff,
} from "lucide-react";
import { fetchAPI, patchAPI } from "../api/client";
import { aiGenerate, loadGeneralSettings, type ProviderType } from "../api/ai-service";
import { useWebSocket } from "../api/useWebSocket";
import { useExtensionStatus } from "../api/useExtensionStatus";
import type { Scene, Character, Video } from "../types";
import EditableText from "../components/projects/EditableText";
import BatchStatusBar from "../components/ui/BatchStatusBar";
import AddSceneModal from "../components/projects/AddSceneModal";
import ReviewVideoModal from "../components/pipeline/ReviewVideoModal";
import ReviewSceneModal from "../components/pipeline/ReviewSceneModal";
import PreflightModal, {
  type PreflightCheckItem,
} from "../components/pipeline/PreflightModal";
import TTSSetupModal from "../components/pipeline/TTSSetupModal";
import ExportModal from "../components/pipeline/ExportModal";
import MusicModal from "../components/pipeline/MusicModal";
import GenNarratorModal from "../components/pipeline/GenNarratorModal";
import ChainVideosModal from "../components/pipeline/ChainVideosModal";
import ThumbnailModal from "../components/pipeline/ThumbnailModal";
import YouTubeSEOModal from "../components/pipeline/YouTubeSEOModal";
import YouTubeUploadModal from "../components/pipeline/YouTubeUploadModal";
import FixUUIDsModal from "../components/pipeline/FixUUIDsModal";
import RefreshURLsModal from "../components/pipeline/RefreshURLsModal";
import UploadImageModal from "../components/pipeline/UploadImageModal";
import TextOverlaysModal from "../components/pipeline/TextOverlaysModal";
import BrandLogoModal from "../components/pipeline/BrandLogoModal";
import ReviewBoardModal from "../components/pipeline/ReviewBoardModal";
import CreativeMixModal from "../components/pipeline/CreativeMixModal";
import GuideModal from "../components/pipeline/GuideModal";
import PipelineOrchestratorModal from "../components/pipeline/PipelineOrchestratorModal";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Separator } from "../components/ui/separator";
import { Dialog, DialogContent } from "../components/ui/dialog";
import {
  normalizeOrientation,
  orientationAspect,
  orientationPrefix,
  sceneStatus,
  sceneUrl,
} from "../lib/orientation";
import { cn } from "../lib/utils";

interface Props {
  video: Video;
  projectId: string;
  onBack: () => void;
}

interface SceneFailureSummary {
  imageIds: string[];
  videoIds: string[];
}

interface SceneImageSource {
  prefix: "vertical" | "horizontal";
  url: string | null;
  mediaId: string | null;
}

interface SceneVideoSource {
  prefix: "vertical" | "horizontal";
  stage: "video" | "upscale";
  url: string | null;
  mediaId: string | null;
}

interface ScriptScenePayload {
  display_order?: number | null;
  prompt?: string | null;
  image_prompt?: string | null;
  video_prompt?: string | null;
  narrator_text?: string | null;
  character_names?: string[] | string | null;
  transition_prompt?: string | null;
  chain_type?: "ROOT" | "CONTINUATION" | "INSERT";
  source?: string | null;
}

interface ScriptVideoPayload {
  title?: string | null;
  description?: string | null;
  orientation?: string | null;
}

interface ScriptImportPayload {
  format_version?: number;
  title?: string | null;
  description?: string | null;
  orientation?: string | null;
  video?: ScriptVideoPayload;
  scenes: ScriptScenePayload[];
}

interface ScriptImportResponse {
  ok: boolean;
  video_id: string;
  scenes_total: number;
  deleted_scenes: number;
  deleted_requests: number;
  orientation: string;
  title: string;
}

function parseSignedUrlExpiresAt(
  url: string | null | undefined,
): number | null {
  if (!url) return null;
  if (!/^https?:\/\//i.test(url)) return null;
  try {
    const parsed = new URL(url);
    const raw =
      parsed.searchParams.get("Expires") ?? parsed.searchParams.get("expires");
    if (raw) {
      const ts = Number.parseInt(raw, 10);
      if (Number.isFinite(ts) && ts > 0) return ts * 1000;
    }

    const xGoogExpires =
      parsed.searchParams.get("X-Goog-Expires") ??
      parsed.searchParams.get("x-goog-expires");
    const xGoogDate =
      parsed.searchParams.get("X-Goog-Date") ??
      parsed.searchParams.get("x-goog-date");
    if (!xGoogExpires || !xGoogDate) return null;

    const secs = Number.parseInt(xGoogExpires, 10);
    if (!Number.isFinite(secs) || secs <= 0) return null;
    const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(xGoogDate);
    if (!m) return null;
    const baseMs = Date.UTC(
      Number(m[1]),
      Number(m[2]) - 1,
      Number(m[3]),
      Number(m[4]),
      Number(m[5]),
      Number(m[6]),
    );
    if (!Number.isFinite(baseMs) || baseMs <= 0) return null;
    return baseMs + secs * 1000;
  } catch {
    return null;
  }
}

function isExpiredSignedUrl(
  url: string | null | undefined,
  nowMs = Date.now(),
): boolean {
  const expiresAt = parseSignedUrlExpiresAt(url);
  if (!expiresAt) return false;
  return expiresAt <= nowMs;
}

function isFlowRedirectMediaUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  return /media\.getMediaUrlRedirect/i.test(url);
}

function needsMediaUrlRefresh(
  url: string | null | undefined,
  nowMs = Date.now(),
): boolean {
  if (!url) return true;
  if (!/^https?:\/\//i.test(url)) return false;
  if (isFlowRedirectMediaUrl(url)) return true;
  return isExpiredSignedUrl(url, nowMs);
}

function pickDirectMediaUrl(payload: any): string | null {
  const candidates = [
    payload?.url,
    payload?.servingUri,
    payload?.fifeUrl,
    payload?.imageUri,
    payload?.videoUri,
    payload?.data?.url,
    payload?.data?.servingUri,
    payload?.data?.fifeUrl,
    payload?.data?.imageUri,
    payload?.data?.videoUri,
  ];
  for (const value of candidates) {
    if (typeof value !== "string") continue;
    if (!/^https?:\/\//i.test(value)) continue;
    if (isFlowRedirectMediaUrl(value)) continue;
    return value;
  }
  return null;
}

function resolveSceneImageSource(
  scene: Scene,
  orientation: string,
): SceneImageSource | null {
  const primary = orientationPrefix(orientation);
  const secondary = primary === "vertical" ? "horizontal" : "vertical";
  const slots: Array<"vertical" | "horizontal"> = [primary, secondary];
  for (const prefix of slots) {
    const url = (scene as any)[`${prefix}_image_url`] as string | null;
    const mediaId = (scene as any)[`${prefix}_image_media_id`] as string | null;
    if (url || mediaId)
      return { prefix, url: url ?? null, mediaId: mediaId ?? null };
  }
  return null;
}

function resolveSceneVideoSource(
  scene: Scene,
  orientation: string,
): SceneVideoSource | null {
  const primary = orientationPrefix(orientation);
  const secondary = primary === "vertical" ? "horizontal" : "vertical";
  const slots: Array<"vertical" | "horizontal"> = [primary, secondary];
  for (const prefix of slots) {
    const videoUrl = (scene as any)[`${prefix}_video_url`] as string | null;
    const videoMediaId = (scene as any)[`${prefix}_video_media_id`] as
      | string
      | null;
    if (videoUrl || videoMediaId) {
      return {
        prefix,
        stage: "video",
        url: videoUrl ?? null,
        mediaId: videoMediaId ?? null,
      };
    }
    const upscaleUrl = (scene as any)[`${prefix}_upscale_url`] as string | null;
    const upscaleMediaId = (scene as any)[`${prefix}_upscale_media_id`] as
      | string
      | null;
    if (upscaleUrl || upscaleMediaId) {
      return {
        prefix,
        stage: "upscale",
        url: upscaleUrl ?? null,
        mediaId: upscaleMediaId ?? null,
      };
    }
  }
  return null;
}

function StatusDot({ status }: { status: string }) {
  const cls =
    status === "COMPLETED"
      ? "bg-green-500"
      : status === "FAILED"
        ? "bg-red-500"
        : status === "PROCESSING"
          ? "bg-amber-400"
          : "bg-[hsl(var(--muted-foreground)/0.4)]";
  return (
    <span
      className={cn("inline-block w-2 h-2 rounded-full flex-shrink-0", cls)}
      title={status}
    />
  );
}

function parseChars(raw: string[] | string | null): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function slugForFile(text: string): string {
  const cleaned = text
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || "video";
}

function extractLocalPath(url: string | null | undefined): string | null {
  if (!url) return null;
  const text = String(url).trim();
  if (!text) return null;
  if (/^(\/|[A-Za-z]:[\\/])/.test(text)) return text;
  try {
    const parsed = new URL(text);
    const host = (parsed.hostname || "").toLowerCase();
    if (host !== "127.0.0.1" && host !== "localhost") return null;
    if (parsed.pathname.replace(/\/+$/, "") !== "/api/flow/local-media")
      return null;
    const p = parsed.searchParams.get("path");
    if (!p) return null;
    return decodeURIComponent(p);
  } catch {
    return null;
  }
}

// ─── Scene List Item ───────────────────────────────────────────
function SceneListItem({
  scene,
  selected,
  orientation,
  imageOverride,
  onImageError,
  onClick,
}: {
  scene: Scene;
  selected: boolean;
  orientation: string;
  imageOverride?: string | null;
  onImageError?: () => void;
  onClick: () => void;
}) {
  const chars = parseChars(scene.character_names);
  const thumb = imageOverride ?? sceneUrl(scene, orientation, "image");
  const imageStatus = sceneStatus(scene, orientation, "image");
  const videoStatus = sceneStatus(scene, orientation, "video");
  const ttsStatus = sceneStatus(scene, orientation, "tts");
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-lg p-2.5 flex gap-2 transition-colors border",
        selected
          ? "bg-[hsl(var(--card))] border-[hsl(var(--ring)/0.5)]"
          : "bg-transparent border-[hsl(var(--border))] hover:bg-[hsl(var(--accent)/0.5)]",
      )}
    >
      <div
        className="flex-shrink-0 rounded overflow-hidden bg-[hsl(var(--muted))]"
        style={{ width: 48, height: 34 }}
      >
        {thumb ? (
          <img
            src={thumb}
            className="w-full h-full object-cover"
            alt=""
            onError={() => onImageError?.()}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-xs text-[hsl(var(--muted-foreground))]">
            #
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0 flex flex-col gap-0.5">
        <div className="flex items-center gap-1 text-xs font-semibold">
          <span>#{scene.display_order + 1}</span>
          {chars.length > 0 && (
            <span className="text-[hsl(var(--muted-foreground))] font-normal truncate">
              · {chars.join(", ")}
            </span>
          )}
        </div>
        <div className="text-xs truncate text-[hsl(var(--muted-foreground))]">
          {scene.prompt ?? scene.video_prompt ?? "(chưa có prompt)"}
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
            <StatusDot status={imageStatus} /> img
          </span>
          <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
            <StatusDot status={videoStatus} /> vid
          </span>
          <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
            <StatusDot status={ttsStatus} /> tts
          </span>
        </div>
      </div>
      <ChevronRight
        size={12}
        className="text-[hsl(var(--muted-foreground))] flex-shrink-0 self-center"
      />
    </button>
  );
}

// ─── Scene Editor ──────────────────────────────────────────────
function SceneEditor({
  scene,
  characters,
  projectId,
  videoId,
  orientation,
  imageOverride,
  videoOverride,
  onImageError,
  onVideoError,
  onSaved,
  onDeleted,
  onReviewScene,
}: {
  scene: Scene;
  characters: Character[];
  projectId: string;
  videoId: string;
  orientation: string;
  imageOverride?: string | null;
  videoOverride?: string | null;
  onImageError?: () => void;
  onVideoError?: () => void;
  onSaved: () => void;
  onDeleted: () => void;
  onReviewScene: () => void;
}) {
  const [selectedChars, setSelectedChars] = useState<string[]>(
    parseChars(scene.character_names),
  );
  const [regenMsg, setRegenMsg] = useState("");
  const [rewritingPrompt, setRewritingPrompt] = useState(false);
  const [preview, setPreview] = useState<{
    url: string;
    type: "image" | "video";
  } | null>(null);

  useEffect(() => {
    setSelectedChars(parseChars(scene.character_names));
  }, [scene.id, scene.character_names]);

  const patch = async (field: string, value: string | null) => {
    await patchAPI(`/api/scenes/${scene.id}`, { [field]: value });
    onSaved();
  };

  const toggleChar = async (name: string) => {
    const next = selectedChars.includes(name)
      ? selectedChars.filter((n) => n !== name)
      : [...selectedChars, name];
    setSelectedChars(next);
    await patchAPI(`/api/scenes/${scene.id}`, { character_names: next });
  };

  const deleteScene = async () => {
    if (!confirm("Xóa phân cảnh này?")) return;
    await fetchAPI(`/api/scenes/${scene.id}`, { method: "DELETE" });
    onDeleted();
  };

  const regen = async (type: "REGENERATE_IMAGE" | "REGENERATE_VIDEO") => {
    setRegenMsg(
      `Đang gửi yêu cầu ${type === "REGENERATE_IMAGE" ? "tạo lại ảnh" : "tạo lại video"}...`,
    );
    try {
      await fetchAPI("/api/requests/batch", {
        method: "POST",
        body: JSON.stringify({
          requests: [
            {
              type,
              project_id: projectId,
              video_id: videoId,
              scene_id: scene.id,
              orientation,
            },
          ],
        }),
      });
      setRegenMsg(
        type === "REGENERATE_IMAGE"
          ? "✓ Đã gửi — tạo lại ảnh"
          : "✓ Đã gửi — tạo lại video",
      );
    } catch (e: any) {
      setRegenMsg(`Lỗi: ${e.message}`);
    }
    setTimeout(() => setRegenMsg(""), 3000);
  };

  const regenerateSafePrompt = async () => {
    if (rewritingPrompt) return;
    setRewritingPrompt(true);
    setRegenMsg("Đang viết lại prompt an toàn bằng AI...");
    try {
      const defaults = loadGeneralSettings();
      const provider = defaults.defaultProvider as ProviderType;
      const systemPrompt = `You are a senior safe-content prompt editor for Google Flow image/video generation.
Return valid JSON only.
Keep story meaning, but rewrite to avoid violent/graphic/hate/sexual/extremist wording.
For image prompt: action + setting only, never character appearance details.`;
      const prompt = `Rewrite this scene into a SAFE version while preserving narrative intent.

Current scene data:
{
  "prompt": ${JSON.stringify(scene.prompt ?? "")},
  "video_prompt": ${JSON.stringify(scene.video_prompt ?? "")},
  "narrator_text": ${JSON.stringify(scene.narrator_text ?? "")},
  "character_names": ${JSON.stringify(parseChars(scene.character_names))}
}

Requirements:
- Keep the same scene purpose and timeline beat.
- Remove/soften explicit violence, gore, hate, sexual, extremist cues.
- If conflict exists, convert to non-graphic cinematic language (e.g. tension, aftermath, diplomacy, strategic movement).
- image prompt must be in English.
- video_prompt format: "0-3s: ... 3-6s: ... 6-8s: ...".
- narrator_text keep the same language style as input narrator_text.

Return JSON:
{
  "prompt": "safe image prompt",
  "video_prompt": "safe motion prompt",
  "narrator_text": "safe narration"
}`;

      const rewritten = await aiGenerate<{
        prompt?: string;
        video_prompt?: string;
        narrator_text?: string;
      }>(prompt, systemPrompt, provider);

      const nextPrompt = String(rewritten?.prompt ?? "").trim();
      const nextVideoPrompt = String(rewritten?.video_prompt ?? "").trim();
      const nextNarratorText = String(rewritten?.narrator_text ?? "").trim();

      if (!nextPrompt && !nextVideoPrompt && !nextNarratorText) {
        throw new Error("AI không trả về prompt hợp lệ.");
      }

      await patchAPI(`/api/scenes/${scene.id}`, {
        prompt: nextPrompt || scene.prompt || null,
        video_prompt: nextVideoPrompt || scene.video_prompt || null,
        narrator_text: nextNarratorText || scene.narrator_text || null,
      });
      onSaved();
      setRegenMsg("✓ Đã cập nhật prompt an toàn cho cảnh. Giờ có thể tạo lại ảnh/video.");
    } catch (e: any) {
      setRegenMsg(`Lỗi gen lại prompt: ${e?.message ?? "unknown"}`);
    } finally {
      setRewritingPrompt(false);
      setTimeout(() => setRegenMsg(""), 4500);
    }
  };

  const imagePreview = imageOverride ?? sceneUrl(scene, orientation, "image");
  const videoPreview =
    videoOverride ??
    sceneUrl(scene, orientation, "video") ??
    sceneUrl(scene, orientation, "upscale");
  const imageLocalPath = extractLocalPath(imagePreview);
  const videoLocalPath = extractLocalPath(videoPreview);
  const videoStatus = sceneStatus(scene, orientation, "video");
  const statusRows = (["image", "video", "tts", "upscale"] as const).map(
    (stage) => ({
      key: stage,
      label:
        stage === "image"
          ? "Hình ảnh"
          : stage === "video"
            ? "Video"
            : stage === "tts"
              ? "Giọng đọc (TTS)"
              : "4K",
      status: sceneStatus(scene, orientation, stage),
    }),
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))]">
          Cảnh #{scene.display_order + 1}
        </span>
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => regen("REGENERATE_IMAGE")}
          >
            <RefreshCw size={11} /> Tạo lại ảnh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => regen("REGENERATE_VIDEO")}
          >
            <Film size={11} /> Tạo lại video
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={regenerateSafePrompt}
            disabled={rewritingPrompt}
          >
            <Sparkles size={11} className={rewritingPrompt ? "animate-pulse" : ""} />
            {rewritingPrompt ? "Đang viết lại prompt..." : "Gen lại prompt (AI)"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onReviewScene}>
            <Star size={11} /> Review cảnh
          </Button>
          <Button variant="destructive" size="sm" onClick={deleteScene}>
            <Trash2 size={11} /> Xóa
          </Button>
        </div>
      </div>

      {regenMsg && (
        <div className="text-xs px-2.5 py-1.5 rounded-md bg-blue-50 border border-blue-200 text-blue-700">
          {regenMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Ảnh
          </Label>
          {imagePreview ? (
            <div
              className="relative group rounded-md overflow-hidden cursor-zoom-in border bg-[hsl(var(--muted)/0.5)]"
              onClick={() => setPreview({ url: imagePreview, type: "image" })}
            >
              <div className="h-[360px] p-2 flex items-center justify-center">
                <img
                  src={imagePreview}
                  alt="scene"
                  className="max-w-full max-h-full object-contain"
                  onError={() => onImageError?.()}
                />
              </div>
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                <span className="opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs font-medium bg-black/50 px-2 py-1 rounded">
                  Xem ảnh đầy đủ
                </span>
              </div>
            </div>
          ) : (
            <div className="h-[360px] rounded-md border bg-[hsl(var(--muted)/0.5)] text-[hsl(var(--muted-foreground))] text-xs flex items-center justify-center">
              Chưa có ảnh
            </div>
          )}
          {imageLocalPath && (
            <div className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono break-all">
              Local: {imageLocalPath}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Video
          </Label>
          {videoPreview && videoStatus === "COMPLETED" ? (
            <div
              className="relative group rounded-md overflow-hidden cursor-pointer border bg-black"
              onClick={() => setPreview({ url: videoPreview, type: "video" })}
            >
              <div className="h-[360px] p-2 flex items-center justify-center">
                <video
                  src={videoPreview}
                  className="max-w-full max-h-full object-contain"
                  muted
                  playsInline
                  preload="metadata"
                  onError={() => onVideoError?.()}
                />
              </div>
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                <span className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-white text-xs font-medium bg-black/50 px-2 py-1 rounded">
                  <Film size={11} /> Xem video
                </span>
              </div>
            </div>
          ) : (
            <div className="h-[360px] rounded-md border bg-[hsl(var(--muted)/0.5)] text-[hsl(var(--muted-foreground))] text-xs flex items-center justify-center">
              {videoStatus === "PROCESSING"
                ? "Video đang xử lý..."
                : videoStatus === "FAILED"
                  ? "Video lỗi, hãy tạo lại"
                  : "Chưa có video"}
            </div>
          )}
          {videoLocalPath && (
            <div className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono break-all">
              Local: {videoLocalPath}
            </div>
          )}
        </div>
      </div>

      {/* Lightbox */}
      {preview && (
        <Dialog open onOpenChange={() => setPreview(null)}>
          <DialogContent className="max-w-5xl w-full p-0 overflow-hidden bg-black border-0">
            <div className="flex items-center justify-center min-h-[60vh] max-h-[90vh]">
              {preview.type === "image" ? (
                <img
                  src={preview.url}
                  alt="preview"
                  className="max-w-full max-h-[88vh] object-contain"
                />
              ) : (
                <video
                  src={preview.url}
                  controls
                  autoPlay
                  className="max-w-full max-h-[88vh]"
                />
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      <div className="flex flex-col gap-1.5">
        <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
          Prompt hình ảnh
        </Label>
        <EditableText
          value={scene.prompt ?? ""}
          onSave={(v) => patch("prompt", v || null)}
          multiline
          className="text-xs"
          placeholder="Mô tả hình ảnh (action + bối cảnh, tiếng Anh)"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
          Prompt video
        </Label>
        <EditableText
          value={scene.video_prompt ?? ""}
          onSave={(v) => patch("video_prompt", v || null)}
          multiline
          className="text-xs"
          placeholder="0-3s: quay trái. 3-6s: zoom vào. 6-8s: giữ nguyên."
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
          Lời dẫn (TTS)
        </Label>
        <EditableText
          value={scene.narrator_text ?? ""}
          onSave={(v) => patch("narrator_text", v || null)}
          multiline
          className="text-xs"
          placeholder="Lời bình cho TTS..."
        />
      </div>

      {characters.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <Label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Nhân vật
          </Label>
          <div className="flex flex-wrap gap-1.5">
            {characters.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => toggleChar(c.name)}
                className={cn(
                  "px-2.5 py-1 rounded-md text-xs font-medium border transition-colors",
                  selectedChars.includes(c.name)
                    ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]"
                    : "bg-transparent text-[hsl(var(--foreground))] border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))]",
                )}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <Separator />
      <div className="flex flex-col gap-1">
        {statusRows.map((row) => (
          <div key={row.key} className="flex items-center gap-2 text-xs">
            <StatusDot status={row.status} />
            <span className="text-[hsl(var(--muted-foreground))]">
              {row.label}
            </span>
            <span className="ml-auto font-mono text-[10px] text-[hsl(var(--foreground))]">
              {row.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Pipeline Bar ──────────────────────────────────────────────
function PipelineBar({
  projectId,
  videoId,
  video,
  orientation,
  lastEventType,
}: {
  projectId: string;
  videoId: string;
  video: Video;
  orientation: string;
  lastEventType: string | null;
}) {
  const [showReview, setShowReview] = useState(false);
  const [showTTS, setShowTTS] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showMusic, setShowMusic] = useState(false);
  const [showNarrator, setShowNarrator] = useState(false);
  const [showChain, setShowChain] = useState(false);
  const [showThumbnail, setShowThumbnail] = useState(false);
  const [showYTSEO, setShowYTSEO] = useState(false);
  const [showYTUpload, setShowYTUpload] = useState(false);
  const [showFixUUIDs, setShowFixUUIDs] = useState(false);
  const [showRefreshURLs, setShowRefreshURLs] = useState(false);
  const [showUploadImage, setShowUploadImage] = useState(false);
  const [showTextOverlays, setShowTextOverlays] = useState(false);
  const [showBrandLogo, setShowBrandLogo] = useState(false);
  const [showReviewBoard, setShowReviewBoard] = useState(false);
  const [showCreativeMix, setShowCreativeMix] = useState(false);
  const [showPipeline, setShowPipeline] = useState(false);
  const [showCameraGuide, setShowCameraGuide] = useState(false);
  const [showThumbnailGuide, setShowThumbnailGuide] = useState(false);
  const [showPreflight, setShowPreflight] = useState(false);
  const [pendingStage, setPendingStage] = useState<
    "images" | "videos" | "video_refs" | "upscale" | null
  >(null);
  const [preflightChecks, setPreflightChecks] = useState<PreflightCheckItem[]>(
    [],
  );
  const [failedImageCount, setFailedImageCount] = useState(0);
  const [failedVideoCount, setFailedVideoCount] = useState(0);
  const [retryingFailedImages, setRetryingFailedImages] = useState(false);
  const [retryingFailedVideos, setRetryingFailedVideos] = useState(false);
  const [batchMsg, setBatchMsg] = useState("");
  const [downloadingAssets, setDownloadingAssets] = useState(false);
  const [downloadAssetsDir, setDownloadAssetsDir] = useState("");

  const loadSceneFailures =
    useCallback(async (): Promise<SceneFailureSummary> => {
      const scenes = await fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`);
      const imageIds = scenes
        .filter(
          (scene) => sceneStatus(scene, orientation, "image") === "FAILED",
        )
        .map((scene) => scene.id);
      const videoIds = scenes
        .filter(
          (scene) => sceneStatus(scene, orientation, "video") === "FAILED",
        )
        .map((scene) => scene.id);
      return { imageIds, videoIds };
    }, [videoId, orientation]);

  const refreshFailureCounts = useCallback(async () => {
    try {
      const summary = await loadSceneFailures();
      setFailedImageCount(summary.imageIds.length);
      setFailedVideoCount(summary.videoIds.length);
    } catch {
      setFailedImageCount(0);
      setFailedVideoCount(0);
    }
  }, [loadSceneFailures]);

  useEffect(() => {
    refreshFailureCounts();
  }, [refreshFailureCounts, lastEventType]);

  const queueMissingRefs = async () => {
    const chars = await fetchAPI<{ id: string; media_id: string | null }[]>(
      `/api/projects/${projectId}/characters`,
    );
    const missing = chars.filter((c) => !c.media_id);
    const requests = missing.map((c) => ({
      type: "GENERATE_CHARACTER_IMAGE",
      project_id: projectId,
      character_id: c.id,
      orientation,
    }));
    if (!requests.length) return 0;
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({ requests }),
    });
    setBatchMsg(`✓ Đã gửi tạo ảnh ref cho ${requests.length} thực thể.`);
    return requests.length;
  };

  const hasReadyImageForOrientation = (scene: Scene): boolean => {
    const prefix = orientationPrefix(orientation);
    const mediaId = (scene as any)[`${prefix}_image_media_id`] as
      | string
      | null
      | undefined;
    return typeof mediaId === "string" && mediaId.trim().length > 0;
  };

  const hasReadyVideoForOrientation = (scene: Scene): boolean => {
    const prefix = orientationPrefix(orientation);
    const mediaId = (scene as any)[`${prefix}_video_media_id`] as
      | string
      | null
      | undefined;
    return typeof mediaId === "string" && mediaId.trim().length > 0;
  };

  const queueMissingImages = async () => {
    const scenes = await fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`);
    const missing = scenes.filter(
      (s) => sceneStatus(s, orientation, "image") !== "COMPLETED",
    );
    const requests = missing.map((s) => ({
      type: "GENERATE_IMAGE",
      project_id: projectId,
      video_id: videoId,
      scene_id: s.id,
      orientation,
    }));
    if (!requests.length) return 0;
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({ requests }),
    });
    setBatchMsg(`✓ Đã gửi tạo ảnh cho ${requests.length} cảnh còn thiếu.`);
    return requests.length;
  };

  const queueMissingVideos = async () => {
    const scenes = await fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`);
    const readyScenes = scenes.filter(hasReadyImageForOrientation);
    const missing = readyScenes.filter(
      (s) => sceneStatus(s, orientation, "video") !== "COMPLETED",
    );
    const skippedNoImage = scenes.length - readyScenes.length;
    const requests = missing.map((s) => ({
      type: "GENERATE_VIDEO",
      project_id: projectId,
      video_id: videoId,
      scene_id: s.id,
      orientation,
    }));
    if (!requests.length) {
      if (skippedNoImage > 0) {
        setBatchMsg(
          `Chưa có cảnh nào đủ ảnh để gen video (đã bỏ qua ${skippedNoImage} cảnh thiếu ảnh).`,
        );
      }
      return 0;
    }
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({ requests }),
    });
    setBatchMsg(
      `✓ Đã gửi tạo video cho ${requests.length} cảnh đã có ảnh${
        skippedNoImage > 0 ? ` (bỏ qua ${skippedNoImage} cảnh thiếu ảnh)` : ""
      }.`,
    );
    return requests.length;
  };

  const genRefs = async () => {
    const count = await queueMissingRefs();
    if (!count) setBatchMsg("Tất cả thực thể đã có ảnh ref.");
  };

  const genImages = async () => {
    const scenes = await fetchAPI<{ id: string }[]>(
      `/api/scenes?video_id=${videoId}`,
    );
    if (!scenes.length) throw new Error("Chưa có phân cảnh nào.");
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({
        requests: scenes.map((s) => ({
          type: "GENERATE_IMAGE",
          project_id: projectId,
          video_id: videoId,
          scene_id: s.id,
          orientation,
        })),
      }),
    });
    setBatchMsg(`✓ Đã gửi tạo ảnh cho ${scenes.length} cảnh.`);
  };

  const genVideos = async () => {
    const scenes = await fetchAPI<Scene[]>(
      `/api/scenes?video_id=${videoId}`,
    );
    if (!scenes.length) throw new Error("Chưa có phân cảnh nào.");
    const readyScenes = scenes.filter(hasReadyImageForOrientation);
    const targetScenes = readyScenes.filter(
      (s) => sceneStatus(s, orientation, "video") !== "COMPLETED",
    );
    if (!targetScenes.length) {
      if (!readyScenes.length) {
        throw new Error("Chưa có cảnh nào có ảnh sẵn sàng để tạo video.");
      }
      setBatchMsg("Tất cả cảnh đã có ảnh đều đã có video.");
      return;
    }
    const skippedNoImage = scenes.length - readyScenes.length;
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({
        requests: targetScenes.map((s) => ({
          type: "GENERATE_VIDEO",
          project_id: projectId,
          video_id: videoId,
          scene_id: s.id,
          orientation,
        })),
      }),
    });
    setBatchMsg(
      `✓ Đã gửi tạo video cho ${targetScenes.length} cảnh đã có ảnh${
        skippedNoImage > 0 ? ` (bỏ qua ${skippedNoImage} cảnh thiếu ảnh)` : ""
      }.`,
    );
  };

  const genVideoRefs = async () => {
    const scenes = await fetchAPI<Scene[]>(
      `/api/scenes?video_id=${videoId}`,
    );
    if (!scenes.length) throw new Error("Chưa có phân cảnh nào.");
    const readyScenes = scenes.filter(hasReadyImageForOrientation);
    const targetScenes = readyScenes.filter(
      (s) => sceneStatus(s, orientation, "video") !== "COMPLETED",
    );
    if (!targetScenes.length) {
      if (!readyScenes.length) {
        throw new Error("Chưa có cảnh nào có ảnh sẵn sàng để tạo video refs.");
      }
      setBatchMsg("Tất cả cảnh đã có ảnh đều đã có video.");
      return;
    }
    const skippedNoImage = scenes.length - readyScenes.length;
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({
        requests: targetScenes.map((s) => ({
          type: "GENERATE_VIDEO_REFS",
          project_id: projectId,
          video_id: videoId,
          scene_id: s.id,
          orientation,
        })),
      }),
    });
    setBatchMsg(
      `✓ Đã gửi tạo video refs cho ${targetScenes.length} cảnh đã có ảnh${
        skippedNoImage > 0 ? ` (bỏ qua ${skippedNoImage} cảnh thiếu ảnh)` : ""
      }.`,
    );
  };

  const upscale = async () => {
    const scenes = await fetchAPI<Scene[]>(
      `/api/scenes?video_id=${videoId}`,
    );
    if (!scenes.length) throw new Error("Chưa có phân cảnh nào.");
    const readyScenes = scenes.filter(hasReadyVideoForOrientation);
    const targetScenes = readyScenes.filter(
      (s) => sceneStatus(s, orientation, "upscale") !== "COMPLETED",
    );
    if (!targetScenes.length) {
      if (!readyScenes.length) {
        throw new Error("Chưa có cảnh nào có video để upscale 4K.");
      }
      setBatchMsg("Tất cả cảnh đã có video đều đã upscale xong.");
      return;
    }
    const skippedNoVideo = scenes.length - readyScenes.length;
    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({
        requests: targetScenes.map((s) => ({
          type: "UPSCALE_VIDEO_LOCAL",
          project_id: projectId,
          video_id: videoId,
          scene_id: s.id,
          orientation,
        })),
      }),
    });
    setBatchMsg(
      `✓ Đã gửi nâng 4K local cho ${targetScenes.length} cảnh đã có video${
        skippedNoVideo > 0 ? ` (bỏ qua ${skippedNoVideo} cảnh chưa có video)` : ""
      }.`,
    );
  };

  const runStageAction = async (
    stage: "images" | "videos" | "video_refs" | "upscale",
  ) => {
    if (stage === "images") return genImages();
    if (stage === "videos") return genVideos();
    if (stage === "video_refs") return genVideoRefs();
    return upscale();
  };

  const downloadAllAssets = async () => {
    setBatchMsg("");
    setDownloadingAssets(true);
    try {
      const res = await fetchAPI<{
        download_dir: string;
        images_downloaded: number;
        videos_downloaded: number;
        failed?: string[];
      }>(`/api/videos/${videoId}/download-assets`, {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          orientation,
          rebind_scene_urls: true,
        }),
      });
      setDownloadAssetsDir(res.download_dir || "");
      const failedCount = res.failed?.length ?? 0;
      setBatchMsg(
        `✓ Đã tải local ${res.images_downloaded} ảnh, ${res.videos_downloaded} video${
          failedCount > 0 ? ` · lỗi ${failedCount}` : ""
        }.`,
      );
    } catch (e: any) {
      const raw = String(e?.message ?? "unknown");
      if (raw.includes('API 404: {"detail":"Not Found"}')) {
        setBatchMsg(
          "Lỗi tải ảnh/video local: backend agent đang chạy bản cũ (thiếu endpoint download-assets). Khởi động lại app/agent rồi thử lại.",
        );
      } else {
        setBatchMsg(`Lỗi tải ảnh/video local: ${raw}`);
      }
    } finally {
      setDownloadingAssets(false);
    }
  };

  const openDownloadFolder = async () => {
    if (!downloadAssetsDir) return;
    if (window.electron?.openPath) {
      const result = await window.electron.openPath(downloadAssetsDir);
      if (!result.ok && result.error) setBatchMsg(`Không mở được thư mục: ${result.error}`);
      return;
    }
    setBatchMsg(`Thư mục local: ${downloadAssetsDir}`);
  };

  const buildPreflightChecks = async (
    stage: "images" | "videos" | "video_refs" | "upscale",
  ): Promise<PreflightCheckItem[]> => {
    const [health, scenes, chars, localUpscale] = await Promise.all([
      fetchAPI<{ extension_connected: boolean }>("/health"),
      fetchAPI<Scene[]>(`/api/scenes?video_id=${videoId}`),
      fetchAPI<{ id: string; media_id: string | null }[]>(
        `/api/projects/${projectId}/characters`,
      ),
      stage === "upscale"
        ? fetchAPI<{ ready: boolean; error?: string }>("/api/workflows/local-upscale/health")
        : Promise.resolve(null),
    ]);

    const hasScenes = scenes.length > 0;
    const missingRefs = chars.filter((c) => !c.media_id).length;
    const imageReadyScenes = scenes.filter(hasReadyImageForOrientation).length;
    const missingImages = scenes.length - imageReadyScenes;
    const videoReadyScenes = scenes.filter(hasReadyVideoForOrientation).length;
    const missingVideos = scenes.length - videoReadyScenes;
    const extensionStrict = stage !== "upscale";

    const checks: PreflightCheckItem[] = [
      {
        id: "extension",
        label: "Extension connection",
        status: health.extension_connected
          ? "pass"
          : extensionStrict
            ? "fail"
            : "warn",
        description: health.extension_connected
          ? "Extension đã kết nối."
          : extensionStrict
            ? "Extension đang mất kết nối."
            : "Extension đang mất kết nối (upscale local vẫn có thể chạy nếu video đã lưu local).",
        hint: health.extension_connected
          ? "Sẵn sàng gọi Flow API."
          : extensionStrict
            ? "Mở tab Google Flow và bấm reconnect."
            : "Nếu thiếu video local, hệ thống mới cần extension để lấy lại nguồn.",
        blocking: extensionStrict,
      },
      {
        id: "scenes",
        label: "Scene availability",
        status: hasScenes ? "pass" : "fail",
        description: hasScenes
          ? `Có ${scenes.length} cảnh trong video.`
          : "Video chưa có cảnh nào.",
        hint: hasScenes ? undefined : "Thêm scene trước khi chạy batch.",
        blocking: true,
      },
    ];

    if (stage === "images") {
      checks.push({
        id: "refs",
        label: "Reference images",
        status: missingRefs === 0 ? "pass" : "fail",
        description:
          missingRefs === 0
            ? "Tất cả thực thể đã có media_id."
            : `Còn ${missingRefs} thực thể thiếu media_id.`,
        hint:
          missingRefs === 0
            ? undefined
            : "Sinh ảnh ref trước khi tạo scene images.",
        blocking: true,
        quickFixLabel: "Gen refs thiếu",
        quickFix: async () => {
          await queueMissingRefs();
        },
      });
    }

    if (stage === "videos" || stage === "video_refs" || stage === "upscale") {
      checks.push({
        id: "scene-images",
        label: "Scene images readiness",
        status:
          imageReadyScenes === 0
            ? "fail"
            : missingImages === 0
              ? "pass"
              : "warn",
        description:
          missingImages === 0
            ? "Tất cả cảnh đã có ảnh."
            : imageReadyScenes > 0
              ? `${imageReadyScenes} cảnh đã có ảnh, ${missingImages} cảnh còn thiếu ảnh.`
              : "Chưa có cảnh nào có ảnh.",
        hint:
          missingImages === 0
            ? undefined
            : imageReadyScenes > 0
              ? "Có thể gen video cho các cảnh đã có ảnh ngay bây giờ."
              : "Gen ảnh trước khi gen video/upscale.",
        blocking: imageReadyScenes === 0,
        quickFixLabel: "Gen ảnh thiếu",
        quickFix: async () => {
          await queueMissingImages();
        },
      });
    }

    if (stage === "upscale") {
      checks.push({
        id: "upscale-tools",
        label: "Local 4K dependencies",
        status: localUpscale?.ready ? "pass" : "fail",
        description: localUpscale?.ready
          ? "Đã sẵn sàng ffmpeg + Real-ESRGAN cho nâng 4K local."
          : "Thiếu dependency upscale local.",
        hint: localUpscale?.ready
          ? undefined
          : localUpscale?.error || "Cài ffmpeg/ffprobe + realesrgan-ncnn-vulkan và model trước khi chạy.",
        blocking: !localUpscale?.ready,
      });
      checks.push({
        id: "scene-videos",
        label: "Scene videos readiness",
        status:
          videoReadyScenes === 0
            ? "fail"
            : missingVideos === 0
              ? "pass"
              : "warn",
        description:
          videoReadyScenes === 0
            ? "Chưa có cảnh nào có video."
            : missingVideos === 0
              ? "Tất cả cảnh đã có video."
              : `${videoReadyScenes} cảnh đã có video, ${missingVideos} cảnh chưa có video.`,
        hint:
          videoReadyScenes === 0
            ? "Gen video trước khi upscale."
            : "Upscale sẽ chạy ngay cho các cảnh đã có video.",
        blocking: videoReadyScenes === 0,
        quickFixLabel: "Gen video thiếu",
        quickFix: async () => {
          await queueMissingVideos();
        },
      });
    }

    return checks;
  };

  const openPreflight = async (
    stage: "images" | "videos" | "video_refs" | "upscale",
  ) => {
    setBatchMsg("");
    setPendingStage(stage);
    try {
      const checks = await buildPreflightChecks(stage);
      setPreflightChecks(checks);
      setShowPreflight(true);
    } catch (e: any) {
      setBatchMsg(`Lỗi preflight: ${e?.message ?? "unknown"}`);
    }
  };

  const rerunPreflight = async () => {
    if (!pendingStage) return;
    const checks = await buildPreflightChecks(pendingStage);
    setPreflightChecks(checks);
  };

  const continueAfterPreflight = async () => {
    if (!pendingStage) return;
    await runStageAction(pendingStage);
    setShowPreflight(false);
  };

  const regenFailedImages = async () => {
    setRetryingFailedImages(true);
    setBatchMsg("");
    try {
      const { imageIds } = await loadSceneFailures();
      if (imageIds.length === 0) {
        setBatchMsg("Không có cảnh ảnh lỗi để tạo lại.");
        return;
      }
      await fetchAPI("/api/requests/batch", {
        method: "POST",
        body: JSON.stringify({
          requests: imageIds.map((sceneId) => ({
            type: "REGENERATE_IMAGE",
            project_id: projectId,
            video_id: videoId,
            scene_id: sceneId,
            orientation,
          })),
        }),
      });
      setBatchMsg(`✓ Đã gửi tạo lại ảnh cho ${imageIds.length} cảnh lỗi.`);
      setFailedImageCount(0);
    } catch (e: any) {
      setBatchMsg(`Lỗi tạo lại ảnh lỗi: ${e?.message ?? "unknown"}`);
    } finally {
      setRetryingFailedImages(false);
    }
  };

  const regenFailedVideos = async () => {
    setRetryingFailedVideos(true);
    setBatchMsg("");
    try {
      const { videoIds } = await loadSceneFailures();
      if (videoIds.length === 0) {
        setBatchMsg("Không có cảnh video lỗi để tạo lại.");
        return;
      }
      await fetchAPI("/api/requests/batch", {
        method: "POST",
        body: JSON.stringify({
          requests: videoIds.map((sceneId) => ({
            type: "REGENERATE_VIDEO",
            project_id: projectId,
            video_id: videoId,
            scene_id: sceneId,
            orientation,
          })),
        }),
      });
      setBatchMsg(`✓ Đã gửi tạo lại video cho ${videoIds.length} cảnh lỗi.`);
      setFailedVideoCount(0);
    } catch (e: any) {
      setBatchMsg(`Lỗi tạo lại video lỗi: ${e?.message ?? "unknown"}`);
    } finally {
      setRetryingFailedVideos(false);
    }
  };

  return (
    <>
      <div className="flex-shrink-0 rounded-lg p-3 flex flex-col gap-2.5 border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
          Pipeline sản xuất
        </div>

        {/* ── Generate ── */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Generate
          </span>
          <div className="flex flex-wrap gap-1.5">
            <Button variant="secondary" size="sm" onClick={genRefs}>
              <Users size={11} /> Gen Ref ảnh
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void openPreflight("images");
              }}
            >
              <Image size={11} /> Gen Hình cảnh
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void openPreflight("videos");
              }}
            >
              <Film size={11} /> Gen Video clip
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void openPreflight("video_refs");
              }}
            >
              <Film size={11} /> Gen Video Refs
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowChain(true)}
            >
              <Link2 size={11} /> Kết nối cảnh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void openPreflight("upscale");
              }}
            >
              <Zap size={11} /> Nâng 4K local
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={regenFailedImages}
              disabled={retryingFailedImages || failedImageCount === 0}
              className={
                failedImageCount > 0
                  ? "border-red-300 text-red-600 hover:bg-red-50"
                  : ""
              }
            >
              <RefreshCw
                size={11}
                className={retryingFailedImages ? "animate-spin" : ""}
              />
              {retryingFailedImages
                ? "Đang tạo lại ảnh lỗi..."
                : `Tạo lại ảnh lỗi (${failedImageCount})`}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={regenFailedVideos}
              disabled={retryingFailedVideos || failedVideoCount === 0}
              className={
                failedVideoCount > 0
                  ? "border-red-300 text-red-600 hover:bg-red-50"
                  : ""
              }
            >
              <RefreshCw
                size={11}
                className={retryingFailedVideos ? "animate-spin" : ""}
              />
              {retryingFailedVideos
                ? "Đang tạo lại video lỗi..."
                : `Tạo lại video lỗi (${failedVideoCount})`}
            </Button>
          </div>
          {batchMsg && (
            <div
              className={cn(
                "text-[11px] rounded-md px-2 py-1 border",
                batchMsg.startsWith("✓")
                  ? "text-green-700 bg-green-50 border-green-200"
                  : "text-red-700 bg-red-50 border-red-200",
              )}
            >
              {batchMsg}
            </div>
          )}
        </div>

        <Separator />

        {/* ── Audio & Export ── */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Audio & Xuất file
          </span>
          <div className="flex flex-wrap gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowReview(true)}
            >
              <Star size={11} /> Đánh giá clip
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowReviewBoard(true)}
            >
              <Boxes size={11} /> Review Board
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowNarrator(true)}
            >
              <FileText size={11} /> Script lời (AI)
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowTTS(true)}>
              <Mic size={11} /> Giọng đọc (TTS)
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowMusic(true)}
            >
              <Music size={11} /> Nhạc nền
            </Button>
            <Button size="sm" onClick={() => setShowExport(true)}>
              <Download size={11} /> Xuất video
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={downloadAllAssets}
              disabled={downloadingAssets}
            >
              <Download
                size={11}
                className={downloadingAssets ? "animate-pulse" : ""}
              />{" "}
              {downloadingAssets ? "Đang tải local..." : "Tải ảnh/video local"}
            </Button>
            {downloadAssetsDir && (
              <Button variant="ghost" size="sm" onClick={openDownloadFolder}>
                <FolderOpen size={11} /> Mở thư mục tải
              </Button>
            )}
          </div>
          <div className="text-[11px] text-[hsl(var(--muted-foreground))] leading-relaxed">
            Script lời (AI) → Giọng đọc (TTS) → Xuất video (bật fit narrator) để
            tự khớp thời gian.
          </div>
        </div>

        <Separator />

        {/* ── Post-edit ── */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Hậu kỳ & Xuất bản
          </span>
          <div className="flex flex-wrap gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowUploadImage(true)}
            >
              <Upload size={11} /> Upload ảnh
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowTextOverlays(true)}
            >
              <FileText size={11} /> Chèn chữ
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowBrandLogo(true)}
            >
              <ImageIcon size={11} /> Brand Logo
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowThumbnail(true)}
            >
              <ImageIcon size={11} /> Thumbnail
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowYTSEO(true)}
            >
              <Tv2 size={11} /> YouTube SEO
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowYTUpload(true)}
            >
              <Sparkles size={11} /> Đăng YouTube
            </Button>
          </div>
        </div>

        <Separator />

        {/* ── AI Tools + Utilities ── */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Công cụ AI & Tiện ích
          </span>
          <div className="flex flex-wrap gap-1.5">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowPipeline(true)}
            >
              <Bot size={11} /> Smart Pipeline
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowCreativeMix(true)}
            >
              <Sparkles size={11} /> Creative Mix
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowCameraGuide(true)}
            >
              <BookOpen size={11} /> Hướng dẫn quay
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowThumbnailGuide(true)}
            >
              <BookOpen size={11} /> Hướng dẫn thumbnail
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFixUUIDs(true)}
            >
              <Wrench size={11} /> Fix UUIDs
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRefreshURLs(true)}
            >
              <RefreshCw size={11} /> Làm mới URL
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <BatchStatusBar
            videoId={videoId}
            type="GENERATE_CHARACTER_IMAGE"
            label="Ảnh TN"
            lastEventType={lastEventType}
            orientation={orientation}
          />
          <BatchStatusBar
            videoId={videoId}
            type="GENERATE_IMAGE"
            label="Hình cảnh"
            lastEventType={lastEventType}
            orientation={orientation}
          />
          <BatchStatusBar
            videoId={videoId}
            type="GENERATE_VIDEO"
            label="Video"
            lastEventType={lastEventType}
            orientation={orientation}
          />
          <BatchStatusBar
            videoId={videoId}
            type="GENERATE_VIDEO_REFS"
            label="Video Refs"
            lastEventType={lastEventType}
            orientation={orientation}
          />
          <BatchStatusBar
            videoId={videoId}
            type="UPSCALE_VIDEO_LOCAL"
            label="Nâng 4K local"
            lastEventType={lastEventType}
            orientation={orientation}
          />
        </div>
      </div>

      {showReview && (
        <ReviewVideoModal
          videoId={videoId}
          projectId={projectId}
          onClose={() => setShowReview(false)}
        />
      )}
      {showTTS && (
        <TTSSetupModal
          videoId={videoId}
          projectId={projectId}
          orientation={orientation}
          onClose={() => setShowTTS(false)}
        />
      )}
      {showExport && (
        <ExportModal
          videoId={videoId}
          projectId={projectId}
          defaultOrientation={orientation}
          onClose={() => setShowExport(false)}
        />
      )}
      {showMusic && (
        <MusicModal
          videoId={videoId}
          projectId={projectId}
          onClose={() => setShowMusic(false)}
        />
      )}
      {showNarrator && (
        <GenNarratorModal
          videoId={videoId}
          projectId={projectId}
          onClose={() => setShowNarrator(false)}
        />
      )}
      {showChain && (
        <ChainVideosModal
          videoId={videoId}
          projectId={projectId}
          orientation={orientation}
          onClose={() => setShowChain(false)}
        />
      )}
      {showThumbnail && (
        <ThumbnailModal
          projectId={projectId}
          projectName={video.title}
          onClose={() => setShowThumbnail(false)}
        />
      )}
      {showYTSEO && (
        <YouTubeSEOModal
          projectId={projectId}
          videoId={videoId}
          onClose={() => setShowYTSEO(false)}
        />
      )}
      {showYTUpload && (
        <YouTubeUploadModal
          projectId={projectId}
          videoId={videoId}
          onClose={() => setShowYTUpload(false)}
        />
      )}
      {showFixUUIDs && (
        <FixUUIDsModal
          projectId={projectId}
          videoId={videoId}
          orientation={orientation}
          onClose={() => setShowFixUUIDs(false)}
        />
      )}
      {showRefreshURLs && (
        <RefreshURLsModal
          projectId={projectId}
          videoId={videoId}
          onClose={() => setShowRefreshURLs(false)}
        />
      )}
      {showUploadImage && (
        <UploadImageModal
          projectId={projectId}
          videoId={videoId}
          orientation={orientation}
          onClose={() => setShowUploadImage(false)}
        />
      )}
      {showTextOverlays && (
        <TextOverlaysModal
          videoId={videoId}
          onClose={() => setShowTextOverlays(false)}
        />
      )}
      {showBrandLogo && (
        <BrandLogoModal
          projectId={projectId}
          videoId={videoId}
          onClose={() => setShowBrandLogo(false)}
        />
      )}
      {showReviewBoard && (
        <ReviewBoardModal
          projectId={projectId}
          videoId={videoId}
          orientation={orientation}
          onClose={() => setShowReviewBoard(false)}
        />
      )}
      {showCreativeMix && (
        <CreativeMixModal
          projectId={projectId}
          videoId={videoId}
          orientation={orientation}
          onClose={() => setShowCreativeMix(false)}
        />
      )}
      {showPipeline && (
        <PipelineOrchestratorModal
          projectId={projectId}
          videoId={videoId}
          orientation={orientation}
          onClose={() => setShowPipeline(false)}
        />
      )}
      {showCameraGuide && (
        <GuideModal guide="camera" onClose={() => setShowCameraGuide(false)} />
      )}
      {showThumbnailGuide && (
        <GuideModal
          guide="thumbnail"
          onClose={() => setShowThumbnailGuide(false)}
        />
      )}
      {showPreflight && (
        <PreflightModal
          title="Preflight trước khi chạy batch"
          subtitle="Kiểm tra điều kiện bắt buộc trước khi gửi request hàng loạt."
          checks={preflightChecks}
          onClose={() => setShowPreflight(false)}
          onRecheck={rerunPreflight}
          onContinue={continueAfterPreflight}
          continueLabel="Chạy bước này"
        />
      )}
    </>
  );
}

// ─── Main ─────────────────────────────────────────────────────
export default function VideoDetailPage({ video, projectId, onBack }: Props) {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [showAddScene, setShowAddScene] = useState(false);
  const [showSceneReview, setShowSceneReview] = useState(false);
  const [orientation, setOrientation] = useState<string>(
    normalizeOrientation(video.orientation),
  );
  const [videoTitle, setVideoTitle] = useState(video.title);
  const [scriptImportOpen, setScriptImportOpen] = useState(false);
  const [scriptImporting, setScriptImporting] = useState(false);
  const [scriptImportError, setScriptImportError] = useState("");
  const [scriptImportInfo, setScriptImportInfo] = useState("");
  const [scriptPayload, setScriptPayload] = useState<ScriptImportPayload | null>(
    null,
  );
  const [scriptFileName, setScriptFileName] = useState("");
  const scriptFileInputRef = useRef<HTMLInputElement | null>(null);
  const { lastEvent } = useWebSocket();
  const { connected: extensionConnected, check: recheckExtension } =
    useExtensionStatus();
  const [reconnecting, setReconnecting] = useState(false);
  const [resolvedImageUrls, setResolvedImageUrls] = useState<
    Record<string, string>
  >({});
  const [resolvedVideoUrls, setResolvedVideoUrls] = useState<
    Record<string, string>
  >({});
  const detailPaneRef = useRef<HTMLDivElement | null>(null);
  const [sceneListMaxHeight, setSceneListMaxHeight] = useState<number | null>(
    null,
  );
  const refreshingSceneImageIdsRef = useRef<Set<string>>(new Set());
  const refreshingSceneVideoIdsRef = useRef<Set<string>>(new Set());
  const refreshFailedAtRef = useRef<Map<string, number>>(new Map());
  const IMAGE_URL_RETRY_DELAY_MS = 45_000;
  const reconnectKickAtRef = useRef(0);
  const refreshKey = (sceneId: string, stage: "image" | "video") =>
    `${sceneId}:${stage}`;

  const ensureExtensionConnectedForMedia = useCallback(async () => {
    if (extensionConnected) {
      const fresh = await recheckExtension();
      if (fresh) return true;
    }
    const now = Date.now();
    if (now - reconnectKickAtRef.current > 2500) {
      reconnectKickAtRef.current = now;
      await window.electron?.openFlowTab?.({ focus: false, reveal: false });
      await window.electron?.reconnectExtension?.();
    }
    await new Promise((r) => setTimeout(r, 900));
    return Boolean(await recheckExtension());
  }, [extensionConnected, recheckExtension]);

  const load = useCallback(async () => {
    const [s, c] = await Promise.all([
      fetchAPI<Scene[]>(`/api/scenes?video_id=${video.id}`),
      fetchAPI<Character[]>(`/api/projects/${projectId}/characters`),
    ]);
    setScenes(s);
    setCharacters(c);
    setSelectedScene((prev) =>
      prev ? (s.find((x) => x.id === prev.id) ?? null) : (s[0] ?? null),
    );
  }, [video.id, projectId]);

  const refreshSceneImageUrl = useCallback(
    async (scene: Scene) => {
      const key = refreshKey(scene.id, "image");
      if (refreshingSceneImageIdsRef.current.has(scene.id)) return null;
      const source = resolveSceneImageSource(scene, orientation);
      if (!source?.mediaId) return null;
      const failedAt = refreshFailedAtRef.current.get(key);
      if (failedAt && Date.now() - failedAt < IMAGE_URL_RETRY_DELAY_MS)
        return null;

      if (!(await ensureExtensionConnectedForMedia())) return null;

      refreshingSceneImageIdsRef.current.add(scene.id);
      try {
        const fetchFresh = async () =>
          fetchAPI<any>(
            `/api/flow/media/${source.mediaId}?project_id=${encodeURIComponent(projectId)}`,
          );
        let data: any;
        try {
          data = await fetchFresh();
        } catch (error: any) {
          const message = String(error?.message ?? "");
          const authRelated =
            message.includes("401") ||
            message.toUpperCase().includes("UNAUTHENTICATED") ||
            message.includes("AUTH_EXPIRED");
          if (!authRelated) throw error;

          await window.electron?.openFlowTab?.({ focus: false, reveal: false });
          await window.electron?.reconnectExtension?.();
          await new Promise((r) => setTimeout(r, 1200));
          await recheckExtension();
          data = await fetchFresh();
        }
        const fresh = pickDirectMediaUrl(data);
        if (!fresh) return null;
        refreshFailedAtRef.current.delete(key);
        setResolvedImageUrls((prev) =>
          prev[scene.id] === fresh ? prev : { ...prev, [scene.id]: fresh },
        );
        const shouldPersistLocal = /\/api\/flow\/local-media\?path=/.test(fresh);
        if (shouldPersistLocal) {
          const current = (scene as any)[`${source.prefix}_image_url`] as
            | string
            | null;
          if (current !== fresh) {
            await patchAPI(`/api/scenes/${scene.id}`, {
              [`${source.prefix}_image_url`]: fresh,
            });
          }
        }
        return fresh as string;
      } catch {
        refreshFailedAtRef.current.set(key, Date.now());
        return null;
      } finally {
        refreshingSceneImageIdsRef.current.delete(scene.id);
      }
    },
    [ensureExtensionConnectedForMedia, orientation, projectId],
  );

  const refreshSceneVideoUrl = useCallback(
    async (scene: Scene) => {
      const key = refreshKey(scene.id, "video");
      if (refreshingSceneVideoIdsRef.current.has(scene.id)) return null;
      const source = resolveSceneVideoSource(scene, orientation);
      if (!source?.mediaId) return null;
      const failedAt = refreshFailedAtRef.current.get(key);
      if (failedAt && Date.now() - failedAt < IMAGE_URL_RETRY_DELAY_MS)
        return null;

      if (!(await ensureExtensionConnectedForMedia())) return null;

      refreshingSceneVideoIdsRef.current.add(scene.id);
      try {
        const fetchFresh = async () =>
          fetchAPI<any>(
            `/api/flow/media/${source.mediaId}?project_id=${encodeURIComponent(projectId)}`,
          );
        let data: any;
        try {
          data = await fetchFresh();
        } catch (error: any) {
          const message = String(error?.message ?? "");
          const authRelated =
            message.includes("401") ||
            message.toUpperCase().includes("UNAUTHENTICATED") ||
            message.includes("AUTH_EXPIRED");
          if (!authRelated) throw error;

          await window.electron?.openFlowTab?.({ focus: false, reveal: false });
          await window.electron?.reconnectExtension?.();
          await new Promise((r) => setTimeout(r, 1200));
          await recheckExtension();
          data = await fetchFresh();
        }
        const fresh = pickDirectMediaUrl(data);
        if (!fresh) return null;
        refreshFailedAtRef.current.delete(key);
        setResolvedVideoUrls((prev) =>
          prev[scene.id] === fresh ? prev : { ...prev, [scene.id]: fresh },
        );
        const shouldPersistLocal = /\/api\/flow\/local-media\?path=/.test(fresh);
        if (shouldPersistLocal) {
          const field =
            source.stage === "upscale"
              ? `${source.prefix}_upscale_url`
              : `${source.prefix}_video_url`;
          const current = (scene as any)[field] as string | null;
          if (current !== fresh) {
            await patchAPI(`/api/scenes/${scene.id}`, {
              [field]: fresh,
            });
          }
        }
        return fresh as string;
      } catch {
        refreshFailedAtRef.current.set(key, Date.now());
        return null;
      } finally {
        refreshingSceneVideoIdsRef.current.delete(scene.id);
      }
    },
    [ensureExtensionConnectedForMedia, orientation, projectId, recheckExtension],
  );

  // NOTE: disable automatic startup URL-refresh/read-media sweep.
  // Keep media refresh user-driven (manual refresh / selected-scene preview onError)
  // to avoid request storms when opening large projects.

  useEffect(() => {
    load();
    fetchAPI<{ orientation?: string }>(`/api/videos/${video.id}`)
      .then((v) => {
        if (v.orientation) {
          setOrientation(normalizeOrientation(v.orientation));
          return;
        }
        return fetchAPI<{ orientation?: string }>(
          `/api/projects/${projectId}`,
        ).then((p) => setOrientation(normalizeOrientation(p.orientation)));
      })
      .catch(() => {});
  }, [load, projectId, video.id]);

  useEffect(() => {
    refreshFailedAtRef.current.clear();
    setResolvedImageUrls({});
    setResolvedVideoUrls({});
  }, [video.id, projectId]);

  useEffect(() => {
    setVideoTitle(video.title);
  }, [video.id, video.title]);

  useEffect(() => {
    if (!lastEvent) return;
    const relevant = [
      "scene_created",
      "scene_updated",
      "scene_deleted",
      "character_created",
      "character_updated",
      "character_deleted",
      "request_update",
      "request_completed",
      "request_failed",
      "video_updated",
      "urls_refreshed",
    ];
    if (relevant.includes(lastEvent.type)) load();
  }, [lastEvent, load]);

  useEffect(() => {
    const node = detailPaneRef.current;
    if (!node) {
      setSceneListMaxHeight(null);
      return;
    }

    const updateHeight = () => {
      const next = Math.round(node.getBoundingClientRect().height);
      setSceneListMaxHeight(next > 0 ? next : null);
    };

    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(node);
    window.addEventListener("resize", updateHeight);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateHeight);
    };
  }, [selectedScene?.id, scenes.length, orientation]);

  const lastEventType = lastEvent?.type ?? null;
  const hasGaps =
    scenes.length > 0 && scenes.some((s, i) => s.display_order !== i);

  const fixOrder = async () => {
    await fetchAPI(`/api/videos/${video.id}/recompact`, { method: "POST" });
    load();
  };

  const saveVideoTitle = async (next: string) => {
    const trimmed = next.trim();
    if (!trimmed) return;
    setVideoTitle(trimmed);
    await patchAPI(`/api/videos/${video.id}`, { title: trimmed });
  };

  const exportScript = async () => {
    setScriptImportError("");
    setScriptImportInfo("");
    try {
      const payload = await fetchAPI<any>(`/api/videos/${video.id}/script-export`);
      const text = JSON.stringify(payload, null, 2);
      const blob = new Blob([text], { type: "application/json" });
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      link.href = href;
      link.download = `${slugForFile(videoTitle)}_script_${stamp}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(href);
      setScriptImportInfo("✓ Đã export kịch bản JSON.");
    } catch (e: any) {
      const raw = String(e?.message ?? "unknown");
      if (raw.includes('API 404: {"detail":"Not Found"}')) {
        setScriptImportError(
          "Lỗi export kịch bản: backend agent đang chạy bản cũ (thiếu route script-export). Khởi động lại app/agent rồi thử lại.",
        );
      } else {
        setScriptImportError(`Lỗi export kịch bản: ${raw}`);
      }
    }
  };

  const openImportScriptPicker = () => {
    setScriptImportError("");
    setScriptImportInfo("");
    setScriptPayload(null);
    setScriptFileName("");
    scriptFileInputRef.current?.click();
  };

  const onImportScriptFilePicked = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const rawText = await file.text();
      const parsed = JSON.parse(rawText);
      if (!Array.isArray(parsed?.scenes) || parsed.scenes.length === 0) {
        throw new Error("File kịch bản phải có mảng scenes và không được rỗng.");
      }
      const payload: ScriptImportPayload = {
        format_version:
          typeof parsed?.format_version === "number"
            ? parsed.format_version
            : undefined,
        title:
          typeof parsed?.title === "string" ? parsed.title : parsed?.video?.title,
        description:
          typeof parsed?.description === "string"
            ? parsed.description
            : parsed?.video?.description,
        orientation:
          typeof parsed?.orientation === "string"
            ? parsed.orientation
            : parsed?.video?.orientation,
        video:
          parsed?.video && typeof parsed.video === "object"
            ? {
                title:
                  typeof parsed.video.title === "string"
                    ? parsed.video.title
                    : null,
                description:
                  typeof parsed.video.description === "string"
                    ? parsed.video.description
                    : null,
                orientation:
                  typeof parsed.video.orientation === "string"
                    ? parsed.video.orientation
                    : null,
              }
            : undefined,
        scenes: parsed.scenes as ScriptScenePayload[],
      };
      setScriptPayload(payload);
      setScriptFileName(file.name);
      setScriptImportOpen(true);
    } catch (e: any) {
      setScriptImportError(
        `Không đọc được file kịch bản: ${e?.message ?? "JSON không hợp lệ."}`,
      );
    }
  };

  const runImportScript = async () => {
    if (!scriptPayload) return;
    setScriptImporting(true);
    setScriptImportError("");
    try {
      const result = await fetchAPI<ScriptImportResponse>(
        `/api/videos/${video.id}/script-import`,
        {
          method: "POST",
          body: JSON.stringify({
            ...scriptPayload,
            replace_existing: true,
            clear_requests: true,
          }),
        },
      );
      setScriptImportOpen(false);
      setScriptPayload(null);
      setVideoTitle(result.title);
      setOrientation(normalizeOrientation(result.orientation));
      setResolvedImageUrls({});
      setResolvedVideoUrls({});
      setSelectedScene(null);
      await load();
      setScriptImportInfo(
        `✓ Đã import ${result.scenes_total} cảnh, reset media an toàn và sẵn sàng generate.`,
      );
    } catch (e: any) {
      const raw = String(e?.message ?? "unknown");
      if (raw.includes('API 404: {"detail":"Not Found"}')) {
        setScriptImportError(
          "Lỗi import kịch bản: backend agent đang chạy bản cũ (thiếu route script-import). Khởi động lại app/agent rồi thử lại.",
        );
      } else {
        setScriptImportError(`Lỗi import kịch bản: ${raw}`);
      }
    } finally {
      setScriptImporting(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-3 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button variant="ghost" size="sm" onClick={onBack}>
          ← Quay lại
        </Button>
        <EditableText
          value={videoTitle}
          onSave={saveVideoTitle}
          className="font-semibold text-sm"
        />
        <Badge variant="outline">{orientationAspect(orientation)}</Badge>
        <span
          className={cn(
            "text-xs",
            hasGaps ? "text-amber-500" : "text-[hsl(var(--muted-foreground))]",
          )}
        >
          {scenes.length} cảnh{hasGaps ? " ⚠ thiếu cảnh" : ""}
        </span>
        <Button variant="outline" size="sm" onClick={exportScript}>
          <Download size={12} /> Export kịch bản
        </Button>
        <Button variant="outline" size="sm" onClick={openImportScriptPicker}>
          <Upload size={12} /> Import kịch bản
        </Button>
        <div className="flex-1" />
        {/* Extension status — click to reconnect when disconnected */}
        {extensionConnected ? (
          <span className="flex items-center gap-1.5 text-[11px] font-medium px-2 py-1 rounded-md border text-green-700 border-green-200 bg-green-50">
            <Wifi size={10} /> Extension
          </span>
        ) : (
          <button
            className={cn(
              "flex items-center gap-1.5 text-[11px] font-medium px-2 py-1 rounded-md border transition-colors",
              reconnecting
                ? "text-amber-600 border-amber-200 bg-amber-50 cursor-not-allowed"
                : "text-red-600 border-red-300 bg-red-50 hover:bg-red-100 cursor-pointer",
            )}
            title="Click để mở Flow và wake extension"
            disabled={reconnecting}
            onClick={async () => {
              setReconnecting(true);
              try {
                await window.electron?.openFlowTab?.({ focus: true, reveal: true });
                await window.electron?.reconnectExtension?.();

                let connected = false;
                for (let attempt = 0; attempt < 6; attempt += 1) {
                  await new Promise((r) => setTimeout(r, 1200));
                  connected = await recheckExtension();
                  if (connected) break;
                  if (attempt === 2) {
                    // Retry hard reconnect once more mid-way.
                    await window.electron?.reconnectExtension?.();
                  }
                }
              } finally {
                setReconnecting(false);
              }
            }}
          >
            {reconnecting ? (
              <>
                <RefreshCw size={10} className="animate-spin" /> Đang kết nối
                lại...
              </>
            ) : (
              <>
                <WifiOff size={10} /> Extension mất kết nối — Nhấn để fix
              </>
            )}
          </button>
        )}
        {hasGaps && (
          <Button
            variant="outline"
            size="sm"
            onClick={fixOrder}
            className="border-amber-300 text-amber-600 hover:bg-amber-50"
          >
            ⚡ Sửa thứ tự
          </Button>
        )}
        <Button size="sm" onClick={() => setShowAddScene(true)}>
          <Plus size={12} /> Thêm cảnh
        </Button>
      </div>

      {/* Gap warning */}
      {hasGaps && (
        <div className="text-xs rounded-md px-3 py-2 flex items-center gap-2 flex-shrink-0 bg-amber-50 border border-amber-200 text-amber-700">
          ⚠ Một số cảnh không tạo được (display_order bị thiếu). Nhấn{" "}
          <strong>⚡ Sửa thứ tự</strong> để đánh số lại, sau đó thêm cảnh bị
          thiếu thủ công.
        </div>
      )}
      {scriptImportInfo && (
        <div className="text-xs rounded-md px-3 py-2 flex-shrink-0 bg-green-50 border border-green-200 text-green-700">
          {scriptImportInfo}
        </div>
      )}
      {scriptImportError && (
        <div className="text-xs rounded-md px-3 py-2 flex-shrink-0 bg-red-50 border border-red-200 text-red-700">
          {scriptImportError}
        </div>
      )}

      {/* Pipeline */}
      <PipelineBar
        projectId={projectId}
        videoId={video.id}
        video={video}
        orientation={orientation}
        lastEventType={lastEventType}
      />

      {/* Split view */}
      <div className="flex gap-3 items-start">
        {/* Scene list */}
        <div
          className="flex flex-col gap-1.5 overflow-y-auto flex-shrink-0 pr-1"
          style={{
            width: 232,
            maxHeight:
              sceneListMaxHeight && sceneListMaxHeight > 0
                ? sceneListMaxHeight
                : undefined,
          }}
        >
          {scenes.length === 0 && (
            <div className="text-xs py-6 text-[hsl(var(--muted-foreground))]">
              Chưa có phân cảnh nào.
              <br />
              Nhấn "Thêm cảnh" để bắt đầu.
            </div>
          )}
          {scenes.map((s) => (
            <SceneListItem
              key={s.id}
              scene={s}
              selected={selectedScene?.id === s.id}
              orientation={orientation}
              imageOverride={resolvedImageUrls[s.id] ?? null}
              onClick={() => setSelectedScene(s)}
            />
          ))}
        </div>

        {/* Editor */}
        <div
          ref={detailPaneRef}
          className="flex-1 min-w-0 rounded-lg p-4 border border-[hsl(var(--border))] bg-[hsl(var(--card))]"
        >
          {selectedScene ? (
            <SceneEditor
              scene={selectedScene}
              characters={characters}
              projectId={projectId}
              videoId={video.id}
              orientation={orientation}
              imageOverride={resolvedImageUrls[selectedScene.id] ?? null}
              videoOverride={resolvedVideoUrls[selectedScene.id] ?? null}
              onImageError={() => {
                void refreshSceneImageUrl(selectedScene);
              }}
              onVideoError={() => {
                void refreshSceneVideoUrl(selectedScene);
              }}
              onSaved={load}
              onDeleted={() => {
                setSelectedScene(null);
                load();
              }}
              onReviewScene={() => setShowSceneReview(true)}
            />
          ) : (
            <div className="py-8 text-xs text-[hsl(var(--muted-foreground))]">
              Chọn phân cảnh để chỉnh sửa
            </div>
          )}
        </div>
      </div>

      <input
        ref={scriptFileInputRef}
        type="file"
        accept=".json,application/json"
        className="hidden"
        onChange={onImportScriptFilePicked}
      />

      {scriptImportOpen && scriptPayload && (
        <Dialog
          open={scriptImportOpen}
          onOpenChange={(next) => {
            if (!scriptImporting) setScriptImportOpen(next);
          }}
        >
          <DialogContent className="max-w-3xl">
            <div className="flex flex-col gap-3 p-4">
              <div className="text-base font-semibold">Import kịch bản</div>
              <div className="text-xs text-[hsl(var(--muted-foreground))]">
                File: <strong>{scriptFileName || "(không rõ tên)"}</strong>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div className="rounded-md border p-2">
                  <div className="text-[10px] uppercase text-[hsl(var(--muted-foreground))]">
                    Tổng cảnh
                  </div>
                  <div className="text-sm font-semibold">
                    {scriptPayload.scenes.length}
                  </div>
                </div>
                <div className="rounded-md border p-2">
                  <div className="text-[10px] uppercase text-[hsl(var(--muted-foreground))]">
                    Tiêu đề video
                  </div>
                  <div className="text-sm font-semibold truncate">
                    {scriptPayload.title ||
                      scriptPayload.video?.title ||
                      videoTitle}
                  </div>
                </div>
                <div className="rounded-md border p-2">
                  <div className="text-[10px] uppercase text-[hsl(var(--muted-foreground))]">
                    Tỉ lệ
                  </div>
                  <div className="text-sm font-semibold">
                    {normalizeOrientation(
                      scriptPayload.orientation ||
                        scriptPayload.video?.orientation ||
                        orientation,
                    ) === "VERTICAL"
                      ? "9:16"
                      : "16:9"}
                  </div>
                </div>
              </div>
              <div className="rounded-md border border-amber-200 bg-amber-50 text-amber-800 text-xs p-2.5">
                Import sẽ ghi đè toàn bộ scene hiện tại của episode này, reset
                media/status về trạng thái sẵn sàng generate, và xoá request cũ
                để tránh xung đột queue.
              </div>
              <div className="max-h-56 overflow-y-auto rounded-md border p-2">
                <div className="text-[10px] uppercase mb-1 text-[hsl(var(--muted-foreground))]">
                  Xem trước cảnh (5 dòng đầu)
                </div>
                <div className="flex flex-col gap-1.5">
                  {scriptPayload.scenes.slice(0, 5).map((sc, idx) => (
                    <div
                      key={`${idx}-${sc.display_order ?? idx}`}
                      className="text-xs rounded border px-2 py-1.5"
                    >
                      <div className="font-semibold">
                        Cảnh #{typeof sc.display_order === "number" ? sc.display_order + 1 : idx + 1}
                      </div>
                      <div className="text-[hsl(var(--muted-foreground))] truncate">
                        {sc.prompt ||
                          sc.image_prompt ||
                          sc.video_prompt ||
                          sc.narrator_text ||
                          "(trống)"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={scriptImporting}
                  onClick={() => setScriptImportOpen(false)}
                >
                  Huỷ
                </Button>
                <Button
                  size="sm"
                  disabled={scriptImporting}
                  onClick={runImportScript}
                >
                  {scriptImporting ? "Đang import..." : "Xác nhận import"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {showSceneReview && selectedScene && (
        <ReviewSceneModal
          projectId={projectId}
          videoId={video.id}
          sceneId={selectedScene.id}
          orientation={orientation}
          onClose={() => setShowSceneReview(false)}
          onRegenerated={load}
          onPatched={load}
        />
      )}

      {showAddScene && (
        <AddSceneModal
          videoId={video.id}
          scenes={scenes}
          characters={characters}
          defaultAfterOrder={
            selectedScene?.display_order ?? Math.max(0, scenes.length - 1)
          }
          onClose={() => setShowAddScene(false)}
          onCreated={() => {
            setShowAddScene(false);
            load();
          }}
        />
      )}
    </div>
  );
}
