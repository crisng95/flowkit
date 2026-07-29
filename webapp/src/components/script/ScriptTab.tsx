import { useEffect, useRef, useState } from "react";
import { api, type Project, type Scene,
  type ScriptChanges,
} from "../../api/client";
import ScreenplayPreview from "./ScreenplayPreview";

export default function ScriptTab({
  project,
  onScriptChange,
}: {
  project: Project;
  onScriptChange?: (script: string) => void;
}) {
  const [script, setScript] = useState(project.script_raw ?? "");
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // "preview" = formatted screenplay page; "edit" = raw Fountain textarea.
  const [view, setView] = useState<"edit" | "preview">(
    (project.script_raw ?? "").trim() ? "preview" : "edit"
  );
  const taRef = useRef<HTMLTextAreaElement>(null);

  // Insert a Fountain screenplay element at the cursor (on its own line).
  const insertSnippet = (text: string) => {
    const ta = taRef.current;
    const start = ta ? ta.selectionStart : script.length;
    const end = ta ? ta.selectionEnd : script.length;
    const before = script.slice(0, start);
    const after = script.slice(end);
    const lead = before.length && !before.endsWith("\n") ? "\n" : "";
    const ins = lead + text;
    setScript(before + ins + after);
    setDirty(true);
    requestAnimationFrame(() => {
      const pos = (before + ins).length;
      ta?.focus();
      ta?.setSelectionRange(pos, pos);
    });
  };

  // Keep local state in sync if the parent project (script_raw) changes.
  useEffect(() => {
    setScript(project.script_raw ?? "");
    setDirty(false);
  }, [project.id, project.script_raw]);

  useEffect(() => {
    api.listScenes(project.id).then((r) => setScenes(r.scenes)).catch(() => {});
  }, [project.id]);

  const hasScript = script.trim().length > 0;

  // Lưu/sửa kịch bản giờ ĐỐI CHIẾU scene thay vì xoá sạch, nên phải nói rõ hệ quả: scene nào
  // đổi nội dung thì storyboard/lời đọc của nó đã CŨ (phải tách beat / vẽ lại), scene bị xoá
  // thì shot của nó cũng mất theo. Trước đây mọi thứ diễn ra âm thầm.
  const [changes, setChanges] = useState<ScriptChanges | null>(null);

  const onResult = (r: { script: string; scenes: Scene[]; changes?: ScriptChanges }) => {
    setScript(r.script);
    setScenes(r.scenes);
    setChanges(r.changes ?? null);
    setDirty(false);
    if (r.script.trim()) setView("preview"); // show the formatted page after AI writes/edits
    onScriptChange?.(r.script);
  };

  const wrap = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setErr(null);
    try {
      onResult(await fn());
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex h-full">
      {/* Main editor */}
      <div className="relative flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between gap-3 px-4 pt-4 pb-2">
          <span className="text-sm text-neutral-400">
            {hasScript
              ? `Screenplay (Fountain) · ${scenes.length} scene`
              : "Chưa có kịch bản"}
          </span>
          {hasScript && (
            <div className="flex items-center gap-2">
              {/* Xem (trang screenplay) ⇄ Sửa (Fountain thô) */}
              <div className="flex rounded-lg bg-neutral-900 p-0.5 text-xs">
                <button
                  onClick={() => setView("preview")}
                  className={`rounded-md px-2.5 py-1 transition ${
                    view === "preview" ? "bg-neutral-700 text-white" : "text-neutral-400 hover:text-neutral-200"
                  }`}
                >
                  📖 Xem
                </button>
                <button
                  onClick={() => setView("edit")}
                  className={`rounded-md px-2.5 py-1 transition ${
                    view === "edit" ? "bg-neutral-700 text-white" : "text-neutral-400 hover:text-neutral-200"
                  }`}
                >
                  ✏️ Sửa
                </button>
              </div>
              {view === "edit" && (
                <button
                  disabled={!dirty || !!busy}
                  onClick={() => wrap("save", () => api.saveScript(project.id, script))}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
                >
                  {busy === "save" ? "Đang lưu…" : dirty ? "Lưu" : "Đã lưu"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Screenplay toolbar — chèn phần tử Fountain chuẩn ngành tại con trỏ (chỉ khi Sửa) */}
        {view === "edit" && (
          <div className="flex flex-wrap gap-1 px-4 pb-2">
            <TBtn onClick={() => insertSnippet("INT. ĐỊA ĐIỂM - DAY\n")} title="Scene Heading (INT./EXT.)">🎬 Cảnh</TBtn>
            <TBtn onClick={() => insertSnippet("Mô tả hành động đang diễn ra.\n")} title="Action — dòng mô tả">Hành động</TBtn>
            <TBtn onClick={() => insertSnippet("TÊN NHÂN VẬT\n")} title="Character cue (in hoa)">👤 Nhân vật</TBtn>
            <TBtn onClick={() => insertSnippet("(diễn giải)\n")} title="Parenthetical">(Diễn giải)</TBtn>
            <TBtn onClick={() => insertSnippet("Lời thoại.\n")} title="Dialogue">💬 Thoại</TBtn>
            <TBtn onClick={() => insertSnippet("CUT TO:\n")} title="Transition (căn phải)">Chuyển →</TBtn>
          </div>
        )}

        {/* Script area — always scrollable; large bottom padding so the floating
            composer never hides the last lines of the screenplay. */}
        <div className="relative flex-1 px-4">
          {view === "preview" ? (
            <ScreenplayPreview script={script} />
          ) : (
            <textarea
              ref={taRef}
              value={script}
              onChange={(e) => {
                setScript(e.target.value);
                setDirty(true);
              }}
              spellCheck={false}
              placeholder={hasScript ? "" : "Kịch bản sẽ hiện ở đây. Nhập ý tưởng bên dưới để tạo…"}
              className="absolute inset-0 mx-4 resize-none overflow-auto rounded-xl border border-neutral-800 bg-neutral-950 p-4 font-mono text-[13px] leading-6 text-neutral-200 outline-none focus:border-indigo-500"
              style={{ fontFamily: '"Courier New", ui-monospace, monospace', paddingBottom: 180 }}
            />
          )}

          {/* Floating composer */}
          <Composer
            project={project}
            hasScript={hasScript}
            busy={busy}
            onGenerate={(idea, dur) =>
              wrap("gen", () => api.generateScript(project.id, idea, dur))
            }
            onChat={(instr) => wrap("chat", () => api.scriptChat(project.id, instr))}
          />
        </div>

        {changes && (changes.body_changed.length > 0 || changes.removed > 0 || changes.added > 0) && (

          <div className="mx-4 mb-2 rounded-lg bg-amber-950/40 px-3 py-2 text-xs text-amber-200">

            <b>Kịch bản đã đổi:</b>{" "}

            {changes.added > 0 && <>+{changes.added} cảnh mới. </>}

            {changes.removed > 0 && (

              <>Đã xoá {changes.removed} cảnh (kèm {changes.shots_removed} shot). </>

            )}

            {changes.body_changed.length > 0 && (

              <>

                {changes.body_changed.length} cảnh đổi nội dung — storyboard và lời đọc của

                chúng giờ đã CŨ, cần tách beat / vẽ lại ảnh:{" "}

                <span className="opacity-80">{changes.body_changed.slice(0, 3).join(" · ")}</span>

                {changes.body_changed.length > 3 && <> …+{changes.body_changed.length - 3}</>}

              </>

            )}

          </div>

        )}


        {err && (
          <div className="mx-8 mb-3 rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
            {err}
          </div>
        )}
      </div>

      {/* Scenes sidebar */}
      <aside className="hidden w-72 shrink-0 overflow-auto border-l border-neutral-800 p-3 lg:block">
        <h3 className="mb-2 px-1 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Scenes
        </h3>
        <div className="space-y-1.5">
          {scenes.map((s) => (
            <div
              key={s.id}
              className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-2.5"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs text-neutral-500">{String(s.idx + 1).padStart(2, "0")}</span>
                <span className="truncate text-sm font-medium text-neutral-200">
                  {s.heading}
                </span>
              </div>
              {s.action && (
                <p className="mt-1 line-clamp-2 text-xs text-neutral-500">{s.action}</p>
              )}
            </div>
          ))}
          {!scenes.length && (
            <p className="px-1 text-xs text-neutral-600">Chưa có scene.</p>
          )}
        </div>
      </aside>
    </div>
  );
}

// Floating bottom composer: switches between "idea → script" and "edit instruction".
function Composer({
  project,
  hasScript,
  busy,
  onGenerate,
  onChat,
}: {
  project: Project;
  hasScript: boolean;
  busy: string | null;
  onGenerate: (idea: string, dur: number | null) => void;
  onChat: (instr: string) => void;
}) {
  const [mode, setMode] = useState<"idea" | "edit">(hasScript ? "edit" : "idea");
  const [idea, setIdea] = useState(project.idea ?? "");
  const [useDur, setUseDur] = useState(!!project.target_duration);
  const [dur, setDur] = useState(project.target_duration ?? 60);
  const [instr, setInstr] = useState("");
  const editRef = useRef<HTMLInputElement>(null);

  // When the script first appears, default to edit mode.
  useEffect(() => {
    if (hasScript) setMode("edit");
  }, [hasScript]);

  const sendEdit = () => {
    if (!instr.trim() || busy) return;
    onChat(instr);
    setInstr("");
  };

  return (
    <div className="pointer-events-none absolute inset-x-7 bottom-4">
      <div className="pointer-events-auto rounded-2xl border border-neutral-700 bg-neutral-900/90 p-2.5 shadow-2xl backdrop-blur">
        {hasScript && (
          <div className="mb-2 flex gap-1">
            <Chip active={mode === "edit"} onClick={() => setMode("edit")}>✏️ Sửa</Chip>
            <Chip active={mode === "idea"} onClick={() => setMode("idea")}>✦ Tạo lại từ ý tưởng</Chip>
          </div>
        )}

        {mode === "idea" ? (
          <div className="space-y-2">
            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="Ý tưởng ngắn hoặc dán nội dung dài (vd: Sự tích cây khế)…"
              className="h-20 w-full resize-none rounded-xl border border-neutral-700 bg-neutral-950 p-3 text-sm outline-none focus:border-indigo-500"
            />
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-neutral-300">
                <input
                  type="checkbox"
                  checked={useDur}
                  onChange={(e) => setUseDur(e.target.checked)}
                  className="h-4 w-4 accent-indigo-500"
                />
                Thời lượng
              </label>
              {useDur ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    value={dur}
                    min={5}
                    onChange={(e) => setDur(parseInt(e.target.value) || 0)}
                    className="w-20 rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1 text-sm outline-none focus:border-indigo-500"
                  />
                  <span className="text-xs text-neutral-500">giây</span>
                </div>
              ) : (
                <span className="text-xs text-neutral-600">(không đặt → giữ đầy đủ nội dung)</span>
              )}
              <button
                disabled={busy === "gen" || !idea.trim()}
                onClick={() => onGenerate(idea, useDur ? dur : null)}
                className="ml-auto rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
              >
                {busy === "gen" ? "AI đang viết…" : "✦ Tạo kịch bản"}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              ref={editRef}
              value={instr}
              onChange={(e) => setInstr(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendEdit()}
              placeholder="Mô tả thay đổi, sửa cảnh, đổi lời thoại…"
              disabled={busy === "chat"}
              className="flex-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-indigo-500 placeholder:text-neutral-600"
            />
            <button
              onClick={sendEdit}
              disabled={busy === "chat" || !instr.trim()}
              className="grid h-9 w-9 place-items-center rounded-full bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40"
            >
              {busy === "chat" ? "…" : "→"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function TBtn({
  onClick,
  title,
  children,
}: {
  onClick: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="rounded-md border border-neutral-700 bg-neutral-900 px-2.5 py-1 text-xs text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100"
    >
      {children}
    </button>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-2.5 py-1 text-xs transition ${
        active ? "bg-indigo-600 text-white" : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
      }`}
    >
      {children}
    </button>
  );
}
