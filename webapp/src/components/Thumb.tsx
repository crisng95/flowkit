import { useEffect, useState } from "react";

interface Props {
  src?: string | null;
  alt: string;
  className?: string;
  rounded?: string;
  /** `false` = thấy TRỌN ảnh, thừa chỗ thì để trống hai bên (object-contain).
   *  Ảnh tham chiếu nhân vật/đạo cụ nay là khung DỌC, mà ô thumbnail là khung ngang,
   *  nên cắt-đầy mặc định xén mất đầu lẫn chân và chỉ chừa khúc giữa người. */
  crop?: boolean;
}

// Image with graceful fallback: while loading or on error, show a soft
// gradient placeholder with the first letter — so the grid never looks broken.
export default function Thumb({ src, alt, className = "", rounded = "rounded-xl", crop = true }: Props) {
  const [failed, setFailed] = useState(false);
  // When src changes (e.g. an image was just generated/downloaded), clear any prior
  // error state so the new image actually loads without needing a tab-switch/remount.
  useEffect(() => setFailed(false), [src]);
  const show = src && !failed;
  return (
    <div
      className={`relative overflow-hidden bg-neutral-800 ${rounded} ${className}`}
    >
      {show ? (
        <img
          key={src!}
          src={src!}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className={`h-full w-full ${crop ? "object-cover" : "object-contain"}`}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-neutral-700/60 to-neutral-900">
          <span className="text-3xl font-semibold text-neutral-400">
            {alt?.trim()?.[0]?.toUpperCase() ?? "·"}
          </span>
        </div>
      )}
    </div>
  );
}
