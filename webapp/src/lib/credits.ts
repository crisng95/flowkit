import { api } from "../api/client";
import type { ConfirmOptions } from "../components/common/Confirm";

// Rough per-item credit cost (Flow doesn't expose exact pricing up front).
// Mọi thao tác trên ẢNH đều 0 credit — tạo, sửa, tách/thay nền, kể cả upscale lên 2K/4K —
// nên batch ảnh không bao giờ phải hỏi trước. Chỉ hai thứ tính tiền:
//   video          ≈20/clip  (đọc từ response generate-video)
//   upscaleVideo4k ≈50/video (đắt hơn cả một lượt render mới; bản 1080p thì 0)
export const CREDIT_COST = { video: 20, upscaleVideo4k: 50, upscaleVideo1080p: 0 } as const;

// Veo 3.1 Lite [Lower Priority] render MIỄN PHÍ (chỉ tài khoản Ultra), nên dự án đặt engine
// đó thì batch video không cần hỏi credit nữa. Cảnh báo thừa làm người dùng mất phản xạ đọc
// nó khi lượt render THẬT SỰ tốn tiền.
// Chú ý: chỉ bản có [Lower Priority] mới 0đ — "Veo 3.1 - Lite" thường vẫn trừ credit.
export function videoCost(videoModel?: string | null, paygateTier?: string | null): number {
  const raw = String(videoModel ?? "").trim();
  if (raw.startsWith("veo_lite") || raw.endsWith("_lite_low_priority")) return 0;
  // Ô rỗng = "tự động": Ultra (tier TWO) rơi vào Veo Lite, xem graph.video_engine.
  if (!raw && paygateTier === "PAYGATE_TIER_TWO") return 0;
  return CREDIT_COST.video;
}

/** Giá một lượt upscale video theo độ phân giải đích (`VIDEO_RESOLUTION_4K` | `..._1080P`). */
export function upscaleVideoCost(resolution?: string | null): number {
  return String(resolution ?? "").includes("4K") ? CREDIT_COST.upscaleVideo4k : 0;
}

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
