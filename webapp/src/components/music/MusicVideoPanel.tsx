import { useEffect, useRef, useState } from "react";
import {
  api,
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
// Kit (storyboard → shot → clip).
//
// Giới hạn của họ định hình toàn bộ màn này: MỘT lượt = MỘT bài, MỘT đoạn ≤60s. Muốn video
// dài hoặc nhiều bài thì phải dựng nhiều lượt rồi NỐI lại — nên ở đây có hàng đợi và nút
// nối, chứ không phải một nút "tạo video" đơn lẻ.
//
// Ba điều đã đo trên job thật:
//   • ~750 credit + ~9 phút mỗi lượt, credit chỉ trừ khi render XONG (job lỗi không mất gì).
//   • KHÔNG neo phong cách thì mỗi cảnh một chất liệu (ảnh thật → giấy cắt dán → đất nặn
//     trong cùng một video 60s) → ô "ảnh neo" mặc định bật.
//   • Trạng thái chỉ đọc được qua job_id; clip audio KHÔNG bao giờ được cập nhật, nên job_id
//     phải giữ lại ở máy người dùng.

/** Một lượt render đang XẾP HÀNG (chưa gửi đi). Phải xếp hàng chứ không bắn song song:
 *  `video__create_music_video` không nhận tham số, nó bắn ĐỀ XUẤT ĐANG TREO của conversation
 *  — hai lượt chồng nhau là lượt sau cướp đề xuất của lượt trước, và mỗi lượt 750 credit. */
type QueueItem = {
  qid: string;
  clip_id: string;
  conversation_id: string | null;
  title: string;
  aspect: string;
  start_s: number;
  duration_s: number;
  style: string;
  note: string;
  anchor: boolean;
  lyrics: boolean;
};

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
  /** /media/… sau khi đã tải bản của mình về dự án (điều kiện để nối). */
  saved_web?: string | null;
};

const STAGES: Record<string, string> = {
  "02_visual_aesthetic": "chọn phong cách",
  "03_video_planning_from_song": "lên kịch bản theo nhạc",
  "04_video_continuing_shot": "dựng từng cảnh",
  "05_stitch_clips": "ghép cảnh",
  "06_postprocess": "hoàn thiện",
};

const KEY = (pid: string) => `flowkit.musicVideos.${pid}`;
const QKEY = (pid: string) => `flowkit.musicVideoQueue.${pid}`;

