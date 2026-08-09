import { api } from "../api/client";
import type { ConfirmOptions } from "../components/common/Confirm";

// Rough per-item credit cost (Flow doesn't expose exact pricing up front).
// CHỈ VIDEO tốn credit — ≈20/clip (đọc từ response generate-video). Tạo ảnh, sửa ảnh, tách
// nền, upscale ảnh đều KHÔNG trừ credit, nên các batch ảnh không cần hỏi trước.
export const CREDIT_COST = { video: 20 } as const;

type ConfirmFn = (o: ConfirmOptions) => Promise<boolean>;

/**
 * Pre-batch credit check (video-app.md §2.10). Estimates `count × perItem` credits and,
 * if it exceeds the current balance, asks the user to confirm before spending. Returns
 * true if the batch should proceed. Never blocks when credits can't be read.
 */
export async function creditGuard(
  confirm: ConfirmFn,
  count: number,
  perItem: number,
  label: string,
): Promise<boolean> {
  let credits: number | null = null;
  try {
    credits = (await api.credits())?.credits ?? null;
  } catch {
    return true; // can't read balance → don't block
  }
  const need = count * perItem;
  if (credits == null || need <= credits) return true;
  return confirm({
    title: "Có thể không đủ credit",
    message:
      `${label}: ~${count} mục × ${perItem} ≈ ${need} credit, nhưng chỉ còn ${credits}. ` +
      "Vẫn tiếp tục? Batch sẽ dừng lại khi hết credit.",
    confirmText: "Vẫn chạy",
    danger: true,
  });
}
