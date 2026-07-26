import { useEffect, useState } from "react";
import { api, thumbUrl, type Project, type FlowProject } from "../api/client";
import Thumb from "./Thumb";
import { useConfirm } from "./common/Confirm";

interface Props {
  onOpen: (p: Project) => void;
}

export default function ProjectGrid({ onOpen }: Props) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [flow, setFlow] = useState<FlowProject[]>([]);
  const [showImport, setShowImport] = useState(false);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const confirm = useConfirm();

  const importZip = async (file: File | undefined) => {
    if (!file) return;
    setImporting(true);
    setErr(null);
    try {
      const p = await api.importProjectZip(file);
      await refresh();
      onOpen(p);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setImporting(false);
    }
  };

  const refresh = async () => {
    try {
      setProjects((await api.listProjects()).projects);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const loadFlow = async () => {
    setShowImport((s) => !s);
    if (!flow.length) {
      try {
        setFlow((await api.flowProjects()).projects);
      } catch (e: any) {
        setErr(e.message);
      }
    }
  };

  const importFlow = async (fp: FlowProject) => {
    await api.createProject({
      title: fp.title || "Untitled",
      import_flow_project_id: fp.flow_project_id,
      import_thumb_media_key: fp.thumb_media_key,
    });
    await refresh();
    setShowImport(false);
  };

  const remove = async (p: Project) => {
    const ok = await confirm({
      title: "Xoá dự án?",
      message: `Dự án "${p.title}" sẽ bị xoá khỏi Studio.`,
      confirmText: "Xoá",
      danger: true,
    });
    if (!ok) return;
    await api.deleteProject(p.id);
    refresh();
  };

  return (
    <div className="px-6 py-8 2xl:px-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dự án</h1>
          <p className="text-sm text-neutral-400">Tạo video từ ý tưởng bằng AI</p>
        </div>
        <div className="flex gap-2">
          <label
            title="Nhập dự án từ file .zip đã export"
            className="cursor-pointer rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium text-neutral-200 hover:bg-neutral-800"
          >
            {importing ? "Đang nhập…" : "⬆ Nhập .zip"}
            <input
              type="file"
              accept=".zip,application/zip"
              className="hidden"
              disabled={importing}
              onChange={(e) => importZip(e.target.files?.[0])}
            />
          </label>
          <button
            onClick={loadFlow}
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium text-neutral-200 hover:bg-neutral-800"
          >
            Import từ Flow
          </button>
          <button
            onClick={() => setCreating(true)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            + Project mới
          </button>
        </div>
      </div>

      {err && (
        <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 px-4 py-2 text-sm text-rose-300">
          {err}
        </div>
      )}

      {showImport && (
        <div className="mb-8 rounded-2xl border border-neutral-800 bg-neutral-900/50 p-4">
          <h2 className="mb-3 text-sm font-medium text-neutral-300">
            Project trên Google Flow
          </h2>
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(200px,1fr))]">
            {flow.map((fp) => (
              <button
                key={fp.flow_project_id}
                onClick={() => importFlow(fp)}
                className="group text-left"
              >
                <Thumb
                  src={fp.thumb_media_key ? thumbUrl(fp.thumb_media_key) : null}
                  alt={fp.title}
                  className="aspect-video w-full ring-1 ring-neutral-800 group-hover:ring-indigo-500"
                />
                <div className="mt-1.5 truncate text-xs text-neutral-300">{fp.title}</div>
              </button>
            ))}
            {!flow.length && (
              <div className="col-span-full py-6 text-center text-sm text-neutral-500">
                Đang tải… (cần extension kết nối)
              </div>
            )}
          </div>
        </div>
      )}

      {/* auto-fill: pack as many ~260px cards as the viewport allows, so an ultra-wide screen
          fills edge-to-edge instead of leaving big margins around a fixed 4-column grid. */}
      <div className="grid gap-5 [grid-template-columns:repeat(auto-fill,minmax(260px,1fr))]">
        {projects.map((p) => (
          <div
            key={p.id}
            className="group overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900/50 transition hover:border-neutral-600"
          >
            <button onClick={() => onOpen(p)} className="block w-full text-left">
              <Thumb
                src={p.thumb_media_key ? thumbUrl(p.thumb_media_key) : null}
                alt={p.title}
                rounded="rounded-none"
                className="aspect-video w-full"
              />
            </button>
            <div className="flex items-center justify-between gap-2 p-3">
              <button onClick={() => onOpen(p)} className="min-w-0 flex-1 text-left">
                <div className="truncate font-medium">{p.title}</div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-neutral-500">
                  <span>{p.style}</span>
                  {p.storytelling ? (
                    <span className="rounded bg-amber-500/15 px-1.5 text-amber-300">
                      storytelling
                    </span>
                  ) : null}
                </div>
              </button>
              <button
                onClick={() => remove(p)}
                title="Xóa"
                className="rounded-md p-1.5 text-neutral-500 opacity-0 transition hover:bg-neutral-800 hover:text-rose-400 group-hover:opacity-100"
              >
                🗑
              </button>
            </div>
          </div>
        ))}
        {!projects.length && (
          <div className="col-span-full rounded-2xl border border-dashed border-neutral-800 py-16 text-center text-neutral-500">
            Chưa có project. Bấm <b className="text-neutral-300">+ Project mới</b> để bắt đầu.
          </div>
        )}
      </div>

      {creating && (
        <CreateModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function CreateModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [aspect, setAspect] = useState("VIDEO_ASPECT_RATIO_LANDSCAPE");
  const [style, setStyle] = useState("Realistic");
  const [scriptLang, setScriptLang] = useState("Tiếng Việt");
  const [storytelling, setStorytelling] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Pre-fill from global defaults (Settings §2.7A) so new projects inherit them.
  useEffect(() => {
    api.getSettings().then((g) => {
      if (g.aspect_ratio) setAspect(g.aspect_ratio);
      if (g.style) setStyle(g.style);
      if (g.script_lang) setScriptLang(g.script_lang);
      if (g.storytelling != null) setStorytelling(!!g.storytelling);
    }).catch(() => {});
  }, []);

  const submit = async () => {
    if (!title.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await api.createProject({ title, aspect_ratio: aspect, style, storytelling,
        script_lang: scriptLang.trim() || "Tiếng Việt" });
      onCreated();
    } catch (e: any) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-semibold">Project mới</h2>
        <label className="mb-1 block text-xs text-neutral-400">Tên project</label>
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ví dụ: Sự tích cây khế"
          className="mb-4 w-full rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs text-neutral-400">Khung hình</label>
            <select
              value={aspect}
              onChange={(e) => setAspect(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
            >
              <option value="VIDEO_ASPECT_RATIO_LANDSCAPE">16:9 ngang</option>
              <option value="VIDEO_ASPECT_RATIO_PORTRAIT">9:16 dọc</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-400">Style</label>
            <input
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
          </div>
        </div>
        <div className="mb-4">
          <label className="mb-1 block text-xs text-neutral-400">Ngôn ngữ kịch bản / lời đọc</label>
          <input
            value={scriptLang}
            onChange={(e) => setScriptLang(e.target.value)}
            placeholder="Tiếng Việt"
            className="w-full rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
        </div>
        <label className="mb-4 flex items-center gap-2 text-sm text-neutral-300">
          <input
            type="checkbox"
            checked={storytelling}
            onChange={(e) => setStorytelling(e.target.checked)}
            className="h-4 w-4 accent-indigo-500"
          />
          Chế độ Storytelling (giọng đọc dẫn dắt)
        </label>
        {err && <div className="mb-3 text-sm text-rose-400">{err}</div>}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-800"
          >
            Hủy
          </button>
          <button
            onClick={submit}
            disabled={busy || !title.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {busy ? "Đang tạo…" : "Tạo"}
          </button>
        </div>
      </div>
    </div>
  );
}
