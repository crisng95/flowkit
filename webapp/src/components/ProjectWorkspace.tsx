import {
  useEffect, useState,
  type Dispatch, type ReactNode, type SetStateAction,
} from "react";
import { api, type Entity, type Project } from "../api/client";
import ScriptTab from "./script/ScriptTab";
import AssetsTab from "./assets/AssetsTab";
import StoryboardTab from "./storyboard/StoryboardTab";
import ShotsTab from "./shots/ShotsTab";
import AssembleTab from "./assemble/AssembleTab";
import MusicTab from "./music/MusicTab";
import AllImages from "./AllImages";
import NodeEditor, { type EditorTarget } from "./nodeeditor/NodeEditor";
import SettingsTab from "./settings/SettingsTab";
import { JobsProvider } from "../jobs/JobsContext";
import JobProgress from "./common/JobProgress";

const TABS = ["Script", "Assets", "Storyboard", "Shots", "Nhạc", "Assemble", "Ảnh",
  "Thiết lập"] as const;
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
  "Thiết lập": "⚙",
};

const RAIL_KEY = "fk.sidebar.collapsed";

export default function ProjectWorkspace({
  project,
  setProject,
}: {
  // Dự án do App sở hữu — tên/khung hình/model hiển thị trên thanh trên cùng của app, nên
  // mọi thay đổi ở đây phải đẩy ngược lên qua setProject.
  project: Project;
  setProject: Dispatch<SetStateAction<Project>>;
}) {
  const [tab, setTab] = useState<Tab>("Script");
  // Keep-alive: render every tab we've visited and just hide the inactive ones, so a
  // long-running job (e.g. Storyboard auto-gen) and its progress survive tab switches.
  const [visited, setVisited] = useState<Set<Tab>>(() => new Set(["Script"]));
  useEffect(() => {
    setVisited((v) => (v.has(tab) ? v : new Set(v).add(tab)));
  }, [tab]);
  const [editor, setEditor] = useState<EditorTarget | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [reload, setReload] = useState(0);
  // Sidebar thu gọn thành dải icon — nhớ lựa chọn qua các phiên làm việc.
  const [railed, setRailed] = useState(() => localStorage.getItem(RAIL_KEY) === "1");
  useEffect(() => {
    localStorage.setItem(RAIL_KEY, railed ? "1" : "0");
  }, [railed]);

  const pid = project.id;

  // Fetch the full project (with script_raw) on open.
  useEffect(() => {
    api.getProject(pid).then(setProject).catch(() => {});
  }, [pid, setProject]);

  // (Re)load entities on open, every time the node editor opens, and after a node-apply
  // (reload bump). Regenerating an asset elsewhere changes its media_id/image_path, so the
  // "Nguồn ảnh" picker must refetch — otherwise it binds a stale snapshot and shows the old
  // image even though generation (which resolves entity_id live) uses the new one.
  useEffect(() => {
    api.listEntities(pid).then((r) => setEntities(r.entities)).catch(() => {});
  }, [pid, reload, editor]);

  const openEditor = (t: EditorTarget) => setEditor(t);

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
    {/* Không còn header riêng: danh tính dự án đã lên thanh trên cùng của app và ⚙ đã là
        một tab, nên toàn bộ chiều cao ở đây thuộc về sidebar + nội dung. */}
    <div className="flex h-full flex-col">
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
          {pane(
            "Thiết lập",
            <SettingsTab key={project.id} project={project} onSaved={setProject} />
          )}
        </div>
      </div>

      {editor && (
        <NodeEditor
          target={editor}
          entities={entities}
          projectId={project.id}
          videoModel={project.video_model}
          projectHeader={project.prompt_header}
          projectFooter={project.prompt_footer}
          onClose={() => setEditor(null)}
          onApplied={() => setReload((r) => r + 1)}
        />
      )}

      <JobProgress />
    </div>
    </JobsProvider>
  );
}
