import type { ReactNode } from "react";
import Thumb from "../Thumb";
import { downloadFile } from "../../lib/download";

interface Props {
  imageSrc?: string | null;
  videoSrc?: string | null;
  title: string;
  index?: number;
  subtitle?: string | null;
  busy?: boolean;
  busyLabel?: string;
  selected?: boolean;
  actions?: ReactNode;
  // Saves the card's media to disk. `downloadUrl` may point at a DIFFERENT file than the one
  // previewed (a shot card previews the HD clip but downloads the 1080p/4K upscale).
  downloadUrl?: string | null;
  downloadName?: string;
  downloadTitle?: string;
  onClick?: () => void;
  onPreview?: () => void;
  onEdit?: () => void;
}

// Shared image/video card: media on top, title + description below, hover actions.
export default function MediaCard({
  imageSrc,
  videoSrc,
  title,
  index,
  subtitle,
  busy,
  busyLabel = "Đang tạo…",
  selected,
  actions,
  downloadUrl,
  downloadName,
  downloadTitle,
  onClick,
  onPreview,
  onEdit,
}: Props) {
  return (
    <div
      className={`group overflow-hidden rounded-xl border bg-neutral-900/50 transition ${
        selected ? "border-indigo-500 ring-1 ring-indigo-500" : "border-neutral-800 hover:border-neutral-600"
      }`}
    >
      <div className="relative cursor-pointer" onClick={onClick}>
        {videoSrc ? (
          <video
            key={videoSrc}
            src={videoSrc}
            className="aspect-video w-full bg-black object-cover"
            muted
            playsInline
            preload="metadata"
            onMouseEnter={(e) => (e.currentTarget as HTMLVideoElement).play().catch(() => {})}
            onMouseLeave={(e) => {
              const v = e.currentTarget as HTMLVideoElement;
              v.pause();
              v.currentTime = 0;
            }}
          />
        ) : (
          <Thumb src={imageSrc} alt={title} rounded="rounded-none" className="aspect-video w-full" />
        )}

        {busy && (
          <div className="absolute inset-0 grid place-items-center bg-black/60 text-sm text-neutral-200">
            <span className="animate-pulse">{busyLabel}</span>
          </div>
        )}

        <div className="absolute right-1.5 top-1.5 flex gap-1 opacity-0 transition group-hover:opacity-100">
          {onPreview && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPreview();
              }}
              title="Phóng to"
              className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-neutral-700"
            >
              ⤢
            </button>
          )}
          {onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              title="Edit (node editor)"
              className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-neutral-700"
            >
              ✎
            </button>
          )}
          {downloadUrl && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                downloadFile(downloadUrl, downloadName || downloadUrl.split("/").pop() || "media");
              }}
              title={downloadTitle || "Tải về máy"}
              className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-emerald-600"
            >
              ⬇
            </button>
          )}
          {actions}
        </div>
      </div>
      <div className="p-2" onClick={onClick}>
        <div className="flex items-center gap-1.5">
          {index != null && (
            <span className="text-xs text-neutral-500">{String(index + 1).padStart(2, "0")}</span>
          )}
          <span className="truncate text-sm font-medium">{title}</span>
        </div>
        {subtitle && <p className="mt-0.5 line-clamp-2 text-xs text-neutral-500">{subtitle}</p>}
      </div>
    </div>
  );
}
