import { useEffect, useState } from "react";
import {
  api,
  musicApi,
  type Project,
  type MusicSong,
  type MusicConversation,
} from "../../api/client";
import { useConfirm } from "../common/Confirm";

// Sinh/quản lý nhạc nền bằng Flow Music: tạo mới (1 hoặc 2 bản A/B, nghe thử rồi chọn),
// hoặc chọn lại 1 bài đã tạo trước đó trong tài khoản flowmusic.app (kèm xoá).
export default function MusicManager({
  project,
  volume,
  onApplied,
  onClose,
}: {
  project: Project;
  volume: number;
  onApplied: (p: Project) => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"new" | "library">("new");
  const [err, setErr] = useState<string | null>(null);

  // ── Tạo mới ──────────────────────────────────────────────
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<MusicSong[] | null>(null);

  const generate = async () => {
    if (!prompt.trim()) return;
    setBusy(true);
    setErr(null);
    setCandidates(null);
    try {
      const r = await api.generateBgm(project.id, prompt.trim(), null, volume);
      if ("pending_selection" in r) {
        setCandidates(r.songs);
      } else {
        onApplied(r);
        onClose();
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const pick = async (song: MusicSong) => {
    setBusy(true);
    setErr(null);
    try {
      const p = await api.selectBgm(project.id, song.audio_url, volume);
      onApplied(p);
      onClose();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  // ── Bài đã tạo ───────────────────────────────────────────
  const [convos, setConvos] = useState<MusicConversation[] | null>(null);
  const [convBusy, setConvBusy] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedSongs, setExpandedSongs] = useState<MusicSong[] | null>(null);
  const confirm = useConfirm();

  useEffect(() => {
    if (tab !== "library" || convos !== null) return;
    setConvBusy(true);
    musicApi
      .conversations(30)
      .then(setConvos)
      .catch((e) => setErr(e.message))
      .finally(() => setConvBusy(false));
  }, [tab, convos]);

  const expand = async (c: MusicConversation) => {
    if (expanded === c.id) {
      setExpanded(null);
      return;
    }
    setExpanded(c.id);
    setExpandedSongs(null);
    setErr(null);
    try {
      setExpandedSongs(await musicApi.conversationSongs(c.id));
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const remove = async (c: MusicConversation) => {
    if (
      !(await confirm({
        title: "Xoá bài hát này?",
        message: `"${c.title || "(không tên)"}" sẽ bị xoá khỏi tài khoản Flow Music. Không thể hoàn tác.`,
        danger: true,
        confirmText: "Xoá",
      }))
    )
      return;
    try {
      await musicApi.deleteConversation(c.id);
      setConvos((prev) => prev?.filter((x) => x.id !== c.id) ?? null);
      if (expanded === c.id) setExpanded(null);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 p-6"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-neutral-800 px-5 py-3">
          <h3 className="font-semibold">🎧 Nhạc nền — Flow Music</h3>
          <button onClick={onClose} className="ml-auto text-neutral-500 hover:text-neutral-300">
            ✕
          </button>
        </div>

        <div className="flex border-b border-neutral-800 px-5">
          <button
            onClick={() => setTab("new")}
            className={`px-3 py-2 text-sm ${tab === "new" ? "border-b-2 border-indigo-500 text-neutral-100" : "text-neutral-500 hover:text-neutral-300"}`}
          >
            Tạo mới
          </button>
          <button
            onClick={() => setTab("library")}
            className={`px-3 py-2 text-sm ${tab === "library" ? "border-b-2 border-indigo-500 text-neutral-100" : "text-neutral-500 hover:text-neutral-300"}`}
          >
            Bài đã tạo
          </button>
        </div>

        <div className="flex-1 overflow-auto p-5">
          {err && (
            <div className="mb-3 rounded-lg bg-rose-950/40 px-3 py-2 text-sm text-rose-300">{err}</div>
          )}

          {tab === "new" && (
            <div className="space-y-3">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={
                  "Mô tả nhạc bằng tiếng Anh: nhạc cụ, nhịp độ, tâm trạng...\n" +
                  "Vd: Instrumental lofi chillhop, 72 BPM, warm boom-bap drums, rainy evening mood, no vocals, smooth loopable intro and outro"
                }
                rows={4}
                disabled={busy}
                className="w-full resize-none rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
              />
              <button
                onClick={generate}
                disabled={busy || !prompt.trim()}
                className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
              >
                {busy ? "Đang tạo… (thường 30–70s)" : "🎵 Sinh nhạc"}
              </button>

              {candidates && candidates.length > 0 && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs text-neutral-500">
                    Flow Music ra {candidates.length} bản — nghe thử rồi chọn 1:
                  </p>
                  {candidates.map((s) => (
                    <SongCard key={s.clip_id} song={s} busy={busy} onPick={() => pick(s)} />
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "library" && (
            <div className="space-y-2">
              {convBusy && <p className="text-sm text-neutral-500">Đang tải…</p>}
              {convos && convos.length === 0 && (
                <p className="text-sm text-neutral-500">Chưa có bài nào.</p>
              )}
              {convos?.map((c) => (
                <div key={c.id} className="rounded-lg border border-neutral-800">
                  <div className="flex items-center gap-2 px-3 py-2">
                    <button
                      onClick={() => expand(c)}
                      className="flex-1 truncate text-left text-sm text-neutral-200 hover:text-white"
                    >
                      {expanded === c.id ? "▾" : "▸"} {c.title || "(không tên)"}
                    </button>
                    <span className="shrink-0 text-xs text-neutral-600">
                      {new Date(c.last_message_at).toLocaleDateString("vi-VN")}
                    </span>
                    <button
                      onClick={() => remove(c)}
                      className="shrink-0 text-rose-400 hover:text-rose-300"
                      title="Xoá"
                    >
                      🗑
                    </button>
                  </div>
                  {expanded === c.id && (
                    <div className="space-y-2 border-t border-neutral-800 px-3 py-2">
                      {expandedSongs === null && (
                        <p className="text-xs text-neutral-500">Đang tải…</p>
                      )}
                      {expandedSongs && expandedSongs.length === 0 && (
                        <p className="text-xs text-neutral-500">
                          Không tìm thấy bài hát trong đoạn chat này.
                        </p>
                      )}
                      {expandedSongs?.map((s) => (
                        <SongCard key={s.clip_id} song={s} busy={busy} onPick={() => pick(s)} />
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SongCard({
  song,
  busy,
  onPick,
}: {
  song: MusicSong;
  busy: boolean;
  onPick: () => void;
}) {
  const mins = song.duration_s ? Math.floor(song.duration_s / 60) : 0;
  const secs = song.duration_s ? Math.round(song.duration_s % 60) : 0;
  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-900 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="truncate text-sm font-medium text-neutral-200">
          {song.title || "(không tên)"}
        </span>
        {song.duration_s != null && (
          <span className="shrink-0 text-xs tabular-nums text-neutral-500">
            {mins}:{String(secs).padStart(2, "0")}
          </span>
        )}
      </div>
      <audio controls src={song.audio_url} className="h-8 w-full" />
      <button
        onClick={onPick}
        disabled={busy}
        className="mt-2 w-full rounded-md bg-indigo-600/20 px-3 py-1.5 text-xs font-medium text-indigo-300 hover:bg-indigo-600/30 disabled:opacity-40"
      >
        ✓ Dùng bài này làm nhạc nền
      </button>
    </div>
  );
}
