import { downloadFile, slugName } from "../../lib/download";

interface Props {
  imageSrc?: string | null;
  videoSrc?: string | null;
  title?: string;
  // Save the media being viewed. Defaults to the previewed file itself; pass these to save a
  // different one (e.g. the 1080p upscale behind an HD preview) or to name the file.
  downloadUrl?: string | null;
  downloadName?: string;
  onClose: () => void;
}

export default function Lightbox({
  imageSrc,
  videoSrc,
  title,
  downloadUrl,
  downloadName,
  onClose,
}: Props) {
  const src = downloadUrl || videoSrc || imageSrc;
  const name =
    downloadName ||
    `${slugName(title || "media")}.${(src || "").toLowerCase().endsWith(".mp4") ? "mp4" : "png"}`;
  return (
    <div
      className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-black/85 p-6"
      onClick={onClose}
    >
      <div className="max-h-[85vh] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
        {videoSrc ? (
          <video src={videoSrc} controls autoPlay className="max-h-[85vh] max-w-[90vw] rounded-lg" />
        ) : (
          <img src={imageSrc ?? ""} alt={title} className="max-h-[85vh] max-w-[90vw] rounded-lg" />
        )}
        {title && <div className="mt-2 text-center text-sm text-neutral-300">{title}</div>}
      </div>
      <div className="absolute right-5 top-5 flex gap-2" onClick={(e) => e.stopPropagation()}>
        {src && (
          <button
            onClick={() => downloadFile(src, name)}
            title={`Tải về → ${name}`}
            className="grid h-9 w-9 place-items-center rounded-full bg-neutral-800 text-neutral-200 hover:bg-emerald-600"
          >
            ⬇
          </button>
        )}
        <button
          onClick={onClose}
          className="grid h-9 w-9 place-items-center rounded-full bg-neutral-800 text-neutral-200 hover:bg-neutral-700"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
