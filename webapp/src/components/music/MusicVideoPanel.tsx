import { useEffect, useRef, useState } from "react";
import {
  clipIdFromAudioUrl,
  musicApi,
  type MusicConversation,
  type MusicSong,
  type MusicTrack,
  type Project,
} from "../../api/client";
import { useConfirm } from "../common/Confirm";
import { downloadFile, slugName } from "../../lib/download";

// Music video của Flow Music: HỌ dựng hình cho bài hát, khác hẳn đường dựng video của Flow
// Kit (storyboard → shot → clip). Dùng khi muốn một MV minh hoạ nhanh cho một bài trong
// playlist, không phải khi muốn kiểm soát từng khung hình.
//
// Ba điều đã đo trên job thật, và UI này được dựng quanh chúng:
//   • ~750 credit + ~9 phút mỗi video, credit chỉ trừ khi render XONG (job lỗi không mất gì).
//   • KHÔNG neo phong cách thì mỗi cảnh một chất liệu (ảnh thật → giấy cắt dán → đất nặn
//     trong cùng một video 60s). Vì vậy ô "ảnh neo" mặc định bật.
//   • Trạng thái chỉ đọc được qua job_id; clip audio KHÔNG bao giờ được cập nhật. Nên job_id
//     phải được giữ lại ở máy người dùng, nếu không là mất dấu video đang render.

type Job = {
  job_id: string;
  clip_id: string;
  title: string;
  aspect: string;
  created_at: number;
  video_url?: string | null;
  status?: string;
  stage?: string | null;
  error?: string | null;
};

const STAGES: Record<string, string> = {
  "02_visual_aesthetic": "chọn phong cách",
  "03_video_planning_from_song": "lên kịch bản theo nhạc",
  "04_video_continuing_shot": "dựng từng cảnh",
  "05_stitch_clips": "ghép cảnh",
  "06_postprocess": "hoàn thiện",
};

const KEY = (pid: string) => `flowkit.musicVideos.${pid}`;

const loadJobs = (pid: string): Job[] => {
  try {
    return JSON.parse(localStorage.getItem(KEY(pid)) || "[]");
  } catch {
    return [];
  }
};

