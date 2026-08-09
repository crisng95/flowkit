import type { ReactNode } from "react";

// Mảnh giao diện dùng chung cho tab Thiết lập, để nhóm dự án và nhóm ứng dụng trông như một.
export const inp =
  "w-full rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500";

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <label className="mb-1 block text-xs font-medium text-neutral-400">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs leading-relaxed text-neutral-600">{hint}</p>}
    </div>
  );
}

/** Một khối thiết lập có tiêu đề — đơn vị nhóm nhỏ bên trong một mục của sub-nav. */
export function Group({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-4">
      <h3 className="text-sm font-semibold text-neutral-200">{title}</h3>
      {hint && <p className="mt-0.5 text-xs leading-relaxed text-neutral-500">{hint}</p>}
      <div className="mt-3 space-y-4">{children}</div>
    </section>
  );
}

/** Slider có nhãn + số ở cuối — kiểu điều khiển lặp lại nhiều nhất trong phần TTS/nhạc. */
export function Slider({
  label,
  value,
  onChange,
  min,
  max,
  step = 0.05,
  format = (v: number) => `${v.toFixed(2)}s`,
  hint,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  format?: (v: number) => string;
  hint?: ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-3">
        <span className="w-32 shrink-0 text-xs text-neutral-400">{label}</span>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 accent-indigo-500"
        />
        <span className="w-12 shrink-0 text-right text-xs tabular-nums text-neutral-400">
          {format(value)}
        </span>
      </div>
      {/* thụt bằng đúng bề rộng nhãn (w-32) + gap-3 để chú thích thẳng hàng với thanh trượt */}
      {hint && <p className="ml-[8.75rem] mt-1 text-xs leading-relaxed text-neutral-600">{hint}</p>}
    </div>
  );
}
