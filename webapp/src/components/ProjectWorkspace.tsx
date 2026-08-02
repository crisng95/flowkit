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
      <div className="flex items-center gap-4 border-b border-neutral-800 px-6 py-3">
        <button
          onClick={onBack}
          className="rounded-lg px-2 py-1 text-sm text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
        >
          ← Dự án
        </button>
        <div className="min-w-0">
          <div className="truncate font-medium">{project.title}</div>
        </div>
        <nav className="mx-auto flex gap-1 rounded-xl bg-neutral-900 p-1">
          {TABS.map((t, i) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-lg px-3 py-1.5 text-sm transition ${
                tab === t
                  ? "bg-neutral-700 text-white"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              <span className="mr-1 text-neutral-500">{i + 1}.</span>
              {t}
            </button>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <span className="text-xs text-neutral-500">Style</span>
          <input
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            onBlur={saveStyle}
            className="w-44 rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500"
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

      <div className="flex-1 overflow-hidden">
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
