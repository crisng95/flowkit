import { useEffect, useState } from "react";
import { api, type Health } from "../api/client";

function Pill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-neutral-800/80 px-2.5 py-1 text-xs"
      title={label}
    >
      <span
        className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-500"}`}
      />
      {label}
    </span>
  );
}

// Tier quyết định trần độ phân giải (ONE → 2K ảnh/1080p video, TWO → 4K) nên phải đọc được
// từ xa: xanh dương = tier 1, vàng = tier 2.
const TIER_STYLE: Record<string, { label: string; cls: string }> = {
  PAYGATE_TIER_ONE: { label: "Tier 1", cls: "bg-blue-500/15 text-blue-300 ring-blue-500/30" },
  PAYGATE_TIER_TWO: { label: "Tier 2", cls: "bg-amber-500/15 text-amber-300 ring-amber-500/30" },
};

function tierPill(tier: string) {
  return (
    TIER_STYLE[tier] ?? {
      label: tier.replace("PAYGATE_TIER_", "Tier "),
      cls: "bg-neutral-800 text-neutral-300 ring-neutral-700",
    }
  );
}

export default function StatusPills() {
  const [health, setHealth] = useState<Health | null>(null);
  const [credits, setCredits] = useState<number | null>(null);
  const [tier, setTier] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const h = await api.health();
        if (alive) setHealth(h);
        if (h.extension_connected) {
          try {
            const c = await api.credits();
            if (alive) {
              setCredits(c.credits ?? null);
              setTier(c.userPaygateTier ?? null);
            }
          } catch {
            /* ignore */
          }
        }
      } catch {
        if (alive) setHealth(null);
      }
    };
    tick();
    const t = setInterval(tick, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  // Dự án và media gắn chặt với tài khoản Flow đang đăng nhập trong Chrome, nên phải luôn
  // nhìn thấy mình đang là ai — đăng nhập nhầm account là thấy thiếu dự án / gen hỏng.
  const account = health?.account ?? null;

  return (
    <div className="flex items-center gap-2">
      {health && (
        <span
          className={`inline-flex max-w-[16rem] items-center gap-1.5 truncate rounded-full px-2.5 py-1 text-xs ${
            account
              ? "bg-neutral-800 text-neutral-300"
              : "bg-amber-500/15 text-amber-300"
          }`}
          title={
            account
              ? `Tài khoản Flow: ${account.email ?? account.id}. Chỉ dự án của tài khoản này hiện ở đây.`
              : "Chưa xác định được tài khoản Flow — đang hiện TẤT CẢ dự án. Mở labs.google/fx/tools/flow và đăng nhập, rồi tải lại extension."
          }
        >
          {account?.picture && (
            <img src={account.picture} alt="" className="h-4 w-4 rounded-full" />
          )}
          <span className="truncate">{account?.email ?? "Chưa rõ tài khoản"}</span>
        </span>
      )}
      {tier && (
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${tierPill(tier).cls}`}
          title={`Paygate tier (từ Flow credits): ${tier}`}
        >
          {tierPill(tier).label}
        </span>
      )}
      {credits != null && (
        <span className="rounded-full bg-indigo-500/15 px-2.5 py-1 text-xs font-medium text-indigo-300">
          {credits.toLocaleString()} credits
        </span>
      )}
      <Pill ok={!!health?.extension_connected} label="Flow" />
      <Pill ok={!!health?.tts} label="TTS" />
      <Pill ok={!!health?.ffmpeg} label="ffmpeg" />
    </div>
  );
}
