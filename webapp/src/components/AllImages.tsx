import { useEffect, useState } from "react";
import { api, thumbUrl, type FlowMedia, type Project } from "../api/client";
import Thumb from "./Thumb";
import Lightbox from "./common/Lightbox";

// Gallery of every image in the currently-open project (its Flow project), with name search.
export default function AllImages({ project }: { project: Project }) {
  const [items, setItems] = useState<FlowMedia[] | null>(null);
  const [q, setQ] = useState("");
  const [lightbox, setLightbox] = useState<FlowMedia | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const sync = async () => {
    if (
      !window.confirm(
        "Đồng bộ với Flow: media nào đã bị xoá trên Flow sẽ bị gỡ khỏi entity / shot / lịch sử và xoá file local. Tiếp tục?"
      )
    )
      return;
    setSyncing(true);
    setSyncMsg(null);
    setErr(null);
    try {
      const r = await api.syncProjectMedia(project.id);
      const rm = r.removed;
      setSyncMsg(
        r.total_removed === 0
          ? `Đã đồng bộ — mọi media còn trên Flow (${r.flow_media}). Không có gì để xoá.`
          : `Đã gỡ ${r.total_removed} media đã xoá trên Flow: ` +
              `${rm.entities.length} ảnh asset, ${rm.shot_images.length} ảnh shot, ` +
              `${rm.shot_videos.length} video shot, ${rm.extra_views} view phụ, ${rm.history} lịch sử.`
      );
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSyncing(false);
    }
  };

  const load = () => {
    setItems(null);
    setErr(null);
    if (!project.flow_project_id) {
      setErr("Dự án chưa gắn với project trên Flow.");
      setItems([]);
      return;
    }
    api
      .flowProjectMedia(project.flow_project_id)
      .then((r) => setItems(r.media.filter((m) => m.kind !== "video")))
      .catch((e) => setErr(e.message));
  };
  useEffect(load, [project.flow_project_id]);

  const filtered = (items || []).filter((m) =>
    !q.trim() ? true : (m.name || "").toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="h-full overflow-auto">
      <div className="px-6 py-8 2xl:px-10">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Tất cả ảnh</h1>
            <p className="text-sm text-neutral-400">
              {items === null
                ? "Đang quét ảnh của dự án…"
                : `${filtered.length}/${items.length} ảnh · ${project.title}`}
            </p>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Tìm theo tên ảnh…"
              className="w-64 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm outline-none focus:border-indigo-500"
            />
            <button
              onClick={sync}
              disabled={syncing || !project.flow_project_id}
              title="Đồng bộ với Flow — gỡ media đã bị xoá trên Flow khỏi local"
              className="rounded-lg border border-amber-700/60 px-3 py-1.5 text-sm text-amber-300 hover:bg-amber-950/40 disabled:opacity-40"
            >
              {syncing ? "Đang đồng bộ…" : "⇄ Đồng bộ Flow"}
            </button>
            <button
              onClick={load}
              title="Tải lại"
              className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800"
            >
              ↻
            </button>
          </div>
        </div>

        {syncMsg && (
          <div className="mb-4 rounded-lg border border-amber-800/60 bg-amber-950/30 px-3 py-2 text-sm text-amber-200">
            {syncMsg}
          </div>
        )}
        {err && (
          <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
            {err}
          </div>
        )}
        {items === null && (
          <div className="py-16 text-center text-sm text-neutral-500">Đang tải ảnh của dự án…</div>
        )}
        {items !== null && !filtered.length && !err && (
          <div className="rounded-2xl border border-dashed border-neutral-800 py-16 text-center text-neutral-500">
            Không có ảnh nào khớp.
          </div>
        )}

        <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(200px,1fr))]">
          {filtered.map((m) => (
            <button
              key={m.media_id}
              onClick={() => setLightbox(m)}
              className="group overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900/50 text-left transition hover:border-indigo-500"
            >
              <Thumb src={thumbUrl(m.media_id, project.id)} alt={m.name} rounded="rounded-none" className="aspect-square w-full" />
              <div className="p-2">
                <div className="truncate text-xs font-medium">{m.name || "—"}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {lightbox && (
        <Lightbox
          imageSrc={thumbUrl(lightbox.media_id, project.id)}
          title={lightbox.name}
          onClose={() => setLightbox(null)}
        />
      )}
    </div>
  );
}
