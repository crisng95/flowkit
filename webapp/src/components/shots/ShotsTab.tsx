import { useEffect, useState } from "react";
import { api, storyboard, shots as shotsApi, type Project, type Scene, type Shot } from "../../api/client";
import type { EditorTarget } from "../nodeeditor/NodeEditor";
import MediaCard from "../common/MediaCard";
import Lightbox from "../common/Lightbox";
import type { DownloadChoice } from "../common/DownloadMenu";
import { useConfirm } from "../common/Confirm";
import BulkAddShots from "../common/BulkAddShots";
import { creditGuard, upscaleVideoCost, videoCost } from "../../lib/credits";
import { downloadFile, slugName, pad3 } from "../../lib/download";
import { useJobs, useJobWatcher } from "../../jobs/JobsContext";

// 'VIDEO_RESOLUTION_1080P' → '1080p' (hậu tố tên file, giống hires.video_res_label bên server).
const resTag = (res?: string | null) => (res || "").split("_").pop()?.toLowerCase() || "";

// Nhãn hiển thị: server trả nhãn viết hoa hết ("1080P"), đọc như tên file lỗi.
const resLabel = (res?: string | null) => (resTag(res) === "4k" ? "4K" : resTag(res));

// Bản upscale là một file RIÊNG (<media_id>_upsampled.mp4) và chỉ còn đúng khi nó thuộc về
// video hiện tại — render lại shot là bản upscale cũ thành rác, `upscale_media_id` bắt được.
const currentUpscale = (sh: Shot) =>
  sh.upscale_path && sh.upscale_media_id === sh.video_media_id ? sh.upscale_path : null;

// Shot chained (beat dài hơn một clip) ghép cục bộ từ nhiều clip → Flow không upscale được;
// `video_path` của nó không trỏ vào /media/. Cùng luật với hires.video_upscalable.
const chainedShot = (sh: Shot) => !!sh.video_path && !sh.video_path.startsWith("/media/");

