import { useEffect, useLayoutEffect, useRef, useState } from "react";

export type DownloadChoice = {
  key: string;
  label: string;        // "Nguyên bản (HD)" | "1080p" | "4K"
  hint?: string;        // "chưa có — render ~1 phút, 0 credit"
  disabled?: boolean;
  onSelect: () => void | Promise<void>;
};

/**
 * Nút ⬇ có nhiều mốc để chọn (nguyên bản / 1080p / 4K).
 *
 * Menu dùng `position: fixed` + toạ độ đo từ nút, KHÔNG phải absolute: thẻ media bọc ngoài
 * có `overflow-hidden` nên menu absolute bị cắt cụt ngay dưới nút. Hàng nút của thẻ lại chỉ
 * hiện khi hover, nên `onOpenChange` để thẻ ghim nó lại trong lúc menu đang mở — không thì
 * rê chuột xuống chọn là cả cụm biến mất.
 */
export default function DownloadMenu({
  choices,
  title = "Tải về máy",
  onOpenChange,
  round,
}: {
  choices: DownloadChoice[];
  title?: string;
  onOpenChange?: (open: boolean) => void;
  round?: boolean;   // kiểu nút to, tròn của Lightbox
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const toggle = (v: boolean) => {
    setOpen(v);
    onOpenChange?.(v);
  };

  useLayoutEffect(() => {
    if (!open) return;
    const r = btnRef.current?.getBoundingClientRect();
    if (r) setPos({ top: r.bottom + 6, right: Math.max(8, window.innerWidth - r.right) });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    // Bấm ra ngoài thì đóng — nhưng phải CHỪA nút và chính menu ra. Listener chạy ở pha
    // capture (thẻ media nuốt sự kiện nên pha bubble không tới nơi), tức nó chạy TRƯỚC
    // handler của item; đóng vô điều kiện là menu unmount ngay ở mousedown và cú click chọn
    // mốc không bao giờ tới được item.
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node | null;
      if (t && (btnRef.current?.contains(t) || menuRef.current?.contains(t))) return;
      toggle(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && toggle(false);
    const onScroll = () => toggle(false);   // menu định vị fixed → cuộn là lệch khỏi nút
    window.addEventListener("mousedown", onDown, true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      window.removeEventListener("mousedown", onDown, true);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  const pick = async (c: DownloadChoice) => {
    toggle(false);
    setBusy(true);
    try {
      await c.onSelect();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        ref={btnRef}
        onClick={(e) => {
          e.stopPropagation();
          toggle(!open);
        }}
        onMouseDown={(e) => e.stopPropagation()}
        disabled={busy}
        title={title}
        className={
          round
            ? "grid h-9 w-9 place-items-center rounded-full bg-neutral-800 text-neutral-200 hover:bg-emerald-600 disabled:opacity-50"
            : "grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-emerald-600 disabled:opacity-50"
        }
      >
        {busy ? <span className="animate-pulse text-xs">…</span> : "⬇"}
      </button>
      {open && pos && (
        <div
          ref={menuRef}
          style={{ top: pos.top, right: pos.right }}
          className="fixed z-[90] w-60 overflow-hidden rounded-lg border border-neutral-700 bg-neutral-900 py-1 text-left shadow-2xl"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {choices.map((c) => (
            <button
              key={c.key}
              disabled={c.disabled}
              onClick={(e) => {
                e.stopPropagation();
                pick(c);
              }}
              className="block w-full px-3 py-1.5 text-left hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <span className="text-sm text-neutral-200">{c.label}</span>
              {c.hint && <span className="mt-0.5 block text-xs text-neutral-500">{c.hint}</span>}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