function loadJson<T>(key: string): T[] {
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;

export default function MusicVideoPanel({
  project,
  tracks,
}: {
  project: Project;
  tracks: MusicTrack[];
}) {
  // Hai nguồn bài, vì dựng MV không đòi bài phải nằm trong playlist dự án.
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

  const [picked, setPicked] = useState<string[]>([]);
  const [aspect, setAspect] = useState("16:9");
  const [segLen, setSegLen] = useState(60);
  const [segCount, setSegCount] = useState(1);
  const [lyrics, setLyrics] = useState(false);
  const [style, setStyle] = useState("");
  const [note, setNote] = useState("");
  const [anchor, setAnchor] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>(() => loadJson<Job>(KEY(project.id)));
  const [queue, setQueue] = useState<QueueItem[]>(() => loadJson<QueueItem>(QKEY(project.id)));
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [joined, setJoined] = useState<{ web: string; duration: number; parts: number } | null>(
    null
  );
  const confirm = useConfirm();

  useEffect(() => {
    setJobs(loadJson<Job>(KEY(project.id)));
    setQueue(loadJson<QueueItem>(QKEY(project.id)));
    setJoined(null);
  }, [project.id]);

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
  // Đổi nguồn/cuộc trò chuyện thì bỏ chọn cũ — id không còn nằm trong danh sách nữa.
  useEffect(() => setPicked([]), [src, convId]);

  const saveJobs = (next: Job[]) => {
    setJobs(next);
    localStorage.setItem(KEY(project.id), JSON.stringify(next));
  };
  const saveQueue = (next: QueueItem[]) => {
    setQueue(next);
    localStorage.setItem(QKEY(project.id), JSON.stringify(next));
  };
  const refs = useRef({ saveJobs, saveQueue, jobs, queue });
  refs.current = { saveJobs, saveQueue, jobs, queue };

  const running = jobs.some((j) => !j.video_url && j.status !== "error");

  // Poll lượt chưa xong. 20s/lần là đủ: render mất ~9 phút, hỏi dày hơn chỉ tốn lượt relay.
  useEffect(() => {
    if (!running) return;
    let stop = false;
    const tick = async () => {
      const cur = refs.current.jobs;
      const updated = await Promise.all(
        cur.map(async (j) => {
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
      if (!stop) refs.current.saveJobs(updated);
    };
    const id = setInterval(tick, 20000);
    tick();
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [running]);

  // Đầu tàu của hàng đợi: chỉ gửi lượt kế khi KHÔNG còn lượt nào đang chạy.
  useEffect(() => {
    if (running || sending || !queue.length) return;
    let stop = false;
    (async () => {
      setSending(true);
      const item = queue[0];
      const drop = () =>
        refs.current.saveQueue(refs.current.queue.filter((q) => q.qid !== item.qid));
      try {
        const r = await musicApi.createMusicVideo({
          clip_id: item.clip_id,
          conversation_id: item.conversation_id,
          aspect_ratio: item.aspect,
          render_lyrics: item.lyrics,
          style: item.style || null,
          style_image_url: item.anchor ? "auto" : null,
          note: item.note || null,
          start_s: item.start_s,
          duration_s: item.duration_s,
        });
        if (stop) return;
        if (r.status !== "submitted" || !r.video_job_id) {
          setErr(`"${item.title}": Flow Music không nhận lệnh (${r.status}). ${r.text || ""}`.trim());
          drop();
          return;
        }
        if (r.warning) setErr(`"${item.title}": ${r.warning}`);
        refs.current.saveJobs([
          {
            job_id: r.video_job_id,
            clip_id: r.clip_id_used || item.clip_id,
            title: item.title,
            aspect: item.aspect,
            created_at: Date.now(),
            status: "running",
          },
          ...refs.current.jobs,
        ]);
        drop();
      } catch (e: any) {
        if (!stop) {
          setErr(e.message);
          drop();
        }
      } finally {
        if (!stop) setSending(false);
      }
    })();
    return () => {
      stop = true;
    };
  }, [running, sending, queue.length]);

  const enqueue = async () => {
    const chosen = songs.filter((s) => picked.includes(s.clip_id));
    if (!chosen.length) {
      setErr("Chọn ít nhất một bài.");
      return;
    }
    const total = chosen.length * segCount;
    const ok = await confirm({
      title: `Dựng ${total} video?`,
      message:
        `${chosen.length} bài × ${segCount} đoạn ${segLen}s = ${total} lượt render, ` +
        `khoảng ${total * 9} phút và ~${total * 750} credit. Chúng chạy LẦN LƯỢT (Flow Music ` +
        "không cho hai lượt chồng nhau). Credit chỉ trừ khi mỗi lượt render xong.",
      confirmText: `Dựng ${total} video`,
      danger: true,
    });
    if (!ok) return;
    setErr(null);
    const stamp = Date.now();
    const items: QueueItem[] = [];
    chosen.forEach((s, si) => {
      for (let k = 0; k < segCount; k++) {
        items.push({
          qid: `${stamp}-${si}-${k}`,
          clip_id: s.clip_id,
          conversation_id: src === "library" ? convId || null : null,
          title: segCount > 1 ? `${s.title} (${k + 1}/${segCount})` : s.title,
          aspect,
          start_s: k * segLen,
          duration_s: segLen,
          style: style.trim(),
          note: note.trim(),
          anchor,
          lyrics,
        });
      }
    });
    saveQueue([...queue, ...items]);
  };

  const saveToProject = async (j: Job) => {
    if (!j.video_url) return;
    setSaving(j.job_id);
    setErr(null);
    try {
      const r = await api.saveMusicVideo(project.id, j.video_url, j.title);
      saveJobs(jobs.map((x) => (x.job_id === j.job_id ? { ...x, saved_web: r.web } : x)));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(null);
    }
  };

  // Ghép theo PLAYLIST: mỗi bài lấy MV của chính nó (khớp bằng clip_id), hình lặp cho hết
  // bài, tiếng là bản đầy đủ. Đây mới là cách ra video dài đúng nghĩa — nối thẳng các MV chỉ
  // cho ra chuỗi đoạn 60s rời rạc.
  const playlistPairs = tracks
    .map((t) => {
      const cid = clipIdFromAudioUrl(t.audio_url);
      const job = jobs.find((j) => j.clip_id === cid && j.saved_web);
      return { track: t, clip_id: cid, video_web: job?.saved_web || null };
    })
    .filter((x) => !!x.clip_id);
  const ready = playlistPairs.filter((p) => p.video_web);

  const buildPlaylist = async () => {
    if (!ready.length) {
      setErr("Chưa bài nào trong playlist có music video đã lưu vào dự án.");
      return;
    }
    const missing = playlistPairs.length - ready.length;
    const ok = await confirm({
      title: "Dựng video theo playlist?",
      message:
        `${ready.length}/${playlistPairs.length} bài có sẵn music video. Hình của mỗi bài sẽ ` +
        `LẶP cho hết bài đó rồi chuyển sang bài kế; tiếng lấy bản đầy đủ của bài.` +
        (missing ? ` ${missing} bài chưa có video sẽ bị BỎ QUA.` : ""),
      confirmText: "Dựng video",
    });
    if (!ok) return;
    setJoining(true);
    setErr(null);
    try {
      setJoined(
        await api.buildMusicVideo(
          project.id,
          ready.map((p) => ({ track_id: p.track.id, video_web: p.video_web! })),
          `${project.title}-mv`
        )
      );
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setJoining(false);
    }
  };

  // Bản Resolve: cùng phép ghép, nhưng chỗ nối là CROSS DISSOLVE thay vì cắt phựt — ffmpeg
  // ở đường "dựng sẵn" chỉ nối cứng, muốn mượt thì dựng tiếp trong Resolve.
  const [xfade, setXfade] = useState(24);
  const [xml, setXml] = useState<{ web_path: string; clips: number; songs: number } | null>(null);
  const exportDavinci = async () => {
    if (!ready.length) {
      setErr("Chưa bài nào trong playlist có music video đã lưu vào dự án.");
      return;
    }
    setJoining(true);
    setErr(null);
    try {
      setXml(
        await api.musicVideoDavinci(
          project.id,
          ready.map((p) => ({ track_id: p.track.id, video_web: p.video_web! })),
          xfade
        )
      );
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setJoining(false);
    }
  };

  // Nối thô theo thứ tự CŨ → MỚI: dùng khi các lượt là nhiều ĐOẠN của cùng một bài, hoặc khi
  // bài không nằm trong playlist dự án.
  const joinAll = async () => {
    const parts = [...jobs].reverse().filter((j) => j.saved_web);
    if (parts.length < 2) {
      setErr("Cần ít nhất 2 video ĐÃ lưu vào dự án để nối.");
      return;
    }
    if (new Set(parts.map((p) => p.aspect)).size > 1) {
      setErr("Các video phải cùng tỷ lệ khung hình mới nối được.");
      return;
    }
    setJoining(true);
    setErr(null);
    try {
      setJoined(
        await api.concatMusicVideos(
          project.id,
          parts.map((p) => p.saved_web!),
          `${project.title}-mv`
        )
      );
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setJoining(false);
    }
  };

  const forget = (j: Job) => saveJobs(jobs.filter((x) => x.job_id !== j.job_id));
  const savedCount = jobs.filter((j) => j.saved_web).length;
  const inp =
    "w-full rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500";

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-1 flex items-baseline gap-2">
        <h3 className="font-medium">🎬 Music video (Flow Music dựng hình)</h3>
        <span className="text-xs text-neutral-500">~750 credit · ~9 phút · 720p · mỗi lượt 1 bài</span>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-neutral-500">
        Flow Music chỉ dựng được <b>một đoạn ≤60s của một bài</b> mỗi lượt. Cách rẻ nhất để có
        video dài: dựng <b>một video cho mỗi bài</b>, lưu về dự án, rồi bấm{" "}
        <b>Dựng video theo playlist</b> — hình của mỗi bài sẽ lặp cho hết bài đó rồi chuyển
        sang bài kế, tiếng lấy bản đầy đủ. Credit chỉ trừ khi mỗi lượt render xong.
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
                src === s
                  ? "bg-neutral-800 text-neutral-100"
                  : "text-neutral-500 hover:bg-neutral-800/60"
              }`}
            >
              {s === "playlist" ? `Playlist dự án (${playlistSongs.length})` : "Thư viện Flow Music"}
            </button>
          ))}
        </div>

        {src === "library" && (
          <label className="block">
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

        <div>
          <div className="mb-1 flex items-center gap-2 text-xs text-neutral-400">
            <span>Bài hát ({picked.length} đã chọn)</span>
            {songs.length > 1 && (
              <button
                onClick={() =>
                  setPicked(picked.length === songs.length ? [] : songs.map((s) => s.clip_id))
                }
                className="text-indigo-400 hover:text-indigo-300"
              >
                {picked.length === songs.length ? "bỏ chọn hết" : "chọn hết"}
              </button>
            )}
          </div>
          <div className="max-h-40 space-y-0.5 overflow-auto rounded-lg border border-neutral-800 p-1">
            {!songs.length && (
              <p className="px-2 py-3 text-center text-xs text-neutral-600">
                {libBusy
                  ? "đang nạp…"
                  : src === "playlist"
                    ? "Playlist chưa có bài nào từ Flow Music (bài tải lên từ máy không dựng được)."
                    : "Chọn một cuộc trò chuyện để thấy bài."}
              </p>
            )}
            {songs.map((s) => (
              <label
                key={s.clip_id}
                className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-neutral-800/60"
              >
                <input
                  type="checkbox"
                  checked={picked.includes(s.clip_id)}
                  onChange={(e) =>
                    setPicked(
                      e.target.checked
                        ? [...picked, s.clip_id]
                        : picked.filter((x) => x !== s.clip_id)
                    )
                  }
                />
                <span className="truncate text-neutral-300">{s.title}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1 block text-xs text-neutral-400">Tỷ lệ</span>
            <select value={aspect} onChange={(e) => setAspect(e.target.value)} className={inp}>
              <option value="16:9">16:9 ngang</option>
              <option value="9:16">9:16 dọc (Shorts)</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-neutral-400">Mỗi đoạn (giây)</span>
            <input
              type="number"
              min={10}
              max={60}
              step={10}
              value={segLen}
              onChange={(e) => setSegLen(Math.min(60, Math.max(10, Number(e.target.value) || 60)))}
              className={inp}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-neutral-400">Số đoạn mỗi bài</span>
            <select
              value={segCount}
              onChange={(e) => setSegCount(Number(e.target.value))}
              className={inp}
            >
              {[1, 2, 3, 4].map((n) => (
                <option key={n} value={n}>
                  {n} đoạn · {mmss(n * segLen)}
                </option>
              ))}
            </select>
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
            <input type="checkbox" checked={anchor} onChange={(e) => setAnchor(e.target.checked)} />
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
          <button
            onClick={enqueue}
            disabled={!picked.length}
            className="ml-auto rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            🎬 Dựng {picked.length * segCount || ""} video
          </button>
        </div>
      </div>

      {!!queue.length && (
        <div className="mt-4 rounded-lg border border-neutral-800 bg-neutral-950/50 px-3 py-2 text-sm">
          <span className="text-neutral-400">Đang chờ tới lượt ({queue.length}): </span>
          <span className="text-neutral-300">{queue.map((q) => q.title).join(", ")}</span>
          <button
            onClick={() => saveQueue([])}
            className="ml-2 text-xs text-rose-400 hover:text-rose-300"
          >
            huỷ hàng đợi
          </button>
        </div>
      )}

      {!!jobs.length && (
        <div className="mt-4 space-y-2 border-t border-neutral-800 pt-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-neutral-400">
              {jobs.length} lượt · {savedCount} đã lưu vào dự án
              {!!playlistPairs.length && ` · ${ready.length}/${playlistPairs.length} bài playlist có video`}
            </span>
            <button
              onClick={buildPlaylist}
              disabled={joining || !ready.length}
              title="Mỗi bài dùng music video của chính nó, hình lặp cho hết bài, tiếng là bản đầy đủ"
              className="ml-auto rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-40"
            >
              {joining ? "Đang dựng…" : "🎼 Dựng video theo playlist"}
            </button>
            <button
              onClick={joinAll}
              disabled={joining || savedCount < 2}
              title="Nối thô các video đã lưu, giữ nguyên tiếng 60s của từng video — dùng khi chúng là nhiều ĐOẠN của cùng một bài"
              className="rounded-lg border border-sky-700/60 px-3 py-1.5 text-sm text-sky-300 hover:bg-sky-950/40 disabled:opacity-40"
            >
              🔗 Nối thô
            </button>
          </div>

          {/* Đường Resolve: chỗ nối là cross dissolve chứ không cắt phựt như bản ffmpeg. */}
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-800 bg-neutral-950/50 px-3 py-2">
            <span className="text-sm text-neutral-400">Xuất DaVinci Resolve</span>
            <label className="flex items-center gap-1.5 text-xs text-neutral-500">
              cross dissolve
              <input
                type="number"
                min={0}
                max={120}
                step={6}
                value={xfade}
                onChange={(e) => setXfade(Math.max(0, Math.min(120, Number(e.target.value) || 0)))}
                className="w-16 rounded border border-neutral-700 bg-neutral-950 px-1.5 py-1 text-center text-sm text-neutral-200 outline-none focus:border-indigo-500"
              />
              khung ({(xfade / 24).toFixed(2)}s @24fps)
            </label>
            <button
              onClick={exportDavinci}
              disabled={joining || !ready.length}
              title="Timeline .xml: hình lặp hết bài, mỗi mối nối và mỗi chỗ chuyển bài là một cross dissolve"
              className="ml-auto rounded-lg border border-violet-700/60 px-3 py-1.5 text-sm text-violet-300 hover:bg-violet-950/40 disabled:opacity-40"
            >
              {joining ? "Đang xuất…" : "🎞 Xuất timeline"}
            </button>
            {xml && (
              <a
                href={xml.web_path}
                download
                className="w-full text-xs text-violet-300 hover:text-violet-200"
              >
                ✓ {xml.songs} bài · {xml.clips} clip hình · tải {xml.web_path.split("/").pop()}
              </a>
            )}
          </div>

          {joined && (
            <div className="rounded-lg border border-sky-800/60 bg-sky-950/20 p-3">
              <p className="mb-2 text-sm text-sky-300">
                Đã nối {joined.parts} video · {mmss(joined.duration)}
              </p>
              <video src={joined.web} controls className="w-full rounded-lg bg-black" />
              <button
                onClick={() => downloadFile(joined.web, `${slugName(project.title)}-mv.mp4`)}
                className="mt-2 rounded-lg border border-emerald-800/70 px-3 py-1.5 text-sm text-emerald-300 hover:bg-emerald-950/40"
              >
                ⬇ Tải video đã nối
              </button>
            </div>
          )}

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
                  <video
                    src={j.saved_web || j.video_url}
                    controls
                    className="w-full rounded-lg bg-black"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() =>
                        downloadFile(
                          j.saved_web || j.video_url!,
                          `${slugName(j.title || "music-video")}.mp4`
                        )
                      }
                      className="rounded-lg border border-emerald-800/70 px-3 py-1.5 text-sm text-emerald-300 hover:bg-emerald-950/40"
                    >
                      ⬇ Tải về máy
                    </button>
                    {j.saved_web ? (
                      <span className="text-xs text-emerald-400">✓ đã lưu trong dự án</span>
                    ) : (
                      <button
                        onClick={() => saveToProject(j)}
                        disabled={saving === j.job_id}
                        title="Tải bản của mình về dự án — bắt buộc nếu muốn NỐI nhiều video"
                        className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 disabled:opacity-40"
                      >
                        {saving === j.job_id ? "Đang lưu…" : "💾 Lưu vào dự án"}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
