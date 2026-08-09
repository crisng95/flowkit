import { useEffect, useState, type ReactNode } from "react";
import { api, type Entity, type Project } from "../api/client";
import ScriptTab from "./script/ScriptTab";
import AssetsTab from "./assets/AssetsTab";
import StoryboardTab from "./storyboard/StoryboardTab";
import ShotsTab from "./shots/ShotsTab";
import AssembleTab from "./assemble/AssembleTab";
import MusicTab from "./music/MusicTab";
import AllImages from "./AllImages";
import NodeEditor, { type EditorTarget } from "./nodeeditor/NodeEditor";
import ProjectSettings from "./settings/ProjectSettings";
import { JobsProvider } from "../jobs/JobsContext";
import JobProgress from "./common/JobProgress";

const TABS = ["Script", "Assets", "Storyboard", "Shots", "Nhạc", "Assemble", "Ảnh"] as const;
type Tab = (typeof TABS)[number];

// Biểu tượng cho chế độ thu gọn (chỉ còn dải icon) — số thứ tự một mình quá khó đoán.
const TAB_ICON: Record<Tab, string> = {
  Script: "📝",
  Assets: "🎭",
  Storyboard: "🖼",
  Shots: "🎬",
  Nhạc: "🎵",
  Assemble: "🎞",
  Ảnh: "🗂",
};

const RAIL_KEY = "fk.sidebar.collapsed";

// Chữ cái đầu của tối đa 2 từ → nhãn cho ô badge cạnh tên dự án.
const initialsOf = (title: string) =>
  (title.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("") || "?")
    .toUpperCase();

// Dòng phụ dưới tên dự án: hai thứ thực sự cần thấy khi đang làm việc.
const aspectLabel = (a?: string | null) =>
  a === "VIDEO_ASPECT_RATIO_PORTRAIT" ? "9:16" : "16:9";

// "10" | "abra_r2v_10s" → "Omni 10s"; rỗng/rác → "Veo". Cùng luật với _video_engine bên
// agent/api/studio.py.
const engineLabel = (videoModel?: string | null) => {
  const m = String(videoModel || "").trim().match(/^(?:abra_r2v_)?(\d+)s?$/);
  const n = m ? Number(m[1]) : NaN;
  return [4, 6, 8, 10].includes(n) ? `Omni ${n}s` : "Veo";
};

