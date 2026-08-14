import { useEffect, useState } from "react";
import { api, storyboard, shots as shotsApi, type Project, type Scene, type Shot } from "../../api/client";
import type { EditorTarget } from "../nodeeditor/NodeEditor";
import MediaCard from "../common/MediaCard";
import Lightbox from "../common/Lightbox";
import { useConfirm } from "../common/Confirm";
import { creditGuard, videoCost } from "../../lib/credits";
import { downloadFile, slugName, pad3 } from "../../lib/download";
import { useJobs, useJobWatcher } from "../../jobs/JobsContext";

// Which file a shot's ⬇ actually saves, and what to call it. The upscale is a SEPARATE file
// (<media_id>_upsampled.mp4) and is only the right one while it still belongs to the current
// video — re-rendering the shot leaves a stale upscale behind, which `upscale_media_id` catches.
const videoDownload = (sh: Shot, sceneIdx: number) => {
  const upscaled = !!sh.upscale_path && sh.upscale_media_id === sh.video_media_id;
  const url = (upscaled ? sh.upscale_path : sh.video_path) || null;
  if (!url) return null;
  const res = upscaled ? sh.upscale_res?.split("_").pop()?.toLowerCase() : "";
  return {
    url,
    name: `sc${pad3(sceneIdx)}-s${pad3(sh.idx)}-${slugName(sh.title || sh.description || "")}${
      res ? `-${res}` : ""
    }.mp4`,
    title: upscaled ? `Tải video ${res} (bản upscale)` : "Tải video (bản HD)",
  };
};