export default function MusicVideoPanel({
  project,
  tracks,
}: {
  project: Project;
  tracks: MusicTrack[];
}) {
  // Hai nguồn bài, vì dựng MV không đòi bài phải nằm trong playlist dự án:
  //   "playlist"  — bài đã thêm vào dự án (chỉ bài gốc Flow Music: bài upload từ máy không
  //                 có clip_id bên họ nên không dựng được).
  //   "library"   — mọi bài trong tài khoản flowmusic.app, lấy qua conversation.
  const [src, setSrc] = useState<"playlist" | "library">("playlist");
  const [convs, setConvs] = useState<MusicConversation[]>([]);
  const [convId, setConvId] = useState("");
  const [libSongs, setLibSongs] = useState<MusicSong[]>([]);
  const [libBusy, setLibBusy] = useState(false);

  const playlistSongs = tracks
    .map((t) => ({ clip_id: clipIdFromAudioUrl(t.audio_url), title: t.title }))
    .filter((x) => !!x.clip_id) as { clip_id: string; title: string }[];
  const songs =
    src === "playlist"
      ? playlistSongs
      : libSongs.map((s) => ({ clip_id: s.clip_id, title: s.title || s.clip_id.slice(0, 8) }));

  const [clipId, setClipId] = useState<string>("");
  const [aspect, setAspect] = useState("16:9");
  const [durationS, setDurationS] = useState(60);
  const [startS, setStartS] = useState(0);
  const [lyrics, setLyrics] = useState(false);
  const [style, setStyle] = useState("");
  const [note, setNote] = useState("");
  const [anchor, setAnchor] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>(() => loadJobs(project.id));
  const confirm = useConfirm();

  useEffect(() => setJobs(loadJobs(project.id)), [project.id]);
  useEffect(() => {
    if (songs.length && !songs.some((s) => s.clip_id === clipId)) setClipId(songs[0].clip_id);
  }, [songs.map((s) => s.clip_id).join(",")]);

  // Thư viện: nạp danh sách conversation một lần, bài trong đó nạp khi chọn.
  useEffect(() => {
    if (src !== "library" || convs.length) return;
    musicApi.conversations(30).then(setConvs).catch((e) => setErr(e.message));
  }, [src]);
  useEffect(() => {
    if (!convId) return;
    setLibBusy(true);
    musicApi
      .conversationSongs(convId)
      .then(setLibSongs)
      .catch((e) => setErr(e.message))
      .finally(() => setLibBusy(false));
  }, [convId]);

  const save = (next: Job[]) => {
    setJobs(next);
    localStorage.setItem(KEY(project.id), JSON.stringify(next));
  };
  const saveRef = useRef(save);
  saveRef.current = save;

  // Poll job chưa xong. 20s/lần là đủ: render mất ~9 phút, hỏi dày hơn chỉ tốn lượt relay.
  useEffect(() => {
    const pending = jobs.filter((j) => !j.video_url && j.status !== "error");
    if (!pending.length) return;
    let stop = false;
    const tick = async () => {
      const updated = await Promise.all(
        jobs.map(async (j) => {
          if (j.video_url || j.status === "error") return j;
          try {
            const r = await musicApi.musicVideoJob(j.job_id);
            return {
              ...j,
              status: r.status,
              stage: r.stage,
              video_url: r.video_url,
              error: r.error,
            };
          } catch {
            return j;
          }
        })
      );
      if (!stop) saveRef.current(updated);
    };
    const id = setInterval(tick, 20000);
    tick();
    return () => {
      stop = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs.map((j) => `${j.job_id}:${j.video_url ? 1 : 0}:${j.status}`).join(",")]);

  const submit = async () => {
    const song = songs.find((s) => s.clip_id === clipId);
    if (!song) {
      setErr("Chọn một bài lấy từ Flow Music trước.");
      return;
    }
    const ok = await confirm({
      title: "Dựng music video?",
      message:
        `Flow Music sẽ dựng ${durationS}s hình cho "${song.title}" — khoảng 9 phút và ` +
        "~750 credit. Credit chỉ bị trừ khi render xong; job hỏng giữa chừng thì không mất gì.",
      confirmText: "Dựng video",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await musicApi.createMusicVideo({
        clip_id: song.clip_id,
        // Đúng conversation của bài thì agent khỏi phải mò — và đề xuất treo đúng chỗ.
        conversation_id: src === "library" ? convId || null : null,
        aspect_ratio: aspect,
        render_lyrics: lyrics,
        style: style.trim() || null,
        // "auto" = nhờ Flow Music sinh ảnh neo trước. Không neo là mỗi cảnh một chất liệu.
        style_image_url: anchor ? "auto" : null,
        note: note.trim() || null,
        start_s: startS,
        duration_s: durationS,
      });
      if (r.status !== "submitted" || !r.video_job_id) {
        setErr(
          r.status === "proposed"
            ? "Flow Music mới dừng ở bước đề xuất, chưa nhận render — thử lại."
            : `Flow Music không nhận lệnh dựng video. ${r.text || ""}`
        );
        return;
      }
      if (r.warning) setErr(r.warning);
      save([
        {
          job_id: r.video_job_id,
          clip_id: r.clip_id_used || song.clip_id,
          title: song.title,
          aspect,
          created_at: Date.now(),
          status: "running",
        },
        ...jobs,
      ]);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const forget = (j: Job) => save(jobs.filter((x) => x.job_id !== j.job_id));

  const inp =
    "w-full rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-1 flex items-baseline gap-2">
        <h3 className="font-medium">🎬 Music video (Flow Music dựng hình)</h3>
        <span className="text-xs text-neutral-500">~750 credit · ~9 phút · 720p</span>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-neutral-500">
        Flow Music tự lên kịch bản hình theo bài hát — nhanh, nhưng không kiểm soát được từng
        khung như đường storyboard của Flow Kit. Credit chỉ trừ khi render xong.
      </p>

      {err && (
        <div className="mb-3 rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {err}
        </div>
      )}

      <div className="space-y-3">
          <div className="flex gap-1 text-xs">
            {(["playlist", "library"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setSrc(s)}
                className={`rounded-lg px-2.5 py-1 ${
                  src === s ? "bg-neutral-800 text-neutral-100" : "text-neutral-500 hover:bg-neutral-800/60"
                }`}
              >
                {s === "playlist" ? `Playlist dự án (${playlistSongs.length})` : "Thư viện Flow Music"}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {src === "library" && (
              <label className="col-span-2 block sm:col-span-4">
                <span className="mb-1 block text-xs text-neutral-400">Cuộc trò chuyện</span>
                <select value={convId} onChange={(e) => setConvId(e.target.value)} className={inp}>
                  <option value="">— chọn —</option>
                  {convs.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="col-span-2 block">
              <span className="mb-1 block text-xs text-neutral-400">Bài hát</span>
              <select
                value={clipId}
                onChange={(e) => setClipId(e.target.value)}
                disabled={!songs.length}
                className={inp}
              >
                {!songs.length && (
                  <option value="">
                    {libBusy
                      ? "đang nạp…"
                      : src === "playlist"
                        ? "playlist chưa có bài từ Flow Music"
                        : "chọn cuộc trò chuyện trước"}
                  </option>
                )}
                {songs.map((s) => (
                  <option key={s.clip_id} value={s.clip_id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-neutral-400">Tỷ lệ</span>
              <select value={aspect} onChange={(e) => setAspect(e.target.value)} className={inp}>
                <option value="16:9">16:9 ngang</option>
                <option value="9:16">9:16 dọc (Shorts)</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-neutral-400">Độ dài (giây)</span>
              <input
                type="number"
                min={10}
                max={180}
                step={10}
                value={durationS}
                onChange={(e) => setDurationS(Math.max(10, Number(e.target.value) || 60))}
                className={inp}
              />
            </label>
          </div>

          <label className="block">
            <span className="mb-1 block text-xs text-neutral-400">
              Phong cách — nét vẽ, chất liệu, bảng màu
            </span>
            <div className="flex gap-2">
              <input
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                placeholder="vd: late-2000s Japanese TV-anime, thin even line art, flat two-tone cel shading"
                className={inp}
              />
              {!!project.style && (
                <button
                  type="button"
                  onClick={() => setStyle(project.style.replace(/\s+/g, " ").slice(0, 400))}
                  title="Lấy phong cách của dự án làm điểm xuất phát"
                  className="shrink-0 rounded-lg border border-neutral-700 px-2.5 text-xs text-neutral-300 hover:bg-neutral-800"
                >
                  ↤ style dự án
                </button>
              )}
            </div>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-neutral-400">
              Nội dung khung hình — CÁI GÌ xuất hiện (đừng lẫn chất liệu vào đây)
            </span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="vd: phố cổ Hà Nội chiều mưa, đèn lồng, cô gái cầm ô trong suốt"
              className={inp}
            />
          </label>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={anchor}
                onChange={(e) => setAnchor(e.target.checked)}
              />
              <span>
                Ảnh neo phong cách
                <span className="ml-1 text-xs text-neutral-500">
                  (tự tạo trước — tắt thì mỗi cảnh một chất liệu)
                </span>
              </span>
            </label>
            <label className="flex cursor-pointer items-center gap-2">
              <input type="checkbox" checked={lyrics} onChange={(e) => setLyrics(e.target.checked)} />
              <span>Hiện lời bài hát</span>
            </label>
            <label className="flex items-center gap-2">
              <span className="text-neutral-400">Bắt đầu từ</span>
              <input
                type="number"
                min={0}
                step={10}
                value={startS}
                onChange={(e) => setStartS(Math.max(0, Number(e.target.value) || 0))}
                className="w-20 rounded-lg border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm outline-none focus:border-indigo-500"
              />
              <span className="text-neutral-500">giây</span>
            </label>
            <button
              onClick={submit}
              disabled={busy || !clipId}
              className="ml-auto rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
            >
              {busy ? "Đang gửi…" : "🎬 Dựng music video"}
            </button>
          </div>
      </div>

      {!!jobs.length && (
        <div className="mt-4 space-y-2 border-t border-neutral-800 pt-4">
          {jobs.map((j) => (
            <div key={j.job_id} className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium">{j.title}</span>
                <span className="shrink-0 text-xs text-neutral-600">{j.aspect}</span>
                {j.video_url ? (
                  <span className="shrink-0 rounded bg-emerald-900/50 px-1.5 py-0.5 text-[11px] text-emerald-300">
                    xong
                  </span>
                ) : j.status === "error" ? (
                  <span className="shrink-0 rounded bg-rose-900/50 px-1.5 py-0.5 text-[11px] text-rose-300">
                    hỏng — không bị trừ credit
                  </span>
                ) : (
                  <span className="shrink-0 animate-pulse rounded bg-indigo-900/50 px-1.5 py-0.5 text-[11px] text-indigo-300">
                    đang dựng · {STAGES[j.stage || ""] || j.stage || "chờ"}
                  </span>
                )}
                <button
                  onClick={() => forget(j)}
                  title="Bỏ khỏi danh sách (video trên Flow Music vẫn còn)"
                  className="ml-auto shrink-0 rounded px-1.5 text-neutral-600 hover:bg-neutral-800 hover:text-neutral-300"
                >
                  ✕
                </button>
              </div>
              {j.error && <p className="mt-1 text-xs text-rose-400">{j.error}</p>}
              {j.video_url && (
                <div className="mt-2 space-y-2">
                  <video src={j.video_url} controls className="w-full rounded-lg bg-black" />
                  <button
                    onClick={() =>
                      downloadFile(j.video_url!, `${slugName(j.title || "music-video")}.mp4`)
                    }
                    className="rounded-lg border border-emerald-800/70 px-3 py-1.5 text-sm text-emerald-300 hover:bg-emerald-950/40"
                  >
                    ⬇ Tải video
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