export default function ProjectWorkspace({
  project: initial,
  onBack,
}: {
  project: Project;
  onBack: () => void;
}) {
  const [tab, setTab] = useState<Tab>("Script");
  // Keep-alive: render every tab we've visited and just hide the inactive ones, so a
  // long-running job (e.g. Storyboard auto-gen) and its progress survive tab switches.
  const [visited, setVisited] = useState<Set<Tab>>(() => new Set(["Script"]));
  useEffect(() => {
    setVisited((v) => (v.has(tab) ? v : new Set(v).add(tab)));
  }, [tab]);
  const [project, setProject] = useState(initial);
  const [style, setStyle] = useState(initial.style);
  const [editor, setEditor] = useState<EditorTarget | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [reload, setReload] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Sidebar thu gọn thành dải icon — nhớ lựa chọn qua các phiên làm việc.
  const [railed, setRailed] = useState(() => localStorage.getItem(RAIL_KEY) === "1");
  useEffect(() => {
    localStorage.setItem(RAIL_KEY, railed ? "1" : "0");
  }, [railed]);

  // Fetch the full project (with script_raw) on open.
  useEffect(() => {
    api.getProject(initial.id).then(setProject).catch(() => {});
  }, [initial.id]);

  // (Re)load entities on open, every time the node editor opens, and after a node-apply
  // (reload bump). Regenerating an asset elsewhere changes its media_id/image_path, so the
  // "Nguồn ảnh" picker must refetch — otherwise it binds a stale snapshot and shows the old
  // image even though generation (which resolves entity_id live) uses the new one.
  useEffect(() => {
    api.listEntities(initial.id).then((r) => setEntities(r.entities)).catch(() => {});
  }, [initial.id, reload, editor]);

  const openEditor = (t: EditorTarget) => setEditor(t);

  const saveStyle = async () => {
    if (style !== project.style) {
      try {
        await api.updateProject(project.id, { style });
      } catch {
        /* ignore */
      }
    }
  };

  // Plain function (not a component) so the child element keeps its identity across
  // renders — only its visibility toggles. Unvisited tabs aren't rendered yet.
  const pane = (t: Tab, node: ReactNode) =>
    visited.has(t) ? (
      <div key={t} className={tab === t ? "h-full" : "hidden"}>
        {node}
      </div>
    ) : null;

  return (
    <JobsProvider projectId={project.id}>
    <div className="flex h-full flex-col">
      {/* Thanh trên chỉ còn danh tính dự án + cấu hình. Trước đây nó ôm cả 7 tab ở giữa
          (`mx-auto`), nên cửa sổ hẹp là tab bị cắt và tên dự án bị đẩy mất. */}
      <div className="flex items-center gap-3 border-b border-neutral-800 px-4 py-3">
        <button
          onClick={onBack}
          className="shrink-0 rounded-lg px-2 py-1 text-sm text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
        >
          ← Dự án
        </button>
        <div className="h-6 w-px shrink-0 bg-neutral-800" />
        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-[13px] font-semibold tracking-tight text-white ring-1 ring-white/10">
            {initialsOf(project.title)}
          </div>
          <div className="min-w-0">
            {/* `title=` để tên dài bị cắt vẫn xem được đầy đủ khi rê chuột */}
            <h1
              title={project.title}
              className="truncate text-[15px] font-semibold leading-tight tracking-tight text-neutral-100"
            >
              {project.title}
            </h1>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] leading-none text-neutral-500">
              <span className="rounded border border-neutral-800 bg-neutral-900 px-1.5 py-0.5 font-medium text-neutral-400">
                {aspectLabel(project.aspect_ratio)}
              </span>
              <span className="truncate">{engineLabel(project.video_model)}</span>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden text-xs text-neutral-500 lg:inline">Style</span>
          <input
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            onBlur={saveStyle}
            placeholder="Style"
            className="w-32 rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500 lg:w-44"
          />
          <button
            onClick={() => setSettingsOpen(true)}
            title="Cấu hình dự án (prompt header/footer, culture, model)"
            className="rounded-lg border border-neutral-700 px-2.5 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800"
          >
            ⚙
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <nav
          className={`flex shrink-0 flex-col gap-1 overflow-y-auto border-r border-neutral-800 p-2 transition-[width] ${
            railed ? "w-14" : "w-48"
          }`}
        >
          {TABS.map((t, i) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              title={railed ? `${i + 1}. ${t}` : undefined}
              className={`flex items-center rounded-lg text-sm transition ${
                railed ? "justify-center px-0 py-2.5" : "gap-2.5 px-3 py-2"
              } ${
                tab === t
                  ? "bg-neutral-700 text-white"
                  : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
              }`}
            >
              <span className="text-base leading-none">{TAB_ICON[t]}</span>
              {!railed && (
                <>
                  <span className="text-xs text-neutral-500">{i + 1}.</span>
                  <span className="truncate">{t}</span>
                </>
              )}
            </button>
          ))}
          <button
            onClick={() => setRailed((r) => !r)}
            title={railed ? "Mở rộng thanh tab" : "Thu gọn thanh tab"}
            className={`mt-auto rounded-lg py-2 text-sm text-neutral-500 hover:bg-neutral-900 hover:text-neutral-300 ${
              railed ? "px-0 text-center" : "px-3 text-left"
            }`}
          >
            {railed ? "»" : "« Thu gọn"}
          </button>
        </nav>

        <div className="min-w-0 flex-1 overflow-hidden">
          {pane(
            "Script",
            <ScriptTab
              key={project.id}
              project={project}
              onScriptChange={(script_raw) => setProject((p) => ({ ...p, script_raw }))}
            />
          )}
          {pane("Assets", <AssetsTab key={project.id + reload} project={project} onEdit={openEditor} />)}
          {pane(
            "Storyboard",
            <StoryboardTab
              key={project.id + reload}
              project={project}
              onEdit={openEditor}
              onCoverSet={(key) => setProject((p) => ({ ...p, thumb_media_key: key }))}
            />
          )}
          {pane("Shots", <ShotsTab key={project.id + reload} project={project} onEdit={openEditor} />)}
          {pane("Nhạc", <MusicTab key={project.id} project={project} />)}
          {pane("Assemble", <AssembleTab key={project.id + reload} project={project} />)}
          {pane("Ảnh", <AllImages key={project.id + reload} project={project} />)}
        </div>
      </div>

      {editor && (
        <NodeEditor
          target={editor}
          entities={entities}
          projectId={project.id}
          videoModel={project.video_model}
          onClose={() => setEditor(null)}
          onApplied={() => setReload((r) => r + 1)}
        />
      )}

      {settingsOpen && (
        <ProjectSettings
          project={project}
          onClose={() => setSettingsOpen(false)}
          onSaved={(p) => {
            setProject(p);
            setStyle(p.style);
          }}
        />
      )}

      <JobProgress />
    </div>
    </JobsProvider>
  );
}