const parseRefs = (s: string | null): string[] => {
  try {
    return JSON.parse(s || "[]");
  } catch {
    return [];
  }
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export default function ShotsTab({
  project,
  onEdit,
}: {
  project: Project;
  onEdit?: (t: EditorTarget) => void;
}) {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [byScene, setByScene] = useState<Record<string, Shot[]>>({});
  const [sel, setSel] = useState<Shot | null>(null);
  const [running, setRunning] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [lightbox, setLightbox] = useState<Shot | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const confirm = useConfirm();
  const { jobFor } = useJobs();

  const loadShots = async (sid: string) => {
    const r = await storyboard.sceneShots(sid);
    setByScene((m) => ({ ...m, [sid]: r.shots }));
  };

  const reloadAllShots = async () => {
    const sc = scenes.length ? scenes : (await api.listScenes(project.id)).scenes;
    for (const s of sc) await loadShots(s.id);
  };

  useEffect(() => {
    (async () => {
      const sc = (await api.listScenes(project.id)).scenes;
      setScenes(sc);
      for (const s of sc) await loadShots(s.id);
    })().catch((e) => setErr(e.message));
  }, [project.id]);

  // Refetch shots as the server video batch advances (§9) — videos fill in live.
  const videoJob = jobFor("videos");
  useJobWatcher("videos", {
    onAdvance: reloadAllShots,
    onDone: (j) => {
      reloadAllShots();
      if (j.errors.length) setErr(`Auto gen video: ${j.done}/${j.total} xong, ${j.errors.length} lỗi.`);
    },
  });

  const setShot = (u: Shot) => {
    setByScene((m) => ({
      ...m,
      [u.scene_id]: (m[u.scene_id] || []).map((x) => (x.id === u.id ? u : x)),
    }));
    if (sel?.id === u.id) setSel(u);
  };

  const mark = (id: string, on: boolean) =>
    setRunning((s) => {
      const n = new Set(s);
      on ? n.add(id) : n.delete(id);
      return n;
    });

  const genVideo = async (shot: Shot): Promise<boolean> => {
    if (!shot.image_path) {
      setErr("Shot chưa có ảnh frame — tạo ở Storyboard trước");
      return false;
    }
    mark(shot.id, true);
    setErr(null);
    try {
      setShot(await shotsApi.genVideo(shot.id));
      return true;
    } catch (e: any) {
      setErr(e.message);
      return false;
    } finally {
      mark(shot.id, false);
    }
  };

  // Kéo về clip của một lượt render đã submit nhưng hết giờ chờ (operation_json). Chỉ poll
  // lại operation cũ nên không tốn thêm credit — dùng khi "Tạo video"/quick-gen báo Flow vẫn
  // đang render.
  const resumeVideo = async (shot: Shot) => {
    mark(shot.id, true);
    setErr(null);
    try {
      setShot(await shotsApi.resumeVideo(shot.id));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      mark(shot.id, false);
    }
  };

  // Render all shots (have image, no video) as a server-side background job (§9):
  // survives tab close, throttled + verified server-side, streams to the banner.
  const genAll = async () => {
    const all = scenes.flatMap((sc) => byScene[sc.id] || []);
    const todo = all.filter((s) => s.image_media_id && !s.video_path);
    if (!todo.length) {
      setErr("Không có shot nào (có ảnh, chưa có video) để render.");
      return;
    }
    // 0 credit với Veo 3.1 Lite [Lower Priority] → creditGuard tự bỏ qua, không hỏi thừa.
    const per = videoCost(project.video_model, project.paygate_tier);
    if (!(await creditGuard(confirm, todo.length, per, "Render video"))) return;
    setErr(null);
    try {
      await shotsApi.genAllVideos(project.id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="flex h-full">
      <div className="min-w-0 flex-1 overflow-auto px-6 py-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Cinematic Shots</h2>
            <p className="text-sm text-neutral-500">Render video từ ảnh storyboard</p>
          </div>
          <button
            disabled={busy || !!videoJob}
            onClick={genAll}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            {videoJob ? `Đang render ${videoJob.done}/${videoJob.total}…` : "✦ Auto gen video"}
          </button>
        </div>
        {progress && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-indigo-800 bg-indigo-950/40 px-3 py-2 text-sm text-indigo-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
            {progress}
          </div>
        )}
        {err && (
          <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
            {err}
          </div>
        )}
        {scenes.map((sc) => {
          const list = byScene[sc.id] || [];
          return (
            <section key={sc.id} className="mb-8">
              <h3 className="mb-3 text-sm font-medium text-neutral-200">
                <span className="mr-1.5 text-neutral-500">{String(sc.idx + 1).padStart(2, "0")}</span>
                {sc.heading}
              </h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {list.map((sh) => {
                  const dl = videoDownload(sh, sc.idx);
                  return (
                  <MediaCard
                    key={sh.id}
                    imageSrc={sh.image_path}
                    videoSrc={sh.video_path}
                    title={sh.title}
                    index={sh.idx}
                    subtitle={sh.video_path ? "▶ video" : sh.status}
                    downloadUrl={dl?.url}
                    downloadName={dl?.name}
                    downloadTitle={dl?.title}
                    selected={sel?.id === sh.id}
                    busy={running.has(sh.id)}
                    busyLabel="Đang render…"
                    onClick={() => setSel(sh)}
                    onPreview={sh.video_path || sh.image_path ? () => setLightbox(sh) : undefined}
                    onEdit={
                      onEdit
                        ? () =>
                            onEdit({
                              kind: "shot",
                              goal: "video",
                              id: sh.id,
                              title: sh.title,
                              // Video prompt = motion (the action) + visual context for the i2v model.
                              prompt:
                                [sh.motion_prompt, sh.visual_prompt].filter(Boolean).join("\n\n") ||
                                sh.description ||
                                sh.title,
                              refEntityIds: parseRefs(sh.ref_entity_ids),
                              // Other shots in the same scene — pre-seeded as Omni Flash reference
                              // sources so the user can keep character/lighting consistent across
                              // shots without manually adding source nodes.
                              refShotImages: list
                                .filter((x) => x.id !== sh.id && x.image_media_id && x.image_path)
                                .map((x) => ({
                                  media_id: x.image_media_id!,
                                  web: x.image_path!,
                                  label: `S${String(x.idx + 1).padStart(2, "0")} ${(x.title || x.description || "").slice(0, 30)}`.trim(),
                                })),
                              imageMediaId: sh.image_media_id,
                              imageSrc: sh.image_path,
                              videoSrc: sh.video_path,
                            })
                        : undefined
                    }
                    actions={
                      <>
                        {sh.operation_json && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              resumeVideo(sh);
                            }}
                            title="Lấy lại video đang render trên Flow (không tốn credit)"
                            className="grid h-7 w-7 place-items-center rounded-md bg-amber-600/80 text-sm hover:bg-amber-500"
                          >
                            ⟳
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            genVideo(sh);
                          }}
                          title="Render video"
                          className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-indigo-600"
                        >
                          ⚡
                        </button>
                      </>
                    }
                  />
                  );
                })}
                {!list.length && (
                  <div className="col-span-full rounded-xl border border-dashed border-neutral-800 py-6 text-center text-xs text-neutral-600">
                    Chưa có frame — làm Storyboard trước.
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>

      {sel && (
        <ShotPanel
          shot={sel}
          project={project}
          sceneIdx={Math.max(0, scenes.findIndex((s) => s.id === sel.scene_id))}
          running={running.has(sel.id)}
          onClose={() => setSel(null)}
          onChange={setShot}
          onGenVideo={() => genVideo(sel)}
        />
      )}
      {lightbox && (() => {
        const dl = videoDownload(
          lightbox,
          Math.max(0, scenes.findIndex((s) => s.id === lightbox.scene_id))
        );
        return (
          <Lightbox
            imageSrc={lightbox.image_path}
            videoSrc={lightbox.video_path}
            title={lightbox.title}
            downloadUrl={dl?.url}
            downloadName={dl?.name}
            onClose={() => setLightbox(null)}
          />
        );
      })()}
    </div>
  );
}

function ShotPanel({
  shot,
  project,
  sceneIdx,
  running,
  onClose,
  onChange,
  onGenVideo,
}: {
  shot: Shot;
  project: Project;
  sceneIdx: number;
  running: boolean;
  onClose: () => void;
  onChange: (s: Shot) => void;
  onGenVideo: () => void;
}) {
  const [visual, setVisual] = useState(shot.visual_prompt ?? "");
  const [motion, setMotion] = useState(shot.motion_prompt ?? "");
  const [aiBusy, setAiBusy] = useState(false);
  const [upBusy, setUpBusy] = useState(false);
  const [upErr, setUpErr] = useState<string | null>(null);
  // Trần upscale phụ thuộc tier (ONE → 1080p, TWO → 4K) → hỏi server thay vì cứng "4K".
  const [upLabel, setUpLabel] = useState("");

  useEffect(() => {
    setVisual(shot.visual_prompt ?? "");
    setMotion(shot.motion_prompt ?? "");
    setUpErr(null);
  }, [shot.id]);

  useEffect(() => {
    shotsApi.upscaleStatus(project.id).then((r) => setUpLabel(r.label)).catch(() => {});
  }, [project.id]);

  // Video ghép cục bộ từ nhiều clip (chained) không upscale được — Flow chỉ nhận một media.
  const chained = !!shot.video_path && !shot.video_path.startsWith("/media/");
  const upscaled = !!shot.upscale_path && shot.upscale_media_id === shot.video_media_id;

  const save = async () =>
    onChange(await storyboard.updateShot(shot.id, { visual_prompt: visual, motion_prompt: motion }));

  const aiPrompts = async () => {
    setAiBusy(true);
    try {
      onChange(await shotsApi.genPrompts(shot.id));
    } finally {
      setAiBusy(false);
    }
  };

  const upscale = async () => {
    setUpBusy(true);
    setUpErr(null);
    try {
      onChange(await shotsApi.upscale(shot.id, upscaled));
    } catch (e: any) {
      setUpErr(e.message);
    } finally {
      setUpBusy(false);
    }
  };

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-neutral-800 bg-neutral-950/50">
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2.5">
        <span className="truncate text-sm font-medium">{shot.title}</span>
        <button onClick={onClose} className="text-neutral-500 hover:text-neutral-300">✕</button>
      </div>
      <div className="flex-1 space-y-4 overflow-auto p-4">
        <div className="overflow-hidden rounded-lg border border-neutral-800 bg-black">
          {shot.video_path ? (
            <video src={shot.video_path} controls className="aspect-video w-full" />
          ) : shot.image_path ? (
            <img src={shot.image_path} className="aspect-video w-full object-cover" />
          ) : (
            <div className="grid aspect-video w-full place-items-center text-xs text-neutral-600">
              chưa có ảnh
            </div>
          )}
        </div>
        <div className="flex items-center justify-between text-xs text-neutral-400">
          <span>Model: {project.video_model || "Veo i2v"}</span>
          <span>{shot.duration}s</span>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs text-neutral-400">Visual / Motion prompt</label>
            <button
              onClick={aiPrompts}
              disabled={aiBusy}
              className="text-xs text-indigo-400 hover:text-indigo-300 disabled:opacity-40"
            >
              {aiBusy ? "…" : "✨ AI"}
            </button>
          </div>
          <textarea
            value={visual}
            onChange={(e) => setVisual(e.target.value)}
            onBlur={save}
            placeholder="Visual prompt"
            className="mb-2 h-20 w-full resize-none rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500"
          />
          <textarea
            value={motion}
            onChange={(e) => setMotion(e.target.value)}
            onBlur={save}
            placeholder="Motion prompt"
            className="h-20 w-full resize-none rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500"
          />
        </div>
      </div>
      <div className="space-y-2 border-t border-neutral-800 p-3">
        <button
          onClick={onGenVideo}
          disabled={running || !shot.image_path}
          className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
        >
          {running ? "Đang render…" : "Generate Video"}
        </button>
        {shot.video_path && (
          <>
            {(() => {
              const dl = videoDownload(shot, sceneIdx);
              return dl ? (
                <button
                  onClick={() => downloadFile(dl.url, dl.name)}
                  title={`${dl.title} → ${dl.name}`}
                  className="w-full rounded-lg border border-emerald-800/70 py-2 text-sm text-emerald-300 hover:bg-emerald-950/40"
                >
                  ⬇ {dl.title}
                </button>
              ) : null;
            })()}
            <button
              onClick={upscale}
              disabled={upBusy || chained}
              title={
                chained
                  ? "Shot ghép từ nhiều clip — Flow không upscale được video ghép cục bộ"
                  // Đo thực tế: lên 1080p KHÔNG trừ credit; bản 4K chưa kiểm chứng.
                  : `Render lại video ở ${upLabel || "độ phân giải cao"} (~1 phút${
                      upLabel === "4K" ? ", bản 4K có thể tốn credit" : ", không tốn credit"
                    })`
              }
              className="w-full rounded-lg border border-neutral-700 py-2 text-sm hover:bg-neutral-800 disabled:opacity-40"
            >
              {upBusy
                ? "Đang upscale…"
                : chained
                  ? "Không upscale được (chained)"
                  : upscaled
                    ? `↻ Upscale lại ${shot.upscale_res?.split("_").pop()?.toLowerCase() ?? ""}`
                    : `Upscale ${upLabel || "…"}`}
            </button>
            {upErr && <p className="text-xs text-rose-400">{upErr}</p>}
          </>
        )}
      </div>
    </aside>
  );
}
