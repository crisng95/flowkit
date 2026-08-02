import { useEffect, useRef, useState } from "react";
import { api, type MusicStatus, type MusicTrack, type Project } from "../../api/client";
import { useConfirm } from "../common/Confirm";
import MusicManager from "./MusicManager";

// Playlist nhạc của dự án — chế độ "music video": nhiều bài phát nối tiếp, cách nhau `gap`
// giây, và TỔNG thời lượng playlist quyết định độ dài video. Hình (scene/shot) là một dòng
// chung trải lên toàn bộ playlist; thiếu bao nhiêu thì lặp lại từ đầu cho phủ kín, thừa thì
// cắt ở đúng lúc nhạc dứt.
//
// Khác mục "🎵 Nhạc nền" trong ⚙ cấu hình dự án: bên đó là MỘT bài chìm dưới lời đọc.

function mmss(s: number): string {
  if (!s || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.round(s % 60)).padStart(2, "0")}`;
}

export default function MusicTab({ project }: { project: Project }) {
  const [st, setSt] = useState<MusicStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [picker, setPicker] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const confirm = useConfirm();

  const load = async () => {
    try {
      setSt(await api.musicStatus(project.id));
    } catch (e: any) {
      setErr(e.message);
    }
  };
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  const run = async (fn: () => Promise<MusicStatus>) => {
    setBusy(true);
    setErr(null);
    try {
      setSt(await fn());
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const upload = (f: File | undefined) => {
    if (!f) return;
    run(() => api.uploadTrack(project.id, f));
    if (fileRef.current) fileRef.current.value = "";
  };

  const move = (i: number, dir: -1 | 1) => {
    if (!st) return;
    const ids = st.tracks.map((t) => t.id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    run(() => api.reorderTracks(project.id, ids));
  };

  const remove = async (t: MusicTrack) => {
    const ok = await confirm({
      title: "Xoá bài khỏi playlist?",
      message: `"${t.title}" sẽ bị gỡ khỏi dự án và xoá file nhạc đã tải về. Bài gốc trên flowmusic.app vẫn còn.`,
      danger: true,
      confirmText: "Xoá",
    });
    if (ok) run(() => api.deleteTrack(t.id));
  };

  const tracks = st?.tracks ?? [];
  const gap = st?.gap ?? 3;
  const short = st?.shortfall ?? 0;

  return (
    <div className="h-full overflow-auto px-6 py-5">
      <div className="mx-auto max-w-3xl space-y-4">
        {err && (
          <div className="rounded-lg bg-rose-950/40 px-3 py-2 text-sm text-rose-300">{err}</div>
        )}

        {/* Chế độ + khoảng cách giữa các bài */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={!!st?.music_mode}
              disabled={busy || !st}
              onChange={(e) => run(() => api.musicSettings(project.id, { music_mode: e.target.checked }))}
              className="mt-1"
            />
            <span>
              <span className="font-medium">Chế độ music video</span>
              <p className="mt-1 text-xs text-neutral-500">
                Playlist dưới đây là tiếng DUY NHẤT của video (lời đọc TTS bị bỏ) và độ dài
                của nó quyết định độ dài video: hình ngắn hơn thì lặp lại từ đầu cho phủ kín,
                dài hơn thì cắt đúng lúc nhạc dứt. Tắt = quay về nhạc nền một bài chìm dưới
                lời đọc (trong ⚙ cấu hình dự án).
              </p>
            </span>
          </label>

          <div className="mt-3 flex items-center gap-2 border-t border-neutral-800 pt-3">
            <span className="text-sm text-neutral-400">Cách nhau giữa 2 bài</span>
            <input
              type="number"
              min={0}
              max={30}
              step={0.5}
              defaultValue={gap}
              key={gap}
              disabled={busy}
              onBlur={(e) => {
                const v = parseFloat(e.target.value);
                if (!isNaN(v) && v !== gap) run(() => api.musicSettings(project.id, { gap: v }));
              }}
              className="w-20 rounded-lg border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm outline-none focus:border-indigo-500"
            />
            <span className="text-sm text-neutral-500">giây im lặng (không cộng sau bài cuối)</span>
          </div>
        </div>

        {/* Đối chiếu thời lượng */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-neutral-800 bg-neutral-900/40 px-4 py-3 text-sm">
          <span>
            <span className="text-neutral-500">Nhạc </span>
            <b className="tabular-nums text-indigo-300">{mmss(st?.music_duration ?? 0)}</b>
            <span className="text-neutral-600"> ({tracks.length} bài)</span>
          </span>
          <span>
            <span className="text-neutral-500">Hình </span>
            <b className="tabular-nums text-neutral-200">{mmss(st?.video_duration ?? 0)}</b>
            <span className="text-neutral-600">
              {st?.video_measured ? " (đo từ bản đã ghép)" : " (ước tính từ shot)"}
            </span>
          </span>
          {short > 0.5 ? (
            <span className="text-amber-300">
              Thiếu {mmss(short)} — khi ghép, hình sẽ được lặp lại cho phủ kín nhạc.
            </span>
          ) : tracks.length > 0 ? (
            <span className="text-emerald-400">Hình đủ phủ nhạc.</span>
          ) : null}
        </div>

        {/* Playlist */}
        <div className="space-y-2">
          {tracks.length === 0 && (
            <p className="rounded-xl border border-dashed border-neutral-800 px-4 py-8 text-center text-sm text-neutral-500">
              Chưa có bài nào. Thêm nhạc bằng hai nút bên dưới — thứ tự trong danh sách là thứ
              tự phát.
            </p>
          )}
          {tracks.map((t, i) => (
            <div
              key={t.id}
              className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-neutral-900/40 px-3 py-2"
            >
              <span className="w-6 shrink-0 text-center text-sm tabular-nums text-neutral-600">
                {i + 1}
              </span>
              <div className="flex shrink-0 flex-col">
                <button
                  onClick={() => move(i, -1)}
                  disabled={busy || i === 0}
                  className="text-xs leading-none text-neutral-500 hover:text-neutral-200 disabled:opacity-20"
                  title="Lên trên"
                >
                  ▲
                </button>
                <button
                  onClick={() => move(i, 1)}
                  disabled={busy || i === tracks.length - 1}
                  className="text-xs leading-none text-neutral-500 hover:text-neutral-200 disabled:opacity-20"
                  title="Xuống dưới"
                >
                  ▼
                </button>
              </div>
              <div className="min-w-0 flex-1">
                <input
                  defaultValue={t.title}
                  key={t.title}
                  disabled={busy}
                  onBlur={(e) => {
                    const v = e.target.value.trim();
                    if (v && v !== t.title) run(() => api.renameTrack(t.id, v));
                  }}
                  className="w-full truncate rounded border border-transparent bg-transparent px-1 py-0.5 text-sm text-neutral-200 hover:border-neutral-700 focus:border-indigo-500 focus:outline-none"
                />
                {t.web_path && <audio controls src={t.web_path} className="mt-1 h-8 w-full" />}
              </div>
              <span className="shrink-0 text-xs tabular-nums text-neutral-500">
                {mmss(t.duration)}
              </span>
              <span
                className="shrink-0 text-xs text-neutral-600"
                title={t.source === "upload" ? "Tải lên từ máy" : "Sinh bằng Flow Music"}
              >
                {t.source === "upload" ? "📁" : "🎧"}
              </span>
              <button
                onClick={() => remove(t)}
                disabled={busy}
                className="shrink-0 text-rose-400 hover:text-rose-300 disabled:opacity-40"
                title="Xoá khỏi playlist"
              >
                🗑
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <label className="flex flex-1 cursor-pointer items-center justify-center rounded-lg border border-dashed border-neutral-700 px-3 py-3 text-sm text-neutral-400 hover:border-indigo-500 hover:text-neutral-200">
            {busy ? "Đang xử lý…" : "＋ Tải file nhạc lên"}
            <input
              ref={fileRef}
              type="file"
              accept="audio/*"
              className="hidden"
              disabled={busy}
              onChange={(e) => upload(e.target.files?.[0])}
            />
          </label>
          <button
            onClick={() => setPicker(true)}
            disabled={busy}
            className="flex-1 rounded-lg border border-dashed border-neutral-700 px-3 py-3 text-sm text-neutral-400 hover:border-indigo-500 hover:text-neutral-200 disabled:opacity-40"
          >
            🎧 Sinh / chọn bằng Flow Music
          </button>
        </div>

        <p className="text-xs text-neutral-600">
          Ghép video ở tab <b>Assemble</b> như bình thường — khi bật chế độ music video, khâu
          ghép sẽ tự nối playlist thành một dải âm thanh rồi khớp hình vào đúng độ dài đó.
        </p>
      </div>

      {picker && (
        <MusicManager
          project={project}
          volume={0}
          mode="playlist"
          onTracks={setSt}
          onClose={() => setPicker(false)}
        />
      )}
    </div>
  );
}