const videoName = (sh: Shot, sceneIdx: number, res?: string | null) =>
  `sc${pad3(sceneIdx)}-s${pad3(sh.idx)}-${slugName(sh.title || sh.description || "")}${
    res ? `-${resTag(res)}` : ""
  }.mp4`;

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
  const [upscaling, setUpscaling] = useState<Set<string>>(new Set());
  // Các mức upscale tier này cho phép (ONE → 1080p; Ultra → 1080p + 4K). Hỏi server một lần
  // cho cả tab thay vì mỗi thẻ một lượt.
  const [upChoices, setUpChoices] = useState<{ value: string; label: string }[]>([]);
  const [upLabel, setUpLabel] = useState("");
  // Scene đang mở hộp "thêm hàng loạt" (dán nhiều dòng prompt → nhiều shot).
  const [bulk, setBulk] = useState<Scene | null>(null);
  const confirm = useConfirm();
  const { jobFor } = useJobs();

  useEffect(() => {
    shotsApi
      .upscaleStatus(project.id)
      .then((r) => {
        setUpChoices(r.choices || []);
        setUpLabel(r.label);
      })
      .catch(() => {});
  }, [project.id]);

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

  // Render bản upscale ở MỘT mức cụ thể rồi tải luôn. Mỗi shot chỉ giữ được MỘT bản upscale
  // (một cột `upscale_path`), nên xin mức khác là thay bản đang có — nói trước cho người dùng
  // biết. force=true vì server bỏ qua yêu cầu khi bản upscale hiện tại còn đúng video.
  const makeAndDownload = async (sh: Shot, sceneIdx: number, res: string, label: string) => {
    const per = upscaleVideoCost(res);
    const cur = currentUpscale(sh) ? sh.upscale_res : null;
    const notes = [
      per
        ? `Render bản ${label} tốn ~${per} credit (đắt hơn cả một lượt render clip mới).`
        : `Render bản ${label} không tốn credit, mất khoảng 1 phút.`,
      cur && cur !== res
        ? `Bản ${resTag(cur)} đang lưu sẽ bị thay — mỗi shot chỉ giữ một bản upscale.`
        : "",
    ].filter(Boolean);
    if (
      (per || (cur && cur !== res)) &&
      !(await confirm({
        title: `Tải bản ${label}?`,
        message: notes.join(" "),
        confirmText: "Render & tải",
        danger: !!per,
      }))
    )
      return;
    if (per && !(await creditGuard(confirm, 1, per, `Upscale ${label}`))) return;

    setUpscaling((s) => new Set(s).add(sh.id));
    setErr(null);
    try {
      const up = await shotsApi.upscale(sh.id, true, res);
      setShot(up);
      if (up.upscale_path) downloadFile(up.upscale_path, videoName(up, sceneIdx, up.upscale_res));
      else setErr("Flow không trả bản upscale.");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setUpscaling((s) => {
        const n = new Set(s);
        n.delete(sh.id);
        return n;
      });
    }
  };

  // Các mốc cho nút ⬇ của một shot: nguyên bản + từng mức upscale tier cho phép. Mức đã có
  // sẵn thì tải thẳng file; chưa có thì render rồi tải.
  const downloadChoices = (sh: Shot, sceneIdx: number): DownloadChoice[] => {
    if (!sh.video_path) return [];
    const chained = chainedShot(sh);
    const out: DownloadChoice[] = [
      {
        key: "src",
        label: "Nguyên bản (HD)",
        hint: "file Flow phát ra, không phải upscale",
        onSelect: () => downloadFile(sh.video_path!, videoName(sh, sceneIdx)),
      },
    ];
    for (const c of upChoices) {
      const have = currentUpscale(sh) && sh.upscale_res === c.value;
      out.push({
        key: c.value,
        label: resLabel(c.value),
        hint: have
          ? "đã có sẵn"
          : chained
            ? "shot ghép từ nhiều clip — Flow không upscale được"
            : `chưa có — render ~1 phút, ${upscaleVideoCost(c.value) || 0} credit`,
        disabled: !have && chained,
        onSelect: () =>
          have
            ? downloadFile(sh.upscale_path!, videoName(sh, sceneIdx, sh.upscale_res))
            : makeAndDownload(sh, sceneIdx, c.value, resLabel(c.value)),
      });
    }
    return out;
  };

  // Xoá shot. Hỏi lại khi shot đã có video: một clip đã render là ~20 credit, xoá nhầm là
  // mất tiền thật — shot rỗng thì xoá thẳng, đừng bắt bấm hai lần vô ích.
  const delShot = async (sh: Shot) => {
    if (
      sh.video_path &&
      !(await confirm({
        title: "Xoá shot?",
        message: `"${sh.title || `Shot ${sh.idx + 1}`}" đã có video render — xoá là mất luôn clip đó.`,
        confirmText: "Xoá",
        danger: true,
      }))
    )
      return;
    setErr(null);
    try {
      await storyboard.deleteShot(sh.id);
      if (sel?.id === sh.id) setSel(null);
      await loadShots(sh.scene_id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Thêm scene bằng tay — dự án chưa có kịch bản thì chưa có scene nào để treo shot vào.
  const addScene = async (shots = 1) => {
    setErr(null);
    try {
      const sc = await api.addScene(project.id, { shots });
      setScenes((list) => [...list, sc]);
      await loadShots(sc.id);
    } catch (e: any) {
      setErr(e.message);
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
        {!scenes.length && (
          // Chưa có kịch bản = chưa có scene, mà shot nào cũng phải nằm trong một scene.
          <div className="rounded-xl border border-dashed border-neutral-800 py-12 text-center text-sm text-neutral-500">
            <p>Chưa có scene — tạo kịch bản ở tab Script, hoặc tự thêm shot ở đây.</p>
            <button
              disabled={busy}
              onClick={() => addScene(1)}
              className="mt-3 rounded-lg border border-neutral-700 px-3 py-2 text-sm text-neutral-200 hover:bg-neutral-800 disabled:opacity-40"
            >
              + Thêm scene (kèm 1 shot)
            </button>
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
                {list.map((sh) => (
                  <MediaCard
                    key={sh.id}
                    imageSrc={sh.image_path}
                    videoSrc={sh.video_path}
                    title={sh.title}
                    index={sh.idx}
                    subtitle={sh.video_path ? "▶ video" : sh.status}
                    downloadOptions={downloadChoices(sh, sc.idx)}
                    downloadTitle="Tải video (chọn mốc)"
                    selected={sel?.id === sh.id}
                    busy={running.has(sh.id) || upscaling.has(sh.id)}
                    busyLabel={upscaling.has(sh.id) ? "Đang upscale…" : "Đang render…"}
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
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            delShot(sh);
                          }}
                          title="Xoá shot"
                          className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-rose-600"
                        >
                          🗑
                        </button>
                      </>
                    }
                  />
                ))}
                <div className="flex aspect-video flex-col gap-2">
                  <button
                    onClick={async () => {
                      await storyboard.addShot(sc.id);
                      loadShots(sc.id);
                    }}
                    title="Thêm shot vào cuối scene"
                    className="flex-1 rounded-xl border border-dashed border-neutral-700 text-2xl text-neutral-600 hover:border-neutral-500 hover:text-neutral-400"
                  >
                    +
                  </button>
                  <button
                    onClick={() => setBulk(sc)}
                    title="Thêm nhiều shot cùng lúc — dán văn bản, mỗi dòng một prompt chuyển động"
                    className="shrink-0 rounded-xl border border-dashed border-neutral-700 py-1.5 text-xs text-neutral-600 hover:border-neutral-500 hover:text-neutral-400"
                  >
                    ＋ hàng loạt
                  </button>
                </div>
                {!list.length && (
                  <div className="col-span-full text-xs text-neutral-600">
                    Chưa có frame — làm Storyboard trước, hoặc bấm + để tự thêm shot.
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>

      {bulk && (
        <BulkAddShots
          sceneId={bulk.id}
          sceneTitle={bulk.heading}
          field="motion_prompt"
          onDone={(r) => setByScene((m) => ({ ...m, [bulk.id]: r.shots }))}
          onClose={() => setBulk(null)}
        />
      )}

      {sel && (
        <ShotPanel
          shot={sel}
          project={project}
          upLabel={upLabel}
          downloads={downloadChoices(sel, Math.max(0, scenes.findIndex((s) => s.id === sel.scene_id)))}
          running={running.has(sel.id) || upscaling.has(sel.id)}
          onClose={() => setSel(null)}
          onChange={setShot}
          onGenVideo={() => genVideo(sel)}
        />
      )}
      {lightbox && (
        // ⬇ trong lightbox phải cho ĐÚNG những mốc như ⬇ trên thẻ — hai nút cùng một chỗ mà
        // ra hai file khác cỡ là bẫy.
        <Lightbox
          imageSrc={lightbox.image_path}
          videoSrc={lightbox.video_path}
          title={lightbox.title}
          downloadOptions={downloadChoices(
            lightbox,
            Math.max(0, scenes.findIndex((s) => s.id === lightbox.scene_id))
          )}
          onClose={() => setLightbox(null)}
        />
      )}
    </div>
  );
}

function ShotPanel({
  shot,
  project,
  upLabel,
  downloads,
  running,
  onClose,
  onChange,
  onGenVideo,
}: {
  shot: Shot;
  project: Project;
  // Trần upscale phụ thuộc tier (ONE → 1080p, TWO → 4K) — nhãn do tab hỏi server, không cứng "4K".
  upLabel: string;
  downloads: DownloadChoice[];
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

  useEffect(() => {
    setVisual(shot.visual_prompt ?? "");
    setMotion(shot.motion_prompt ?? "");
    setUpErr(null);
  }, [shot.id]);

  const chained = chainedShot(shot);
  const upscaled = !!currentUpscale(shot);

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
            {/* Mỗi mốc một nút: trong panel rộng rãi thì bày thẳng ra dễ đọc hơn menu xổ. */}
            {downloads.map((d) => (
              <button
                key={d.key}
                onClick={() => d.onSelect()}
                disabled={d.disabled || running}
                title={d.hint}
                className="flex w-full items-center justify-between gap-2 rounded-lg border border-emerald-800/70 px-3 py-2 text-sm text-emerald-300 hover:bg-emerald-950/40 disabled:opacity-40 disabled:hover:bg-transparent"
              >
                <span>⬇ {d.label}</span>
                {d.hint && <span className="truncate text-xs text-neutral-500">{d.hint}</span>}
              </button>
            ))}
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
