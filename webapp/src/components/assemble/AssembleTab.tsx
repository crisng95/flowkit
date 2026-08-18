import { useEffect, useState } from "react";
import { api, storyboard, shots as shotsApi, assemble as asm, type MusicTrack, type Project, type Scene, type Shot } from "../../api/client";
import MusicVideoPanel from "../music/MusicVideoPanel";

export default function AssembleTab({ project }: { project: Project }) {
  const [allShots, setAllShots] = useState<Shot[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [progress, setProgress] = useState("");
  const [finalUrl, setFinalUrl] = useState<string | null>(null);
  const [xmlUrl, setXmlUrl] = useState<string | null>(null);
  const [srtUrl, setSrtUrl] = useState<string | null>(null);
  // Chế độ music video: khâu ghép trả về cách nó khớp hình vào độ dài playlist.
  const [musicInfo, setMusicInfo] = useState<
    { duration: number; target: number; source_duration: number; loops: number } | null
  >(null);
  const [xmlInfo, setXmlInfo] = useState<{ clips: number; captions: number; bgm: boolean; missing: number; missingTitles: string[] } | null>(null);
  const [meta, setMeta] = useState<any>(null);
  const [kenBurns, setKenBurns] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  // Playlist chỉ để MusicVideoPanel biết có bài nào của dự án; panel tự lo phần còn lại
  // (và tự cho chọn bài từ thư viện Flow Music khi playlist rỗng).
  const [tracks, setTracks] = useState<MusicTrack[]>([]);

  useEffect(() => {
    api.musicStatus(project.id).then((s) => setTracks(s.tracks)).catch(() => {});
  }, [project.id]);

  useEffect(() => {
    (async () => {
      const sc: Scene[] = (await api.listScenes(project.id)).scenes;
      let all: Shot[] = [];
      for (const s of sc) all = all.concat((await storyboard.sceneShots(s.id)).shots);
      setAllShots(all);
    })().catch((e) => setErr(e.message));
  }, [project.id]);

  const withVideo = allShots.filter((s) => s.video_path);
  const withImage = allShots.filter((s) => s.image_path);
  const withNarr = allShots.filter((s) => (s as any).narration_path);

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setErr(null);
    try {
      return await fn();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
      setProgress("");
    }
  };

  const narrateAll = () =>
    run("narr", async () => {
      const todo = allShots.filter(
        (s) => (s.video_path || s.image_path) && !(s as any).narration_path
      );
      for (let i = 0; i < todo.length; i++) {
        setProgress(`Narration ${i + 1}/${todo.length}…`);
        const u = await shotsApi.narration(todo[i].id);
        setAllShots((list) => list.map((x) => (x.id === u.id ? u : x)));
      }
    });

  const doAssemble = () =>
    run("assemble", async () => {
      const r = await asm.build(project.id);
      setFinalUrl(r.web_path + "?t=" + Date.now());
      setMusicInfo(r.music ?? null);
    });

  const doAssembleImages = () =>
    run("assemble-img", async () => {
      const r = await asm.buildFromImages(project.id, kenBurns);
      setFinalUrl(r.web_path + "?t=" + Date.now());
      setMusicInfo(r.music ?? null);
    });

  const doExport = () =>
    run("export", async () => {
      const r = await asm.exportSeo(project.id);
      setMeta(r);
    });

  const doDavinci = () =>
    run("xml", async () => {
      setProgress("Đang tạo timeline DaVinci… (có thể mất chút thời gian)");
      const r = await asm.davinci(project.id);
      setXmlUrl(r.web_path + "?t=" + Date.now());
      setSrtUrl(r.captions_srt ? r.captions_srt + "?t=" + Date.now() : null);
      setXmlInfo({ clips: r.clips, captions: r.captions, bgm: r.bgm, missing: r.missing, missingTitles: r.missing_titles });
    });

  return (
    // Khung chứa tab ở ProjectWorkspace là overflow-hidden, nên mỗi tab tự lo phần cuộn.
    <div className="h-full overflow-auto">
    <div className="mx-auto max-w-4xl px-6 py-6">
      <h2 className="mb-1 text-xl font-semibold">Assemble & Export</h2>
      <p className="mb-5 text-sm text-neutral-400">
        Lồng tiếng → ghép video → xuất bản
      </p>

      <div className="mb-6 grid grid-cols-4 gap-3 text-center text-sm">
        <Stat n={allShots.length} label="shots" />
        <Stat n={withImage.length} label="có ảnh" />
        <Stat n={withVideo.length} label="có video" />
        <Stat n={withNarr.length} label="có narration" />
      </div>

      {err && (
        <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {err}
        </div>
      )}
      {progress && <div className="mb-3 text-sm text-indigo-300">{progress}</div>}

      <div className="mb-6 flex flex-wrap gap-3">
        <button onClick={narrateAll} disabled={!!busy}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-40">
          {busy === "narr" ? "Đang lồng tiếng…" : "🎙 Lồng tiếng tất cả"}
        </button>
        <button onClick={doAssemble} disabled={!!busy || !withVideo.length}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40">
          {busy === "assemble" ? "Đang ghép…" : "🎬 Ghép video"}
        </button>
        <button onClick={doAssembleImages} disabled={!!busy || !withImage.length}
          title="Gộp các ảnh shot thành 1 video, mỗi ảnh dài bằng narration của shot"
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40">
          {busy === "assemble-img" ? "Đang ghép ảnh…" : "🖼 Tạo video từ ảnh"}
        </button>
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input type="checkbox" checked={kenBurns} onChange={(e) => setKenBurns(e.target.checked)}
            className="h-4 w-4 accent-emerald-500" />
          Ken Burns (zoom nhẹ)
        </label>
        <button onClick={doExport} disabled={!!busy}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-40">
          {busy === "export" ? "…" : "📝 Export SEO + SRT + Thumbnail"}
        </button>
        <button onClick={doDavinci} disabled={!!busy || (!withVideo.length && !withImage.length)}
          title="Tạo timeline cho DaVinci Resolve: dùng video shot, hoặc ẢNH shot (still) khi chưa có video. Kèm narration từng scene + caption (.srt)"
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-40">
          {busy === "xml" ? "…" : "🎞 Export DaVinci XML"}
        </button>
      </div>

      {finalUrl && (
        <div className="mb-6">
          <h3 className="mb-2 text-sm font-medium text-neutral-300">Video hoàn chỉnh</h3>
          {musicInfo && (
            <p className="mb-2 text-xs text-indigo-300">
              🎵 Khớp theo playlist nhạc: {musicInfo.duration.toFixed(1)}s
              {musicInfo.loops > 0
                ? ` — hình dài ${musicInfo.source_duration.toFixed(1)}s nên được lặp cho phủ kín`
                : " — hình đủ dài, phần thừa đã cắt ở lúc nhạc dứt"}
            </p>
          )}
          <video src={finalUrl} controls className="w-full rounded-xl border border-neutral-800" />
          <a href={finalUrl} download className="mt-2 inline-block text-sm text-indigo-400 hover:text-indigo-300">
            ⭳ Tải final.mp4
          </a>
        </div>
      )}

      {xmlUrl && (
        <div className="mb-6 rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 text-sm">
          {xmlInfo && (
            <div className="mb-1 text-emerald-400">
              ✓ Đã tạo timeline: {xmlInfo.clips} clip · {xmlInfo.captions} caption
              {xmlInfo.bgm ? " · có nhạc nền" : ""}
            </div>
          )}
          {xmlInfo && xmlInfo.missing > 0 && (
            <div className="mb-2 text-amber-400">
              ⚠ {xmlInfo.missing} shot bị bỏ qua (thiếu ảnh/video local, tải lại từ Flow không được):
              {" "}
              {xmlInfo.missingTitles.join(" · ")}. Hãy tạo lại ảnh cho các shot này rồi export lại.
            </div>
          )}
          DaVinci timeline:{" "}
          <a href={xmlUrl} download className="text-indigo-400 hover:text-indigo-300">
            ⭳ timeline.xml
          </a>
          <span className="ml-2 text-neutral-500">Import Timeline trong Resolve, media relink từ ./media</span>
          {srtUrl && (
            <div className="mt-2 text-neutral-300">
              Caption từ khoá:{" "}
              <a href={srtUrl} download className="text-indigo-400 hover:text-indigo-300">
                ⭳ captions.srt
              </a>
              <span className="ml-2 text-neutral-500">
                Kéo vào timeline Resolve → subtitle track (chạy cả bản Free; title track trong XML chỉ vào ở bản Studio)
              </span>
            </div>
          )}
        </div>
      )}

      {meta?.metadata && (
        <div className="space-y-3 rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
          <div>
            <div className="text-xs text-neutral-500">Tiêu đề</div>
            <div className="font-medium">{meta.metadata.title}</div>
          </div>
          <div>
            <div className="text-xs text-neutral-500">Mô tả</div>
            <p className="whitespace-pre-wrap text-sm text-neutral-300">{meta.metadata.description}</p>
          </div>
          <div>
            <div className="text-xs text-neutral-500">Tags</div>
            <div className="flex flex-wrap gap-1.5">
              {(meta.metadata.tags || []).map((t: string) => (
                <span key={t} className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300">{t}</span>
              ))}
            </div>
          </div>
          {meta.thumbnail && (
            <img src={meta.thumbnail} className="w-full max-w-md rounded-lg border border-neutral-800" />
          )}
        </div>
      )}

      {/* Đường ghép NGẮN: để Flow Music tự dựng hình cho một bài hát, không qua storyboard.
          Đặt cuối tab Assemble vì nó cũng cho ra một video hoàn chỉnh — chỉ khác cách làm. */}
      <div className="mt-8">
        <MusicVideoPanel project={project} tracks={tracks} />
      </div>
    </div>
    </div>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 py-3">
      <div className="text-2xl font-semibold">{n}</div>
      <div className="text-xs text-neutral-500">{label}</div>
    </div>
  );
}
