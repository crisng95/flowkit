import { useEffect, useMemo, useState } from "react";
import { storyboard, type Shot } from "../../api/client";

// Thêm HÀNG LOẠT shot vào một scene từ văn bản nhiều dòng — mỗi dòng một prompt.
//
// Dùng chung cho hai tab, khác nhau đúng một chỗ: prompt đi vào cột nào.
//   Storyboard → `description`   (prompt dựng ẢNH khung hình)
//   Shots      → `motion_prompt` (prompt dựng VIDEO)
// Việc tách dòng nằm ở SERVER (`split_bulk_prompts`) để hai tab không bao giờ tách khác
// nhau; phần đếm dòng dưới đây chỉ để xem trước, và cố ý áp cùng luật ấy.

const LIST_MARK = /^\s*(?:[-*•–—]|\(?\d{1,3}[.)]|\d{1,3}\s*[-–])\s+/;

/** Xem trước danh sách prompt — phải khớp `split_bulk_prompts` phía server. */
export function previewPrompts(text: string): string[] {
  return text
    .split(/\r\n|\r|\n/)
    .map((l) => l.replace(LIST_MARK, "").trim())
    .filter(Boolean);
}

export default function BulkAddShots({
  sceneId,
  sceneTitle,
  field,
  onDone,
  onClose,
}: {
  sceneId: string;
  sceneTitle?: string;
  /** "description" = prompt ảnh (Storyboard) · "motion_prompt" = prompt video (Shots) */
  field: "description" | "motion_prompt";
  onDone: (r: { added: number; shots: Shot[] }) => void;
  onClose: () => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const lines = useMemo(() => previewPrompts(text), [text]);
  const isVideo = field === "motion_prompt";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  const submit = async () => {
    if (!lines.length) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await storyboard.addShotsBulk(sceneId, text, field);
      onDone(r);
      onClose();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[95] flex items-center justify-center bg-black/60 p-6"
      onClick={() => !busy && onClose()}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-neutral-800 px-5 py-3">
          <h3 className="min-w-0 truncate font-semibold">
            ＋ Thêm hàng loạt shot{sceneTitle ? ` — ${sceneTitle}` : ""}
          </h3>
          <button
            onClick={() => !busy && onClose()}
            className="ml-auto shrink-0 text-neutral-500 hover:text-neutral-300"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-auto p-5">
          <p className="text-sm text-neutral-400">
            Dán vào đây, <b>mỗi dòng một prompt</b> — mỗi dòng thành một shot, nối vào cuối
            scene. Prompt vào ô{" "}
            <b className={isVideo ? "text-amber-300" : "text-indigo-300"}>
              {isVideo ? "chuyển động (video)" : "mô tả khung hình (ảnh)"}
            </b>
            . Dòng trống bị bỏ qua, đầu dòng kiểu danh sách (<code>1.</code>, <code>-</code>,{" "}
            <code>•</code>) được cắt.
          </p>

          {err && (
            <div className="rounded-lg bg-rose-950/40 px-3 py-2 text-sm text-rose-300">{err}</div>
          )}

          <textarea
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
            rows={12}
            placeholder={
              isVideo
                ? "Máy lia chậm từ trái sang phải qua dãy đèn lồng\nCô gái ngẩng đầu nhìn trời, tóc bay nhẹ\nXe máy chạy ngang khung hình, đèn pha quét qua ống kính"
                : "Cận cảnh bàn tay pha trà, hơi nước bốc lên\nToàn cảnh phố cổ mưa đêm, đèn lồng đỏ hắt xuống mặt đường ướt\nTrung cảnh cô gái đứng dưới mái hiên, nhìn ra ngoài mưa"
            }
            className="w-full resize-y rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 font-mono text-sm leading-relaxed text-neutral-200 placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
          />

          {lines.length > 0 && (
            <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
              <div className="mb-1.5 text-xs text-neutral-500">
                Sẽ tạo <b className="text-neutral-300">{lines.length}</b> shot:
              </div>
              <ol className="max-h-40 space-y-0.5 overflow-auto text-xs text-neutral-400">
                {lines.slice(0, 30).map((l, i) => (
                  <li key={i} className="truncate">
                    <span className="mr-1.5 tabular-nums text-neutral-600">{i + 1}.</span>
                    {l}
                  </li>
                ))}
                {lines.length > 30 && (
                  <li className="text-neutral-600">… và {lines.length - 30} dòng nữa</li>
                )}
              </ol>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 border-t border-neutral-800 px-5 py-3">
          <span className="text-xs text-neutral-600">
            Chỉ tạo shot rỗng kèm prompt — chưa sinh ảnh/video nên không tốn credit.
          </span>
          <button
            onClick={submit}
            disabled={busy || !lines.length}
            className="ml-auto shrink-0 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            {busy ? "Đang thêm…" : `Thêm ${lines.length || ""} shot`}
          </button>
        </div>
      </div>
    </div>
  );
}
