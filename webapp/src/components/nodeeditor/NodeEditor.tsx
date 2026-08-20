import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  NodeResizer,
  Position,
  addEdge,
  reconnectEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  MarkerType,
  SelectionMode,
  type Node,
  type Edge,
  type Connection,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, graphApi, storyboard, thumbUrl, type Entity, type GraphTemplate, type Shot } from "../../api/client";
import Lightbox from "../common/Lightbox";

// A picture the "Nguồn ảnh" node can reference: project assets (entities) AND every
// storyboard shot image — so any generated frame can feed back in as a reference.
export interface RefImage {
  key: string; // "e:<id>" | "s:<id>" | "m:<media_id>"
  kind: "entity" | "shot" | "media";
  label: string;
  media_id: string;
  web: string;
  entity_id?: string; // entities only — lets the source node refresh to the current art
}

export interface EditorTarget {
  kind: "shot" | "entity";
  id: string;
  title: string;
  // Chỉ với kind "entity": quyết định tỉ lệ khung của node tạo ảnh trong đồ thị mặc định —
  // người và đồ vật lấy khung DỌC, bối cảnh lấy khung NGANG. Xem _entity_aspect() bên agent.
  entityType?: string;
  // What this edit produces: an image (storyboard frame / asset art) or a video (shot).
  goal?: "image" | "video";
  prompt?: string | null;
  refEntityIds?: string[];
  imageMediaId?: string | null;
  imageSrc?: string | null;
  videoSrc?: string | null;
}

// ─── Node type metadata (icon / label / accent color) ───────
const META: Record<string, { label: string; icon: string; color: string }> = {
  source: { label: "Nguồn ảnh", icon: "🖼", color: "#f59e0b" },
  prompt: { label: "Prompt đầu vào", icon: "≣", color: "#3b82f6" },
  promptHeader: { label: "Prompt header", icon: "⤒", color: "#6366f1" },
  promptFooter: { label: "Prompt footer", icon: "⤓", color: "#6366f1" },
  refs: { label: "References", icon: "🔗", color: "#0ea5e9" },
  image: { label: "Tạo ảnh AI", icon: "🎨", color: "#a855f7" },
  editImage: { label: "Sửa ảnh AI", icon: "🖌", color: "#f59e0b" },
  removebg: { label: "Tách nền AI", icon: "✂", color: "#f43f5e" },
  replacebg: { label: "Thay nền (ảnh)", icon: "🏞", color: "#f43f5e" },
  filter: { label: "Filter ảnh", icon: "🎚", color: "#14b8a6" },
  colorgrade: { label: "Color grade", icon: "🎞", color: "#0d9488" },
  text: { label: "Chèn chữ", icon: "🔤", color: "#22c55e" },
  upscale: { label: "Upscale / nét", icon: "🔍", color: "#06b6d4" },
  crop: { label: "Crop / tỉ lệ", icon: "🖼", color: "#84cc16" },
  vignette: { label: "Vignette", icon: "🌑", color: "#8b5cf6" },
  border: { label: "Khung viền", icon: "🔲", color: "#eab308" },
  blend: { label: "Ghép / Blend", icon: "🔀", color: "#ec4899" },
  collage: { label: "Ghép lưới", icon: "▦", color: "#ec4899" },
  watermark: { label: "Watermark / Logo", icon: "💧", color: "#0ea5e9" },
  video: { label: "Tạo video AI", icon: "🎬", color: "#a855f7" },
  note: { label: "Ghi chú", icon: "📝", color: "#a3a3a3" },
  output: { label: "Output", icon: "📤", color: "#64748b" },
};

// "refs" intentionally dropped — use one "Nguồn ảnh" (source) node per reference image.
const PALETTE = ["source", "prompt", "promptHeader", "promptFooter", "image", "editImage", "removebg", "replacebg", "filter", "colorgrade", "text", "upscale", "crop", "vignette", "border", "blend", "collage", "watermark", "video", "note", "output"];

// ─── Handles ("định danh") ──────────────────────────────────
// Every node that PRODUCES a picture/clip carries a handle: writing "{handle}" in a
// downstream prompt turns that exact image into its own reference part of the request, so
// the model is told what ROLE the picture plays ("mặc {Áo khoác} cho {Nam}") instead of
// receiving an anonymous pile of reference images. Mirrors _handle_of() in agent/studio/graph.py.
const HANDLE_TYPES = new Set([
  "source", "image", "editImage", "removebg", "replacebg", "filter", "colorgrade",
  "text", "upscale", "crop", "vignette", "border", "blend", "collage", "watermark", "video",
]);

// Braces delimit the token in a prompt, so they can't appear inside a handle.
const cleanHandle = (s: string) => s.replace(/[{}\r\n]/g, "").replace(/\s+/g, " ").slice(0, 40);

// The handle used when the user hasn't typed one — must match the backend fallback.
const autoHandle = (type: string, d: any): string =>
  type === "source" ? (d?.label || "source") : type === "video" ? "video" : "image";

const effHandle = (type: string, d: any): string =>
  cleanHandle(String(d?.handle || "").trim()) || autoHandle(type, d);

// Every "định danh" already spoken for in the graph, lowercased.
const takenHandles = (ns: Node[]): Set<string> =>
  new Set(
    ns.filter((n) => HANDLE_TYPES.has(n.type || ""))
      .map((n) => effHandle(n.type!, n.data as any).toLowerCase())
  );

// "Áo khoác" → "Áo khoác 2" (…3, …) so a copy never shadows the original's token.
const freeHandle = (taken: Set<string>, base: string): string => {
  if (!taken.has(base.toLowerCase())) return cleanHandle(base);
  let k = 2;
  while (taken.has(`${base} ${k}`.toLowerCase())) k++;
  return cleanHandle(`${base} ${k}`);
};

// ─── Token {…} trong prompt ─────────────────────────────────
// `{tên}` là cú pháp DUY NHẤT Flow bind thành reference part (flow_client
// ._build_structured_parts): viết sai một chữ thì ảnh vẫn đi kèm request nhưng model không
// biết nó đóng vai gì, và kết quả trả về như một lượt sinh mới. Lẫn vào chữ thường thì không
// ai soi ra được, nên token được tô nền ngay trong ô nhập — xanh = có ảnh khớp tên, hổ phách
// = KHÔNG khớp gì cả (token chết, sẽ không bind).
type Tok = { start: number; end: number; name: string };

// Trả cả VỊ TRÍ vì lớp tô nền và thẻ sửa/xoá phải cắt đúng đoạn chữ trong textarea, không chỉ
// biết có những tên nào.
const tokensOf = (text: string): Tok[] =>
  Array.from(String(text || "").matchAll(/\{([^{}\n]*)\}/g)).map((m) => ({
    start: m.index!,
    end: m.index! + m[0].length,
    name: m[1].trim(),
  }));

const tokensIn = (text: string): string[] =>
  tokensOf(text).map((t) => t.name).filter(Boolean);

const prettyModel = (m: string) =>
  m.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

// Shared state for custom nodes (update fn + lookups). Avoids prop drilling into
// React Flow's nodeTypes (which must be stable module-level components).
const NodeOps = createContext<{
  update: (id: string, patch: any) => void;
  remove: (id: string) => void;
  duplicate: (id: string) => void;
  bindEntitySource: (fromId: string, entityId: string) => void;
  // Wire an already-placed node into whatever a prompt node feeds, so picking its {handle}
  // in that prompt actually delivers the picture to the generator.
  bindNodeSource: (fromId: string, nodeId: string) => void;
  preview: (src: string, video: boolean) => void;
  genNode: (id: string, propagate?: boolean) => void;
  genningId: string | null;
  results: Record<string, { web: string; ext: string }>;
  // Effective media currently flowing INTO each node id (from its upstream) — lets the
  // Output node mirror its input live, even after a single upstream node is regenerated.
  inputResults: Record<string, { web: string; ext: string }>;
  entities: Entity[];
  images: RefImage[];
  imageModels: string[];
  projectId: string;
  // Omni Flash clip length from ⚙ Cấu hình dự án (null = project uses Veo). A video node
  // without its own `duration` renders at this length.
  projDur: number | null;
  // prompt_header / prompt_footer của ⚙ Thiết lập dự án — node Prompt header/footer bỏ
  // trống thì chạy theo hai giá trị này (và hiện chúng làm placeholder).
  projectHeader: string;
  projectFooter: string;
  // Every image-producing node in the graph, by its effective handle — feeds the prompt
  // autocomplete and the "Ảnh gốc" picker.
  handles: { id: string; type: string; handle: string; web?: string }[];
  // Handles that are ambiguous: shared by 2+ nodes AND actually written as {token} in a
  // prompt, so the request really would bind the wrong picture.
  handleDupes: Set<string>;
  // Effective handles of the nodes feeding `id` directly.
  upstreamHandles: (id: string) => { id: string; handle: string }[];
}>({
  update: () => {},
  remove: () => {},
  duplicate: () => {},
  bindEntitySource: () => {},
  bindNodeSource: () => {},
  preview: () => {},
  genNode: () => {},
  genningId: null,
  results: {},
  inputResults: {},
  entities: [],
  images: [],
  imageModels: [],
  projectId: "",
  projDur: null,
  projectHeader: "",
  projectFooter: "",
  handles: [],
  handleDupes: new Set(),
  upstreamHandles: () => [],
});

const handleStyle = (color: string) => ({
  width: 18,
  height: 18,
  background: color,
  border: "3px solid #0e1411",
  boxShadow: "0 0 0 1px rgba(255,255,255,0.15)",
});

// Bề ngang mặc định của mọi node. Node kéo giãn được ghi đè bằng `data.w`.
const NODE_W = 228;

/**
 * Tay kéo giãn cho các node chứa prompt dài.
 *
 * Kích thước ghi vào `data.w/h` chứ KHÔNG để React Flow giữ ở `node.width/height`:
 * `serializeGraph` chỉ lưu `{id, type, data, position}`, nên cỡ nằm ngoài `data` là mất
 * sạch sau mỗi lần lưu/mở lại đồ thị.
 *
 * Đặt NGOÀI `Shell` (anh em, không phải con) vì Shell bật `overflow-hidden` khi node không
 * mở menu — nằm trong thì bốn vạch kéo bị cắt mất.
 */
function SizeGrip({ id, visible, minH }: { id: string; visible: boolean; minH: number }) {
  const { update } = useContext(NodeOps);
  return (
    <NodeResizer
      isVisible={visible}
      minWidth={NODE_W}
      minHeight={minH}
      lineClassName="!border-indigo-400/70"
      handleClassName="!h-2.5 !w-2.5 !rounded-sm !border-indigo-300 !bg-indigo-500"
      onResize={(_, p) => update(id, { w: Math.round(p.width), h: Math.round(p.height) })}
    />
  );
}

// The node's "định danh": the token a downstream prompt uses to give this picture a role.
// Left blank it falls back to `autoHandle` (shown as the placeholder), which is what the
// backend does too — so an untouched graph behaves exactly as before.
function HandleField({ id, type, data }: { id: string; type: string; data: any }) {
  const { update, handleDupes } = useContext(NodeOps);
  // Local state for the same reason PromptNode keeps one: writing straight to node data
  // round-trips through React Flow's store, which reverts the value for a frame and jumps
  // the caret to the end. An external change (auto-fill on picking an asset) still adopts.
  const [typed, setTyped] = useState<string>(data.handle ?? "");
  const pushed = useRef<string>(data.handle ?? "");
  useEffect(() => {
    const incoming = data.handle ?? "";
    if (incoming !== pushed.current) {
      setTyped(incoming);
      pushed.current = incoming;
    }
  }, [data.handle]);
  const onType = (v: string) => {
    const c = cleanHandle(v);
    setTyped(c);
    pushed.current = c;
    update(id, { handle: c });
  };
  const auto = autoHandle(type, data);
  const eff = typed.trim() || auto;
  const dup = handleDupes.has(eff.toLowerCase());
  return (
    <div className="px-3 pb-2">
      <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">
        Định danh — gõ trong prompt
      </div>
      <div
        className={`flex items-center rounded-md border bg-indigo-950/30 px-1.5 ${
          dup ? "border-amber-500/70" : "border-indigo-700/50"
        }`}
        title="Gõ {tên này} trong prompt của node tạo/sửa ảnh để chỉ đích danh ảnh này"
      >
        <span className="select-none text-[12px] font-semibold text-indigo-400">{"{"}</span>
        <input
          value={typed}
          // The fallback name is what generation ACTUALLY uses when the box is empty, so it's
          // shown as bright as a typed value (just italic) — a dim placeholder would read as
          // "no name yet" and hide the very token the user needs to type.
          placeholder={auto}
          onChange={(e) => onType(e.target.value)}
          className="nodrag min-w-0 flex-1 bg-transparent px-1 py-1 text-[12px] font-semibold text-indigo-200 outline-none placeholder:font-normal placeholder:italic placeholder:text-indigo-300/70"
        />
        <span className="select-none text-[12px] font-semibold text-indigo-400">{"}"}</span>
      </div>
      {dup && (
        <div className="mt-0.5 text-[10px] text-amber-400">
          ⚠ Trùng định danh — prompt sẽ không rõ dùng ảnh nào
        </div>
      )}
    </div>
  );
}

function Shell({
  type,
  id,
  data,
  children,
  inputs = true,
  outputs = true,
  clip = true,
  width,
  height,
}: {
  type: string;
  id?: string;
  data?: any;
  children: React.ReactNode;
  inputs?: boolean;
  outputs?: boolean;
  // Nodes that pop a menu out past their own edge (the prompt autocomplete) must not clip,
  // otherwise the list is sliced off at the node border and only its first row shows.
  clip?: boolean;
  // Node kéo giãn được truyền kích thước vào đây (px). Có `height` thì thân node chuyển sang
  // flex dọc để ô nội dung ăn hết chỗ thừa — không thì kéo cao ra chỉ được khoảng trống.
  width?: number;
  height?: number;
}) {
  const { remove, duplicate } = useContext(NodeOps);
  const m = META[type] || META.output;
  return (
    <div
      className={`rounded-xl border border-neutral-700/80 bg-[#0e1411] shadow-xl ${
        clip ? "overflow-hidden" : ""
      } ${height ? "flex flex-col" : ""}`}
      style={{ borderTopColor: m.color, borderTopWidth: 3, width: width ?? NODE_W, height }}
    >
      <div className="flex items-center gap-2 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-300">
        <span style={{ color: m.color }}>{m.icon}</span>
        <span className="truncate">{m.label}</span>
        {id && (
          <span className="ml-auto flex items-center gap-1">
            <button
              onClick={() => duplicate(id)}
              title="Nhân bản node"
              className="nodrag grid h-5 w-5 place-items-center rounded text-neutral-500 hover:bg-neutral-700 hover:text-white"
            >
              ⧉
            </button>
            <button
              onClick={() => remove(id)}
              title="Xóa node"
              className="nodrag grid h-5 w-5 place-items-center rounded text-neutral-500 hover:bg-rose-600/80 hover:text-white"
            >
              ✕
            </button>
          </span>
        )}
      </div>
      {id && data && HANDLE_TYPES.has(type) && <HandleField id={id} type={type} data={data} />}
      <div className={`space-y-2 px-3 pb-3 ${height ? "flex min-h-0 flex-1 flex-col" : ""}`}>
        {children}
      </div>
      {inputs && <Handle type="target" position={Position.Left} style={handleStyle(m.color)} />}
      {outputs && <Handle type="source" position={Position.Right} style={handleStyle(m.color)} />}
    </div>
  );
}

const fieldCls =
  "nodrag w-full rounded-md border border-neutral-700 bg-neutral-900 px-2 py-1 text-[11px] text-neutral-200 outline-none focus:border-indigo-500";

// ─── Right-click menu styling ───────────────────────────────
const menuItemCls =
  "flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-[11px] text-neutral-200 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent";
const menuDangerCls =
  "flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-[11px] text-rose-300 hover:bg-rose-950/50";
const menuHeadCls =
  "truncate px-3 py-1.5 text-[10px] uppercase tracking-wide text-neutral-500";
const menuSepCls = "my-1 border-t border-neutral-800";
const menuKeyCls = "ml-auto pl-3 text-[10px] text-neutral-500";

function Preview({
  nodeId,
  src,
  video,
  label,
}: {
  nodeId?: string;
  src?: string;
  video?: boolean;
  label: string;
}) {
  const { results, preview } = useContext(NodeOps);
  // A run result (kept in a separate map keyed by node id) survives graph reloads and
  // wins over the seeded/transient src.
  const run = nodeId ? results[nodeId] : undefined;
  const effSrc = run?.web || src;
  const isVideo = run ? run.ext === "mp4" : !!video;
  if (!effSrc)
    return (
      <div className="grid aspect-video w-full place-items-center rounded-md bg-neutral-800/70 text-[11px] text-neutral-500">
        {label}
      </div>
    );
  const open = () => preview(effSrc, isVideo);
  return isVideo ? (
    <div className="relative">
      <video key={effSrc} src={effSrc} controls className="aspect-video w-full rounded-md bg-black object-cover" />
      <button
        onClick={open}
        title="Phóng to"
        className="nodrag absolute right-1 top-1 grid h-6 w-6 place-items-center rounded bg-black/60 text-xs text-white hover:bg-black/80"
      >
        ⛶
      </button>
    </div>
  ) : (
    <img
      key={effSrc}
      src={effSrc}
      onClick={open}
      title="Phóng to"
      className="nodrag aspect-video w-full cursor-zoom-in rounded-md object-cover"
    />
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-[10px] uppercase tracking-wide text-neutral-500">
        <span>{label}</span>
        <span className="text-neutral-300">{value}{suffix}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="nodrag h-1 w-full cursor-pointer accent-indigo-500"
      />
    </div>
  );
}

// A row of compact on/off chips bound to boolean node-data keys.
function ToggleChips({
  id,
  data,
  items,
}: {
  id: string;
  data: any;
  items: { key: string; label: string }[];
}) {
  const { update } = useContext(NodeOps);
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((it) => {
        const on = !!data[it.key];
        return (
          <button
            key={it.key}
            onClick={() => update(id, { [it.key]: !on })}
            className={`nodrag rounded px-1.5 py-0.5 text-[10px] ${
              on ? "bg-indigo-600 text-white" : "border border-neutral-700 text-neutral-400 hover:bg-neutral-800"
            }`}
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

// ─── Node components ────────────────────────────────────────
function SourceNode({ id, data }: NodeProps) {
  const { update, images, projectId } = useContext(NodeOps);
  const d = data as any;
  const [uploading, setUploading] = useState(false);
  const [upErr, setUpErr] = useState<string | null>(null);
  const pick = (key: string) => {
    const img = images.find((x) => x.key === key);
    if (img)
      update(id, {
        src_key: img.key,
        entity_id: img.entity_id || null,
        media_id: img.media_id,
        web: img.web,
        label: img.label,
        // An asset carries a name worth using as the token; a storyboard frame's label is a
        // code like "SC001-S001-…" that reads badly in a prompt, so leave those blank and let
        // the user name the role. Never clobber a handle the user typed.
        ...(d.handle ? {} : { handle: img.kind === "entity" ? img.label : "" }),
      });
  };
  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-picking the same file
    if (!file) return;
    setUploading(true);
    setUpErr(null);
    try {
      const r = await api.uploadImage(projectId, file);
      update(id, {
        src_key: "",
        entity_id: null,
        media_id: r.media_id,
        web: r.web,
        label: r.name || "ảnh tải lên",
      });
    } catch (err: any) {
      setUpErr(err.message || "Upload lỗi");
    } finally {
      setUploading(false);
    }
  };
  const entImgs = images.filter((x) => x.kind === "entity");
  const shotImgs = images.filter((x) => x.kind === "shot");
  const mediaImgs = images.filter((x) => x.kind === "media");
  const selected = d.src_key || (d.entity_id ? `e:${d.entity_id}` : "");
  // A bound entity's image can be regenerated after this node was created, leaving d.web a
  // stale snapshot. Prefer the live URL from the (refetched) reference list so the preview
  // tracks the current asset image — matching what generation (entity_id → live) uses.
  const live = d.entity_id ? images.find((x) => x.entity_id === d.entity_id) : undefined;
  const displaySrc = live?.web || d.web;
  return (
    <Shell type="source" id={id} data={d} inputs={false}>
      <Preview nodeId={id} src={displaySrc} label="Chọn / tải ảnh" />
      <select className={fieldCls} value={selected} onChange={(e) => pick(e.target.value)}>
        <option value="">{d.web ? "(ảnh hiện tại)" : "— chọn ảnh —"}</option>
        {entImgs.length > 0 && (
          <optgroup label="Ảnh asset">
            {entImgs.map((x) => (
              <option key={x.key} value={x.key}>{x.label}</option>
            ))}
          </optgroup>
        )}
        {shotImgs.length > 0 && (
          <optgroup label="Ảnh storyboard">
            {shotImgs.map((x) => (
              <option key={x.key} value={x.key}>{x.label}</option>
            ))}
          </optgroup>
        )}
        {mediaImgs.length > 0 && (
          <optgroup label="Ảnh khác trong dự án">
            {mediaImgs.map((x) => (
              <option key={x.key} value={x.key}>{x.label}</option>
            ))}
          </optgroup>
        )}
      </select>
      <label className="nodrag block cursor-pointer rounded-md border border-dashed border-neutral-700 px-2 py-1 text-center text-[10px] text-neutral-400 hover:bg-neutral-800">
        {uploading ? "Đang tải lên…" : "⬆ Tải ảnh từ máy"}
        <input type="file" accept="image/*" className="hidden" disabled={uploading} onChange={onUpload} />
      </label>
      {upErr && <div className="text-[10px] text-rose-400">{upErr}</div>}
      {d.label && <div className="truncate text-[10px] text-neutral-500">↳ {d.label}</div>}
    </Shell>
  );
}

function PromptNode({ id, data, selected }: NodeProps) {
  const { update, entities, bindEntitySource, bindNodeSource, handles } = useContext(NodeOps);
  const d = data as any;
  // Kéo giãn được: prompt shot dài vài đoạn, xem qua khe 228×96 thì phải cuộn mò từng dòng.
  const grown = !!d.h;
  // Local state for the textarea so typing updates synchronously and the caret stays put.
  // Binding `value` straight to node data round-trips through React Flow's store, which
  // reverts the value for a frame on each keystroke and jumps the cursor to the end.
  // We still adopt an external change (re-seed / "Đa dạng góc máy") via the effect below,
  // distinguished from our own edits by `lastPushed`.
  const [text, setText] = useState<string>(d.text ?? "");
  const lastPushed = useRef<string>(d.text ?? "");
  const taRef = useRef<HTMLTextAreaElement | null>(null);
  const caretRef = useRef<number | null>(null); // caret to restore after a programmatic insert
  // Entity autocomplete: open when the caret sits inside an unclosed "{…".
  const [menu, setMenu] = useState<{ start: number; query: string } | null>(null);
  const [hi, setHi] = useState(0);
  // Token người dùng vừa BẤM vào (không phải mọi lần con trỏ đi qua) → mở thẻ sửa/xoá.
  const [picked, setPicked] = useState<number | null>(null);
  // Textarea cuộn được (h-24) nên lớp nền phải cuộn theo, không thì nền lệch khỏi chữ.
  const [scrollTop, setScrollTop] = useState(0);

  useEffect(() => {
    const incoming = d.text ?? "";
    if (incoming !== lastPushed.current) {
      setText(incoming);
      lastPushed.current = incoming;
    }
  }, [d.text]);

  useLayoutEffect(() => {
    if (caretRef.current != null && taRef.current) {
      taRef.current.selectionStart = taRef.current.selectionEnd = caretRef.current;
      caretRef.current = null;
    }
  });

  // The "{…" being typed right before the caret (no closing "}" / newline in between), else null.
  const detect = (val: string, caret: number) => {
    const before = val.slice(0, caret);
    const brace = before.lastIndexOf("{");
    if (brace < 0) return null;
    const between = before.slice(brace + 1);
    if (/[}{\n]/.test(between)) return null;
    return { start: brace, query: between };
  };

  const setAll = (v: string) => {
    setText(v);
    lastPushed.current = v;
    update(id, { text: v });
  };

  const onChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value;
    setAll(v);
    setMenu(entities.length || handles.length ? detect(v, e.target.selectionStart ?? v.length) : null);
    setHi(0);
    setPicked(null);      // đang gõ thì đóng thẻ, khỏi nhảy ra chắn chữ
  };

  // Suggestions = every picture already wired into this graph (by its "định danh"), then any
  // project asset not yet on the canvas. Picking either inserts "{token}" AND makes sure the
  // picture reaches the generator, so the mention actually binds to an image.
  type Sugg = { token: string; sub: string; nodeId?: string; entityId?: string; web?: string };
  const allSugg = useMemo<Sugg[]>(() => {
    const out: Sugg[] = [];
    const seen = new Set<string>();
    for (const h of handles) {
      if (h.id === id || seen.has(h.handle.toLowerCase())) continue;
      seen.add(h.handle.toLowerCase());
      out.push({ token: h.handle, sub: META[h.type]?.label || h.type, nodeId: h.id, web: h.web });
    }
    for (const e of entities) {
      if (!e.media_id || seen.has(e.name.toLowerCase())) continue;
      seen.add(e.name.toLowerCase());
      out.push({ token: e.name, sub: "Asset — thêm Nguồn ảnh", entityId: e.id,
                 web: e.image_path || undefined });
    }
    return out;
  }, [entities, handles, id]);

  const matches = useMemo<Sugg[]>(() => {
    if (!menu) return [];
    const q = menu.query.trim().toLowerCase();
    return allSugg.filter((s) => !q || s.token.toLowerCase().includes(q)).slice(0, 8);
  }, [menu, allSugg]);

  // Chỉ tính node ẢNH đang có trên canvas, KHÔNG tính asset của dự án chưa được kéo vào:
  // asset chưa có node thì chẳng có ảnh nào đi kèm request, token gọi tên nó vẫn là chữ chết.
  // Chọn nó trong thẻ sẽ tự thêm Nguồn ảnh (bindEntitySource) rồi mới xanh.
  const knownNames = useMemo(
    () => new Set(handles.filter((h) => h.id !== id).map((h) => h.handle.trim().toLowerCase())),
    [handles, id]
  );
  const toks = useMemo(() => tokensOf(text), [text]);
  // Token đang mở thẻ, tra lại theo vị trí mở đầu để nó tự biến mất khi text đổi.
  const active = picked == null ? null : toks.find((t) => t.start === picked) ?? null;

  // Replace the "{query" with "{token}" and drop the caret after "}".
  const pick = (s: Sugg) => {
    if (!menu) return;
    const caret = taRef.current?.selectionStart ?? text.length;
    const next = text.slice(0, menu.start) + "{" + s.token + "}" + text.slice(caret);
    setAll(next);
    caretRef.current = menu.start + s.token.length + 2;
    setMenu(null);
    if (s.entityId) bindEntitySource(id, s.entityId);
    else if (s.nodeId) bindNodeSource(id, s.nodeId);
    requestAnimationFrame(() => taRef.current?.focus());
  };

  // Thay token đang chọn bằng entity khác (s) hoặc xoá hẳn (s = null). Vẫn là sửa CHỮ trong
  // textarea nên gõ tay `{}` trực tiếp lúc nào cũng được — thẻ chỉ là lối tắt.
  const replaceToken = (t: Tok, s: Sugg | null) => {
    const next = s
      ? text.slice(0, t.start) + "{" + s.token + "}" + text.slice(t.end)
      : text.slice(0, t.start) + text.slice(t.end);
    setAll(next);
    caretRef.current = s ? t.start + s.token.length + 2 : t.start;
    setPicked(null);
    if (s?.entityId) bindEntitySource(id, s.entityId);
    else if (s?.nodeId) bindNodeSource(id, s.nodeId);
    requestAnimationFrame(() => taRef.current?.focus());
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (picked != null && e.key === "Escape") { e.preventDefault(); setPicked(null); return; }
    if (!menu || !matches.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => (h + 1) % matches.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => (h - 1 + matches.length) % matches.length); }
    else if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); pick(matches[hi]); }
    else if (e.key === "Escape") { e.preventDefault(); setMenu(null); }
  };

  return (
    <>
      <SizeGrip id={id} visible={!!selected} minH={160} />
      <Shell type="prompt" id={id} inputs={false} clip={!menu && !active} width={d.w} height={d.h}>
      <div className={`relative ${grown ? "flex min-h-0 flex-1 flex-col" : ""}`}>
        {/* Lớp nền: cùng hộp, cùng font, cùng cách xuống dòng với textarea, nhưng CHỮ TRONG
            SUỐT — chỉ vẽ nền cho token. Chữ thật vẫn là của textarea nằm trên (nền của nó đặt
            trong suốt bằng style inline, vì fieldCls cũng có bg-neutral-900 và hai class cùng
            độ ưu tiên thì thứ tự trong stylesheet quyết định chứ không phải thứ tự viết), nên
            con trỏ, bôi đen, undo và gõ IME tiếng Việt không bị đụng tới. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 overflow-hidden rounded-md border border-transparent bg-neutral-900 px-2 py-1 text-[11px] leading-snug"
          // Chừa sẵn máng thanh cuộn ở CẢ HAI lớp: prompt dài làm textarea mọc thanh cuộn,
          // bề rộng chữ hẹp lại, và nếu lớp nền không hẹp theo thì nền lệch khỏi token.
          style={{ scrollbarGutter: "stable" }}
        >
          <div
            className="whitespace-pre-wrap break-words text-transparent"
            style={{ transform: `translateY(${-scrollTop}px)` }}
          >
            {toks.length === 0
              ? text
              : (() => {
                  const segs: React.ReactNode[] = [];
                  let pos = 0;
                  toks.forEach((t, i) => {
                    if (t.start > pos) segs.push(<span key={`p${i}`}>{text.slice(pos, t.start)}</span>);
                    const ok = knownNames.has(t.name.toLowerCase());
                    segs.push(
                      <span
                        key={`t${i}`}
                        className={`rounded-[3px] ring-1 ${
                          ok
                            ? "bg-indigo-500/25 ring-indigo-400/40"
                            : "bg-amber-500/20 ring-amber-400/40"
                        } ${active?.start === t.start ? "ring-2 ring-indigo-300" : ""}`}
                      >
                        {text.slice(t.start, t.end)}
                      </span>
                    );
                    pos = t.end;
                  });
                  segs.push(<span key="tail">{text.slice(pos)}</span>);
                  return segs;
                })()}
          </div>
        </div>
        <textarea
          ref={taRef}
          className={`${fieldCls} nowheel relative resize-none leading-snug ${
            grown ? "min-h-0 flex-1" : "h-24"
          }`}
          style={{ backgroundColor: "transparent", scrollbarGutter: "stable" }}
          value={text}
          placeholder="Nhập prompt…"
          onChange={onChange}
          onKeyDown={onKeyDown}
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
          onClick={(e) => {
            // Bấm TRÚNG một token mới mở thẻ — không mở theo mọi lần con trỏ đi qua, vì
            // gõ giữa token là chuyện thường và popup nhảy ra sẽ rất phiền.
            const c = e.currentTarget.selectionStart ?? 0;
            const t = tokensOf(text).find((x) => c > x.start && c < x.end);
            setPicked(t ? t.start : null);
          }}
          onBlur={() => setTimeout(() => { setMenu(null); setPicked(null); }, 150)}
        />
        {menu && matches.length > 0 && (
          // Wider than the 228px node so a name + its source type fit on one line, and tall
          // enough for the full 8 suggestions instead of scrolling one row at a time.
          <div className="nodrag nowheel absolute left-0 top-full z-[60] mt-1 max-h-72 w-[288px] overflow-auto rounded-md border border-neutral-600 bg-neutral-900 shadow-2xl">
            {matches.map((s, i) => (
              <button
                key={s.nodeId || s.entityId}
                type="button"
                onMouseDown={(ev) => { ev.preventDefault(); pick(s); }}
                className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-[11px] ${
                  i === hi ? "bg-indigo-600 text-white" : "text-neutral-300 hover:bg-neutral-800"
                }`}
              >
                {s.web ? (
                  <img src={s.web} className="h-7 w-7 shrink-0 rounded object-cover" />
                ) : (
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded bg-neutral-800 text-neutral-500">
                    🖼
                  </span>
                )}
                <span className="truncate">{s.token}</span>
                <span className="ml-auto shrink-0 pl-1 text-[9px] uppercase tracking-wide opacity-60">
                  {s.sub}
                </span>
              </button>
            ))}
          </div>
        )}
        {active && !menu && (
          <div className="nodrag nowheel absolute left-0 top-full z-[60] mt-1 w-[288px] overflow-hidden rounded-md border border-neutral-600 bg-neutral-900 shadow-2xl">
            <div className="flex items-center gap-1.5 border-b border-neutral-800 px-2 py-1.5">
              <span
                className={`truncate rounded px-1 text-[11px] ${
                  knownNames.has(active.name.toLowerCase())
                    ? "bg-indigo-500/25 text-indigo-200"
                    : "bg-amber-500/20 text-amber-200"
                }`}
              >
                {"{" + active.name + "}"}
              </span>
              <button
                type="button"
                onMouseDown={(ev) => { ev.preventDefault(); replaceToken(active, null); }}
                title="Xoá token này khỏi prompt"
                className="ml-auto shrink-0 rounded px-1.5 py-0.5 text-[11px] text-rose-300 hover:bg-rose-950/50"
              >
                ✕ Xoá
              </button>
            </div>
            {!knownNames.has(active.name.toLowerCase()) && (
              <p className="border-b border-neutral-800 px-2 py-1.5 text-[10px] text-amber-300/90">
                Chưa có node ảnh nào trên canvas mang tên này — token sẽ KHÔNG gắn được ảnh,
                model chỉ đọc nó như chữ thường. Chọn một ảnh bên dưới (asset sẽ tự được thêm
                thành Nguồn ảnh).
              </p>
            )}
            <div className="max-h-56 overflow-auto">
              {allSugg.length === 0 && (
                <p className="px-2 py-2 text-[11px] text-neutral-500">Chưa có ảnh nào để chọn.</p>
              )}
              {allSugg.map((s) => (
                <button
                  key={s.nodeId || s.entityId}
                  type="button"
                  onMouseDown={(ev) => { ev.preventDefault(); replaceToken(active, s); }}
                  className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-[11px] ${
                    s.token.trim().toLowerCase() === active.name.toLowerCase()
                      ? "bg-neutral-800 text-white"
                      : "text-neutral-300 hover:bg-neutral-800"
                  }`}
                >
                  {s.web ? (
                    <img src={s.web} className="h-7 w-7 shrink-0 rounded object-cover" />
                  ) : (
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded bg-neutral-800 text-neutral-500">
                      🖼
                    </span>
                  )}
                  <span className="truncate">{s.token}</span>
                  <span className="ml-auto shrink-0 pl-1 text-[9px] uppercase tracking-wide opacity-60">
                    {s.sub}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="shrink-0 text-[10px] text-neutral-500">
        {'ⓘ gõ "{" để gọi đích danh một ảnh (định danh); bấm vào token đã tô nền để đổi ảnh hoặc xoá'}
      </div>
      </Shell>
    </>
  );
}

function RefsNode({ id, data }: NodeProps) {
  const { update, entities } = useContext(NodeOps);
  const ids: string[] = (data as any).entity_ids || [];
  const toggle = (eid: string) =>
    update(id, {
      entity_ids: ids.includes(eid) ? ids.filter((x) => x !== eid) : [...ids, eid],
    });
  return (
    <Shell type="refs" id={id} inputs={false}>
      <div className="nodrag nowheel max-h-36 space-y-0.5 overflow-auto">
        {entities.length === 0 && <p className="text-[11px] text-neutral-600">Chưa có asset.</p>}
        {entities.map((e) => (
          <label key={e.id} className="flex items-center gap-1.5 rounded px-1 py-0.5 text-[11px] hover:bg-neutral-800">
            <input type="checkbox" checked={ids.includes(e.id)} onChange={() => toggle(e.id)} className="h-3 w-3 accent-indigo-500" />
            <span className={`h-1.5 w-1.5 rounded-full ${e.media_id ? "bg-emerald-400" : "bg-neutral-600"}`} />
            <span className="truncate text-neutral-300">{e.name}</span>
          </label>
        ))}
      </div>
    </Shell>
  );
}

function AspectModelRow({
  id,
  data,
  models,
  videoModels,
}: {
  id: string;
  data: any;
  models?: string[];
  videoModels?: boolean;
}) {
  const { update } = useContext(NodeOps);
  const aspects = videoModels ? ["16:9", "9:16"] : ["16:9", "9:16", "1:1"];
  return (
    <div className="flex gap-2">
      <label className="flex-1">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Tỷ lệ</div>
        <select className={fieldCls} value={data.aspect || "16:9"} onChange={(e) => update(id, { aspect: e.target.value })}>
          {aspects.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </label>
      <label className="flex-1">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Model</div>
        {videoModels ? (
          <select className={fieldCls} value={data.model || "veo_lite"} onChange={(e) => update(id, { model: e.target.value })}>
            {/* [Lower Priority] = bản 0 credit. "Veo 3.1 - Lite" thường vẫn tính tiền. */}
            <option value="veo_lite">Veo 3.1 Lite ⚡0đ</option>
            <option value="omni">Omni Flash</option>
            <option value="veo">Veo i2v</option>
          </select>
        ) : (
          <select className={fieldCls} value={data.model || ""} onChange={(e) => update(id, { model: e.target.value })}>
            <option value="">Mặc định</option>
            {(models || []).map((m) => <option key={m} value={m}>{prettyModel(m)}</option>)}
          </select>
        )}
      </label>
    </div>
  );
}

// Per-node "tạo nhanh" (generate just this node) + lock (don't regenerate on full run).
function GenControls({ id, data }: { id: string; data: any }) {
  const { genNode, genningId, update } = useContext(NodeOps);
  const busy = genningId === id;
  const locked = !!data.locked;
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5">
        {/* Khoá chặn cả ⚡: bấm mà node vẫn giữ ảnh cũ thì trông như nút hỏng, nên tắt hẳn
            và nói rõ lý do. ⏬ vẫn bật — nó giữ node này và làm mới các node phía sau. */}
        <button
          onClick={() => genNode(id)}
          disabled={!!genningId || locked}
          title={locked
            ? "Đang khóa — mở khóa 🔒 mới tạo lại được node này"
            : "Tạo riêng node này (không chạy node phía sau)"}
          className="nodrag flex-1 rounded-md bg-indigo-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
        >
          {busy ? "Đang tạo…" : "⚡ Tạo nhanh"}
        </button>
        <button
          onClick={() => genNode(id, true)}
          disabled={!!genningId}
          title="Tạo node này RỒI cập nhật mọi node phía sau (xuôi dòng) — chuỗi luôn đồng bộ"
          className="nodrag grid h-[26px] w-7 place-items-center rounded-md border border-sky-600 text-xs text-sky-300 hover:bg-sky-950/40 disabled:opacity-40"
        >
          ⏬
        </button>
        <button
          onClick={() => update(id, { locked: !locked })}
          title={locked
            ? "Đang khóa — bỏ khóa để cho phép tạo lại"
            : "Khóa: không tạo lại node này, dù chạy toàn tuyến, ⚡ tạo nhanh, hay ⚡ từ thẻ shot"}
          className={`nodrag grid h-[26px] w-7 place-items-center rounded-md border text-xs ${
            locked
              ? "border-amber-500 bg-amber-500/20 text-amber-300"
              : "border-neutral-700 text-neutral-400 hover:bg-neutral-800"
          }`}
        >
          {locked ? "🔒" : "🔓"}
        </button>
      </div>
      {locked && (
        <div className="text-[10px] text-amber-400/90">
          Đã khóa — giữ nguyên ảnh này cho mọi lượt chạy (toàn tuyến, ⚡, và ⚡ từ thẻ shot)
        </div>
      )}
    </div>
  );
}

function ImageNode({ id, data, type }: NodeProps) {
  const { update, imageModels, upstreamHandles } = useContext(NodeOps);
  const d = data as any;
  const isEdit = (type || "image") === "editImage";
  // "Sửa ảnh" has two distinct roles for its inputs: ONE picture is the base being edited,
  // the rest are references the prompt addresses by {handle}. Without saying which is which
  // the base was just "whichever edge happened to be last".
  const ups = isEdit ? upstreamHandles(id) : [];
  return (
    <Shell type={type || "image"} id={id} data={d}>
      <Preview nodeId={id} src={d._result || d.preview} label="Kết quả ảnh" />
      {isEdit && (
        <label className="block">
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Ảnh gốc (được sửa)</div>
          <select className={fieldCls} value={d.base_handle || ""} onChange={(e) => update(id, { base_handle: e.target.value })}>
            <option value="">Tự động (ảnh nối cuối)</option>
            {ups.map((u) => (
              <option key={u.id} value={u.handle}>{u.handle}</option>
            ))}
          </select>
        </label>
      )}
      <AspectModelRow id={id} data={d} models={imageModels} />
      <Slider label="Số lượng tạo" value={d.count || 1} min={1} max={4} step={1} onChange={(v) => update(id, { count: v })} />
      {isEdit && ups.length > 1 && (
        <div className="text-[10px] text-neutral-500">
          ⓘ ảnh nối vào khác: gọi bằng {"{định danh}"} trong prompt
        </div>
      )}
      {/* Sửa ảnh đi thẳng vào Flow, không qua compose_prompt của dự án — nói rõ để khỏi
          tưởng style/culture vẫn được áp như node Tạo ảnh. */}
      {/* Cảnh báo "viết prompt bằng tiếng Anh" nằm trong tooltip chứ không chiếm chỗ trên
          canvas — node sửa ảnh vốn đã cao vì có thêm ô chọn ảnh gốc. */}
      {isEdit && (
        <div
          className="text-[10px] text-neutral-500"
          title={
            "Prompt dùng nguyên văn — không áp style/culture/header/footer dự án.\n\n" +
            "Viết bằng TIẾNG ANH, mô tả KẾT QUẢ muốn có: Flow dịch prompt tiếng Việt và đánh " +
            "rơi câu phủ định — “xoá bỏ người và xe” bị đổi thành mô tả một con phố đông đúc " +
            "rồi model vẽ THÊM người.\n\n" +
            "Câu xoá vật thể ra kết quả khác nhau mỗi lần chạy (seed ngẫu nhiên). Tăng “Số " +
            "lượng tạo” lên 2-4 rồi chọn bản sạch nhất thay vì sửa prompt."
          }
        >
          ⓘ prompt nguyên văn · nên viết tiếng Anh
        </div>
      )}
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function VideoNode({ id, data }: NodeProps) {
  const { update, projDur } = useContext(NodeOps);
  const d = data as any;
  const model = d.model || "veo_lite";
  const isLite = model === "veo_lite";
  const liteMode = d.lite_mode || "inference";
  // Chỉ hai chỗ chọn được độ dài: Omni Flash (4-10s) và Veo Lite kiểu nội suy khung
  // đầu/cuối (4-8s). Veo Lite "inference" và Veo i2v đều bị Flow cứng 8s.
  const hasDuration = model === "omni" || (isLite && liteMode === "frames");
  const maxDur = isLite ? 8 : 10;
  // No per-node duration → follow ⚙ Cấu hình dự án (the backend falls back the same way).
  const eff = Math.min(d.duration || projDur || 8, maxDur);
  return (
    <Shell type="video" id={id} data={d}>
      <Preview nodeId={id} src={d._result} video label="Kết quả video" />
      <AspectModelRow id={id} data={d} videoModels />
      {isLite && (
        <label className="block">
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Kiểu tạo</div>
          <select
            className={fieldCls}
            value={liteMode}
            onChange={(e) => update(id, { lite_mode: e.target.value })}
          >
            <option value="inference">Inference — mọi ảnh nối vào = tham chiếu, không nối ảnh = chỉ prompt (8s)</option>
            <option value="frames">Khung đầu + khung cuối — nội suy (4/6/8s)</option>
          </select>
        </label>
      )}
      <Slider label="Số lượng tạo" value={d.count || 1} min={1} max={4} step={1} onChange={(v) => update(id, { count: v })} />
      {hasDuration && (
        <>
          <Slider label="Thời lượng" value={eff} min={4} max={maxDur} step={2} suffix="s" onChange={(v) => update(id, { duration: v })} />
          {/* A node saved back when the editor hard-coded 8s silently overrode a project set
              to 10s — say so instead of quietly rendering the shorter clip. */}
          {!!projDur && !!d.duration && d.duration !== projDur && (
            <button
              onClick={() => update(id, { duration: 0 })}
              className="nodrag w-full rounded-md border border-amber-700/60 bg-amber-950/30 px-2 py-1 text-left text-[10px] text-amber-300 hover:bg-amber-900/40"
            >
              ⚠ Dự án đặt {projDur}s — bấm để dùng theo dự án
            </button>
          )}
        </>
      )}
      <div className="text-[10px] text-neutral-500">
        ⓘ prompt áp style/header/footer dự án (như node Tạo ảnh)
        {isLite && (
          <>
            <br />
            ⚡ Veo 3.1 Lite [Lower Priority]: 0 credit, chỉ tài khoản Ultra — đổi lại xếp hàng
            ưu tiên thấp nên clip lâu hơn.
            {liteMode === "frames"
              ? " Nối ĐÚNG 2 ảnh: ảnh vào trước là khung đầu, ảnh sau là khung cuối."
              : " Kiểu inference Flow cứng 8s — muốn 4/6s thì đổi sang khung đầu + khung cuối. Không nối ảnh nào vào thì chạy text-to-video, chỉ từ prompt."}
          </>
        )}
      </div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function OutputNode({ id, data }: NodeProps) {
  const { inputResults } = useContext(NodeOps);
  const d = data as any;
  // Prefer whatever currently feeds the Output so it tracks upstream changes; fall back
  // to its own last result. No nodeId → Preview won't pin a stale run-result.
  const live = inputResults[id];
  const web = live?.web || d._result || d.result_web;
  const ext = live?.ext || d._ext || d.result_ext || "png";
  return (
    <Shell type="output" id={id} outputs={false}>
      <Preview src={web} video={ext === "mp4"} label="Output cuối" />
    </Shell>
  );
}

// Local (Pillow) image-processing nodes — no AI/credit, result re-uploaded so the chain
// continues. All take an image input and produce an image.
function FilterNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  const num = (k: string, dflt: number) => (d[k] ?? dflt);
  return (
    <Shell type="filter" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả filter" />
      <Slider label="Sáng" value={num("brightness", 1)} min={0} max={2} step={0.05} onChange={(v) => update(id, { brightness: v })} />
      <Slider label="Tương phản" value={num("contrast", 1)} min={0} max={2} step={0.05} onChange={(v) => update(id, { contrast: v })} />
      <Slider label="Bão hòa" value={num("saturation", 1)} min={0} max={2} step={0.05} onChange={(v) => update(id, { saturation: v })} />
      <Slider label="Độ nét" value={num("sharpness", 1)} min={0} max={2} step={0.05} onChange={(v) => update(id, { sharpness: v })} />
      <Slider label="Làm mờ" value={num("blur", 0)} min={0} max={20} step={0.5} suffix="px" onChange={(v) => update(id, { blur: v })} />
      <ToggleChips id={id} data={d} items={[
        { key: "auto", label: "Auto" },
        { key: "grayscale", label: "Đen trắng" },
        { key: "sepia", label: "Sepia" },
        { key: "flip_h", label: "⇆ Lật ngang" },
        { key: "flip_v", label: "⥯ Lật dọc" },
      ]} />
      <label className="block">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Xoay</div>
        <select className={fieldCls} value={String(d.rotate || 0)} onChange={(e) => update(id, { rotate: Number(e.target.value) })}>
          {[0, 90, 180, 270].map((r) => <option key={r} value={r}>{r}°</option>)}
        </select>
      </label>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function TextNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="text" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả chèn chữ" />
      <textarea
        className={`${fieldCls} nowheel h-14 resize-none leading-snug`}
        value={d.text ?? ""}
        placeholder="Nội dung chữ…"
        onChange={(e) => update(id, { text: e.target.value })}
      />
      <div className="flex gap-2">
        <label className="flex-1">
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Vị trí</div>
          <select className={fieldCls} value={d.anchor || "bottom"} onChange={(e) => update(id, { anchor: e.target.value })}>
            {["top", "center", "bottom", "top-left", "top-right", "bottom-left", "bottom-right"].map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </label>
        <label>
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Màu</div>
          <input type="color" value={d.color || "#ffffff"} onChange={(e) => update(id, { color: e.target.value })}
            className="nodrag h-[26px] w-9 cursor-pointer rounded border border-neutral-700 bg-neutral-900" />
        </label>
      </div>
      <Slider label="Cỡ chữ" value={d.font_scale ?? 0.06} min={0.02} max={0.3} step={0.01} onChange={(v) => update(id, { font_scale: v })} />
      <ToggleChips id={id} data={d} items={[{ key: "stroke", label: "Viền đen" }]} />
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function UpscaleNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="upscale" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả upscale" />
      <Slider label="Phóng to" value={d.scale ?? 2} min={1} max={4} step={0.5} suffix="×" onChange={(v) => update(id, { scale: v })} />
      <ToggleChips id={id} data={d} items={[{ key: "sharpen", label: "Làm nét" }]} />
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function CropNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="crop" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả crop" />
      <label className="block">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Khung tỉ lệ</div>
        <select className={fieldCls} value={d.aspect || "free"} onChange={(e) => update(id, { aspect: e.target.value })}>
          {["free", "16:9", "9:16", "1:1", "4:3", "3:4"].map((a) => (
            <option key={a} value={a}>{a === "free" ? "Giữ nguyên" : a}</option>
          ))}
        </select>
      </label>
      <Slider label="Phóng (punch-in)" value={d.zoom ?? 1} min={1} max={3} step={0.05} suffix="×" onChange={(v) => update(id, { zoom: v })} />
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function VignetteNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="vignette" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả vignette" />
      <Slider label="Độ tối viền" value={d.strength ?? 0.5} min={0} max={1} step={0.05} onChange={(v) => update(id, { strength: v })} />
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function BlendNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  const mode = d.mode || "alpha";
  return (
    <Shell type="blend" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả ghép" />
      <label className="block">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Kiểu</div>
        <select className={fieldCls} value={mode} onChange={(e) => update(id, { mode: e.target.value })}>
          <option value="alpha">Hòa trộn (alpha)</option>
          <option value="side">Cạnh nhau</option>
        </select>
      </label>
      {mode === "alpha" && (
        <Slider label="Tỷ lệ trộn" value={d.alpha ?? 0.5} min={0} max={1} step={0.05} onChange={(v) => update(id, { alpha: v })} />
      )}
      <div className="text-[10px] text-neutral-500">ⓘ nối 2 nguồn ảnh vào node này</div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function RemoveBgNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="removebg" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả tách nền" />
      <label className="block">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Nền mới</div>
        <select className={fieldCls} value={d.bg || "white"} onChange={(e) => update(id, { bg: e.target.value })}>
          <option value="white">Trắng</option>
          <option value="black">Đen</option>
          <option value="green">Phông xanh (chroma)</option>
          <option value="gray">Xám trung tính</option>
        </select>
      </label>
      <div className="text-[10px] text-amber-400/80">⚠ Dùng AI — chậm và có thể bị chặn nội dung</div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function BorderNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="border" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả khung viền" />
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Slider label="Độ dày" value={d.width ?? 0.04} min={0} max={0.25} step={0.01} onChange={(v) => update(id, { width: v })} />
        </div>
        <label>
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Màu</div>
          <input type="color" value={d.color || "#000000"} onChange={(e) => update(id, { color: e.target.value })}
            className="nodrag h-[26px] w-9 cursor-pointer rounded border border-neutral-700 bg-neutral-900" />
        </label>
      </div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function ColorGradeNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="colorgrade" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả color grade" />
      <label className="block">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Tông màu</div>
        <select className={fieldCls} value={d.preset || "teal_orange"} onChange={(e) => update(id, { preset: e.target.value })}>
          {[["teal_orange", "Teal–Orange (điện ảnh)"], ["warm", "Ấm"], ["cold", "Lạnh"],
            ["vintage", "Vintage"], ["noir", "Noir (đen trắng)"], ["vibrant", "Rực rỡ"], ["muted", "Trầm"]]
            .map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>
      <Slider label="Cường độ" value={d.intensity ?? 1} min={0} max={1} step={0.05} onChange={(v) => update(id, { intensity: v })} />
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function CollageNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="collage" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả ghép lưới" />
      <Slider label="Số cột (0 = tự)" value={d.cols ?? 0} min={0} max={6} step={1} onChange={(v) => update(id, { cols: v })} />
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Slider label="Khoảng cách" value={d.gap ?? 8} min={0} max={60} step={2} suffix="px" onChange={(v) => update(id, { gap: v })} />
        </div>
        <label>
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Nền</div>
          <input type="color" value={d.bg || "#000000"} onChange={(e) => update(id, { bg: e.target.value })}
            className="nodrag h-[26px] w-9 cursor-pointer rounded border border-neutral-700 bg-neutral-900" />
        </label>
      </div>
      <div className="text-[10px] text-neutral-500">ⓘ nối ≥2 nguồn ảnh vào node này</div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function WatermarkNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="watermark" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả watermark" />
      <label className="block">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-500">Vị trí logo</div>
        <select className={fieldCls} value={d.position || "bottom-right"} onChange={(e) => update(id, { position: e.target.value })}>
          {["top-left", "top-right", "bottom-left", "bottom-right", "center"].map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </label>
      <Slider label="Cỡ logo" value={d.scale ?? 0.18} min={0.05} max={0.6} step={0.01} onChange={(v) => update(id, { scale: v })} />
      <Slider label="Độ mờ" value={d.opacity ?? 0.85} min={0.05} max={1} step={0.05} onChange={(v) => update(id, { opacity: v })} />
      <div className="text-[10px] text-neutral-500">ⓘ nối ảnh NỀN trước, LOGO sau</div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

function ReplaceBgNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="replacebg" id={id} data={d}>
      <Preview nodeId={id} src={d._result} label="Kết quả thay nền" />
      <textarea
        className={`${fieldCls} nowheel h-12 resize-none leading-snug`}
        value={d.text ?? ""}
        placeholder="Mô tả thêm (không bắt buộc)…"
        onChange={(e) => update(id, { text: e.target.value })}
      />
      <div className="text-[10px] text-neutral-500">ⓘ nối CHỦ THỂ trước, ẢNH NỀN sau</div>
      <div className="text-[10px] text-neutral-500">ⓘ prompt dùng nguyên văn — không áp style/culture dự án</div>
      <div className="text-[10px] text-amber-400/80">⚠ Dùng AI — chậm và có thể bị chặn nội dung</div>
      <GenControls id={id} data={d} />
    </Shell>
  );
}

// Bọc ngoài prompt của node tạo ảnh/video mà nó nối tới. Trước đây header/footer của ⚙ Cấu
// hình dự án được chèn ngầm vào MỌI prompt; giờ trong node editor nó chỉ vào khi có node này
// trên canvas, nên nhìn đồ thị là biết prompt thật sự gồm những gì.
function PromptWrapNode({ id, data, type, selected }: NodeProps) {
  const { update, projectHeader, projectFooter } = useContext(NodeOps);
  const d = data as any;
  const isHeader = type === "promptHeader";
  // Bỏ trống = dùng giá trị của dự án (sửa ở Thiết lập là mọi graph ăn theo).
  const fallback = (isHeader ? projectHeader : projectFooter) || "";
  // Header của dự án dài tới sáu đoạn — cùng lý do với node Prompt, cho kéo giãn.
  const grown = !!d.h;
  return (
    <>
      <SizeGrip id={id} visible={!!selected} minH={140} />
      <Shell type={type} id={id} outputs width={d.w} height={d.h}>
      <textarea
        className={`${fieldCls} nowheel leading-snug ${
          grown ? "min-h-0 flex-1 resize-none" : "h-20 resize-y"
        }`}
        value={d.text ?? ""}
        placeholder={fallback ? `(theo dự án) ${fallback}` : "Bỏ trống = theo ⚙ Thiết lập dự án"}
        onChange={(e) => update(id, { text: e.target.value })}
      />
      <div className="shrink-0 text-[10px] text-neutral-500">
        {d.text?.trim()
          ? isHeader ? "ⓘ chèn vào ĐẦU prompt" : "ⓘ chèn vào CUỐI prompt"
          : fallback
            ? "ⓘ đang dùng giá trị của dự án"
            : "⚠ dự án chưa đặt — node này không chèn gì"}
      </div>
      </Shell>
    </>
  );
}

function NoteNode({ id, data }: NodeProps) {
  const { update } = useContext(NodeOps);
  const d = data as any;
  return (
    <Shell type="note" id={id} inputs={false} outputs={false}>
      <textarea
        className="nodrag nowheel h-20 w-full resize-none rounded-md border border-amber-700/40 bg-amber-950/20 px-2 py-1 text-[11px] text-amber-100 outline-none"
        value={d.text ?? ""}
        placeholder="Ghi chú / nhãn nhóm…"
        onChange={(e) => update(id, { text: e.target.value })}
      />
    </Shell>
  );
}

const NODE_TYPES = {
  source: SourceNode,
  prompt: PromptNode,
  promptHeader: PromptWrapNode,
  promptFooter: PromptWrapNode,
  refs: RefsNode,
  image: ImageNode,
  editImage: ImageNode,
  removebg: RemoveBgNode,
  replacebg: ReplaceBgNode,
  filter: FilterNode,
  colorgrade: ColorGradeNode,
  text: TextNode,
  upscale: UpscaleNode,
  crop: CropNode,
  vignette: VignetteNode,
  border: BorderNode,
  blend: BlendNode,
  collage: CollageNode,
  watermark: WatermarkNode,
  video: VideoNode,
  note: NoteNode,
  output: OutputNode,
};

// ─── Default graph ──────────────────────────────────────────
// Built from the target's goal (image vs video) + its seeded sources, so storyboard
// edits open on an image graph and shot edits on a video graph. Each reference entity
// becomes its own "Nguồn ảnh" (source) node, pre-filled with that entity's image.
//
// CHỈ những ảnh shot THẬT SỰ tham chiếu tới mới thành node. Trước đây đồ thị mặc định còn
// gieo sẵn MỌI frame khác trong cùng scene thành một "kệ" node Nguồn ảnh không nối dây, cho
// tiện kéo dây khi cần. Nhưng nó là node phải XOÁ TAY: mở một shot trong scene đã có 20
// frame là ra 20 node thừa, và với shot thêm hàng loạt từ text — nơi các prompt chẳng liên
// quan gì nhau — thì không cái nào dùng tới. Cần một frame cụ thể thì thêm node "Nguồn ảnh"
// rồi chọn trong danh sách của nó: nó vốn đã liệt kê sẵn toàn bộ frame của dự án.
function defaultGraph(
  seed: EditorTarget,
  entities: Entity[],
  // Engine + tỷ lệ của ⚙ Cấu hình dự án — node video của đồ thị mặc định phải khởi đầu
  // bằng chính chúng, không phải hằng số "veo_lite"/"16:9".
  proj: { engine: string; aspect: string }
): { nodes: Node[]; edges: Edge[] } {
  const mk = (id: string, type: string, x: number, y: number, data: any = {}): Node => ({
    id,
    type,
    position: { x, y },
    data: { ...data, _type: type },
  });
  const prompt = seed.prompt ?? "";
  const goal = seed.goal || (seed.kind === "shot" ? "video" : "image");
  const byId = new Map(entities.map((e) => [e.id, e]));

  const nodes: Node[] = [mk("p", "prompt", 0, 20, { text: prompt, seed_prompt: prompt })];
  const edges: Edge[] = [];

  // Header/footer của ⚙ Thiết lập dự án nay đi qua HAI NODE thay vì được chèn ngầm, nên
  // đồ thị mặc định phải có sẵn chúng — không thì graph mới lại ra prompt trần.
  const wrapNodes = (genId: string) => {
    nodes.push(mk("ph", "promptHeader", -300, 20, { text: "" }));
    nodes.push(mk("pf", "promptFooter", -300, 170, { text: "" }));
    edges.push(
      { id: "eph", source: "ph", target: genId },
      { id: "epf", source: "pf", target: genId }
    );
  };

  if (goal === "video") {
    // Frame của CHÍNH shot làm ảnh start/tham chiếu — nhưng CHỈ khi shot đã có frame.
    // Shot chưa có ảnh (vd thêm hàng loạt từ text) mà vẫn gieo node này thì được một node
    // "Nguồn ảnh" RỖNG nối sẵn vào node tạo video: không dùng được việc gì, và người dùng
    // phải xoá tay. Không có nó, đồ thị mặc định đúng bằng thứ cần cho text-to-video
    // (prompt → tạo video → output), thứ Veo Lite và Omni Flash đều làm được.
    if (seed.imageMediaId) {
      nodes.push(
        mk("src", "source", 0, 250, {
          media_id: seed.imageMediaId,
          web: seed.imageSrc || "",
          label: seed.title,
        })
      );
    }
    nodes.push(
      // No `duration` → the clip length comes from ⚙ Cấu hình dự án.
      mk("v", "video", 340, 80, {
        model: proj.engine, lite_mode: "inference", aspect: proj.aspect, count: 1,
        _result: seed.videoSrc || "",
      })
    );
    nodes.push(mk("o", "output", 660, 110, { _result: seed.videoSrc || "", _ext: "mp4" }));
    edges.push({ id: "ep", source: "p", target: "v" });
    if (seed.imageMediaId) edges.push({ id: "es", source: "src", target: "v" });
    edges.push({ id: "eo", source: "v", target: "o" });
    wrapNodes("v");
    return { nodes, edges };
  }

  // image goal: one source node per referenced entity (pre-filled)
  const refIds = (seed.refEntityIds ?? []).filter((i) => byId.get(i)?.media_id);
  refIds.forEach((eid, k) => {
    const e = byId.get(eid)!;
    nodes.push(
      mk(`src${k}`, "source", 0, 200 + k * 150, {
        entity_id: e.id, media_id: e.media_id, web: e.image_path, label: e.name,
      })
    );
    edges.push({ id: `es${k}`, source: `src${k}`, target: "i" });
  });
  // Ảnh tham chiếu người/đồ vật đi khung DỌC: chúng cao hơn rộng, khung ngang phí gần nửa ảnh
  // vào nền trắng hai bên và bóp nhỏ chủ thể — ít điểm ảnh trên khuôn mặt thì model lược nét,
  // mắt to kiểu anime trôi về mắt nhỏ tả thực. Bối cảnh giữ khung NGANG (nó là con phố, và
  // phải khớp khung hình video). Khớp với _entity_aspect() bên agent, đừng để hai bên lệch.
  const refAspect =
    seed.kind === "entity" && ["character", "prop"].includes(seed.entityType || "")
      ? "9:16"
      : "16:9";
  nodes.push(
    mk("i", "image", 340, 80, { aspect: refAspect, model: "", count: 1, _result: seed.imageSrc || "" })
  );
  nodes.push(mk("o", "output", 660, 110, { _result: seed.imageSrc || "" }));
  edges.push({ id: "ep", source: "p", target: "i" }, { id: "eo", source: "i", target: "o" });
  wrapNodes("i");
  return { nodes, edges };
}

// Node "bọc prompt", và các node sinh mà chúng gắn vào. CHỈ image + video: editImage /
// replacebg chạy prompt NGUYÊN VĂN (không qua compose_prompt) nên gắn vào đó chỉ tạo ra một
// node nằm im không tác dụng gì — xem agent/studio/graph.py.
const WRAP_TYPES = ["promptHeader", "promptFooter"] as const;
const WRAP_TARGETS = ["image", "video"];

// Đồ thị lưu từ bản editor này mang `v`. Đồ thị KHÔNG có `v` là bản cũ, lưu từ trước khi
// header/footer tách thành node — chỉ những đồ thị ấy mới được `ensurePromptWrap` vá thêm
// node. Tăng số này khi lại có một lần vá tự động kiểu đó nữa.
const GRAPH_V = 2;

// ─── Editor ─────────────────────────────────────────────────
// Độ dài clip mà ⚙ Cấu hình dự án đặt được — chỉ Omni Flash mới có ("10" / "abra_r2v_10s"
// → 10). Veo Lite và Veo i2v đều bị Flow cứng 8s ở cấp dự án nên trả null: độ dài của Veo
// Lite chỉ đổi được trên chính node, và chỉ ở kiểu nội suy khung đầu/cuối.
// Mirrors _omni_duration() in agent/studio/graph.py.
const omniDuration = (videoModel?: string | null): number | null => {
  const m = String(videoModel || "").trim().match(/^(?:abra_r2v_)?(\d+)s?$/);
  const n = m ? Number(m[1]) : NaN;
  return [4, 6, 8, 10].includes(n) ? n : null;
};

// Engine mà ⚙ Cấu hình dự án đang chọn, theo đúng giá trị ô "Model" của node video.
// Mirrors video_engine() in agent/studio/graph.py — ô rỗng KHÔNG có nghĩa là Veo: mặc định
// của tài khoản Ultra (PAYGATE_TIER_TWO) là Veo Lite. Hai bên lệch nhau thì node hiện một
// engine còn server chạy một engine khác, mà đó đúng là thứ tính tiền.
const projectEngine = (videoModel?: string | null, tier?: string | null): string => {
  const raw = String(videoModel || "").trim();
  if (omniDuration(raw) != null) return "omni";
  if (raw.startsWith("veo_lite")) return "veo_lite";
  if (raw === "veo") return "veo";
  return tier === "PAYGATE_TIER_TWO" ? "veo_lite" : "veo";
};

// VIDEO_ASPECT_RATIO_* của dự án → nhãn tỷ lệ trên node.
const projectAspect = (aspect?: string | null): string =>
  String(aspect || "").includes("PORTRAIT") ? "9:16" : "16:9";

function Editor({
  target,
  entities,
  projectId,
  videoModel,
  videoAspect,
  paygateTier,
  projectHeader: headerProp,
  projectFooter: footerProp,
  onClose,
  onApplied,
}: {
  target: EditorTarget;
  entities: Entity[];
  projectId: string;
  videoModel?: string | null;
  videoAspect?: string | null;
  paygateTier?: string | null;
  projectHeader?: string | null;
  projectFooter?: string | null;
  onClose: () => void;
  onApplied: (r: any) => void;
}) {
  const projDur = useMemo(() => omniDuration(videoModel), [videoModel]);
  // Giá trị khởi đầu cho node video MỚI (xem NODE_DEFAULTS): lấy theo ⚙ Cấu hình dự án chứ
  // không cứng "veo_lite" + "16:9" — dự án đặt Omni Flash / khung dọc mà node mới hiện Veo
  // Lite ngang là đọc sai ngay từ lúc kéo node ra.
  const projEngine = useMemo(
    () => projectEngine(videoModel, paygateTier), [videoModel, paygateTier]);
  const projAspect = useMemo(() => projectAspect(videoAspect), [videoAspect]);
  // Cột DB cho phép NULL → chuẩn hoá về "" một lần, node không phải tự lo.
  const projectHeader = headerProp ?? "";
  const projectFooter = footerProp ?? "";
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [imageModels, setImageModels] = useState<string[]>([]);
  const [shots, setShots] = useState<Shot[]>([]);
  // Every image in the project (Flow), so "Nguồn ảnh" can reference any of them — not just
  // assets/storyboard. {media_id, name}.
  const [projMedia, setProjMedia] = useState<{ media_id: string; name: string }[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  // Edge under the cursor — highlighted so it's obvious WHICH connection a right-click hits
  // when several of them converge on the same node.
  const [hoverEdge, setHoverEdge] = useState<string | null>(null);
  // Right-click menu (on a connection, a node, the multi-selection, or empty canvas).
  const [menu, setMenu] = useState<
    | { x: number; y: number; kind: "edge"; id: string }
    | { x: number; y: number; kind: "node"; id: string }
    | { x: number; y: number; kind: "selection" }
    | { x: number; y: number; kind: "pane"; at: { x: number; y: number } }
    | null
  >(null);
  // Box-select mode: left-drag draws a selection rectangle instead of panning the canvas.
  const [boxSelect, setBoxSelect] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  // Run results keyed by node id — kept apart from node.data so a graph reload
  // (e.g. after onApplied refreshes the parent) doesn't wipe the previews.
  const [results, setResults] = useState<Record<string, { web: string; ext: string }>>({});
  const [lightbox, setLightbox] = useState<{ src: string; video: boolean } | null>(null);
  const [genningId, setGenningId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<GraphTemplate[]>([]);
  const [presetSel, setPresetSel] = useState("");
  // Undo/redo history of durable graph snapshots (structure + settings + positions),
  // ignoring transient run-result previews so a generation doesn't pollute history.
  // Signature of the graph last written to the server — drives the debounced autosave below.
  const savedSig = useRef<string | null>(null);
  const histRef = useRef<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const histIdx = useRef(-1);
  const lastSig = useRef("");
  const skipHist = useRef(false);
  const [histVer, setHistVer] = useState(0);

  // Thick edges + arrow markers; edges touching the active node animate (marching arrows)
  // so connections are easy to follow on a touch screen. The one under the cursor (or picked
  // with a click) turns rose and fattens, so you always know which line you're about to act on.
  const displayEdges = useMemo(
    () =>
      edges.map((e) => {
        const active = !!activeId && (e.source === activeId || e.target === activeId);
        const hot = e.id === hoverEdge || !!e.selected;
        const color = hot ? "#fb7185" : active ? "#818cf8" : "#6b7280";
        return {
          ...e,
          animated: active || hot,
          // A fat invisible hit area — a 3px line is near impossible to right-click where
          // several connections converge on one node.
          interactionWidth: 26,
          markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color },
          style: { strokeWidth: hot ? 6 : active ? 5 : 3, stroke: color },
        };
      }),
    [edges, activeId, hoverEdge]
  );

  const update = useCallback(
    (id: string, patch: any) =>
      setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n))),
    [setNodes]
  );

  const remove = useCallback(
    (id: string) => {
      setNodes((ns) => ns.filter((n) => n.id !== id));
      setEdges((es) => es.filter((e) => e.source !== id && e.target !== id));
      setActiveId((a) => (a === id ? null : a));
    },
    [setNodes, setEdges]
  );

  // Clone a node (its settings, minus the transient result) offset a bit — no edges copied.
  const duplicate = useCallback(
    (id: string) => {
      setNodes((ns) => {
        const src = ns.find((n) => n.id === id);
        if (!src) return ns;
        const { _result, _ext, preview, result_media_id, result_web, result_ext, locked, ...rest } =
          src.data as any;
        const nid = `${src.type}-${Date.now()}`;
        // Two nodes sharing a "định danh" make every {token} mention of it ambiguous, so the
        // copy gets its own — "Áo khoác" → "Áo khoác 2".
        if (rest.handle) rest.handle = freeHandle(takenHandles(ns), rest.handle);
        return [
          ...ns,
          { id: nid, type: src.type, data: { ...rest, _type: src.type },
            position: { x: src.position.x + 40, y: src.position.y + 40 } },
        ];
      });
    },
    [setNodes]
  );

  // ── Connections: explicit, unambiguous removal ──
  // Dragging an endpoint off the connector still works, but with several lines landing on one
  // node you can't tell which one you grabbed. These are driven by the right-click menu, where
  // each connection is named by the nodes it joins.
  const removeEdge = useCallback(
    (edgeId: string) => setEdges((es) => es.filter((e) => e.id !== edgeId)),
    [setEdges]
  );
  const removeEdgesOf = useCallback(
    (nodeId: string, dir: "in" | "out" | "all") =>
      setEdges((es) =>
        es.filter((e) =>
          dir === "in" ? e.target !== nodeId
          : dir === "out" ? e.source !== nodeId
          : e.source !== nodeId && e.target !== nodeId
        )
      ),
    [setEdges]
  );

  // A human name for a node in the connection menu: "🖼 Nguồn ảnh «Nam»".
  const nodeLabel = useCallback(
    (id: string) => {
      const n = nodes.find((x) => x.id === id);
      if (!n) return id;
      const m = META[(n.type as string) || "output"] || META.output;
      const h = HANDLE_TYPES.has(n.type || "") ? effHandle(n.type!, n.data as any) : "";
      return `${m.icon} ${m.label}${h ? ` «${h}»` : ""}`;
    },
    [nodes]
  );

  // ── Group operations (select → copy / paste / duplicate / delete / move) ──
  // Shift+drag (or the ▭ toggle) boxes a group; the whole group then drags as one, and these
  // handle the rest. The clipboard is in-memory: pasting carries the wiring BETWEEN the copied
  // nodes, not the links to nodes left behind.
  const clipboard = useRef<{ nodes: Node[]; edges: Edge[] } | null>(null);
  const [clipCount, setClipCount] = useState(0);
  // Where the cursor last was over the canvas, so Ctrl+V / "Dán tại đây" lands under it.
  const lastPointer = useRef<{ x: number; y: number } | null>(null);

  const selectedIds = useMemo(
    () => new Set(nodes.filter((n) => n.selected).map((n) => n.id)),
    [nodes]
  );

  const copySelection = useCallback(() => {
    const sel = nodes.filter((n) => n.selected);
    if (!sel.length) return false;
    const ids = new Set(sel.map((n) => n.id));
    clipboard.current = {
      nodes: sel.map((n) => ({ ...n, position: { ...n.position }, data: { ...(n.data as any) } })),
      edges: edges.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({ ...e })),
    };
    setClipCount(sel.length);
    return true;
  }, [nodes, edges]);

  // Paste the clipboard at `at` (flow coords) keeping the group's internal layout, or offset
  // from the original when no position is given. The pasted copy becomes the new selection.
  const pasteClipboard = useCallback(
    (at?: { x: number; y: number } | null) => {
      const clip = clipboard.current;
      if (!clip?.nodes.length) return;
      const stamp = Date.now();
      const idMap = new Map<string, string>(
        clip.nodes.map((n, i) => [n.id, `${n.type}-${stamp}-${i}`])
      );
      const minX = Math.min(...clip.nodes.map((n) => n.position.x));
      const minY = Math.min(...clip.nodes.map((n) => n.position.y));
      const dx = at ? at.x - minX : 48;
      const dy = at ? at.y - minY : 48;
      setNodes((ns) => {
        const taken = takenHandles(ns);
        const made = clip.nodes.map((n) => {
          const { _result, _ext, preview, result_media_id, result_web, result_ext, locked, ...rest } =
            n.data as any;
          if (rest.handle) {
            rest.handle = freeHandle(taken, rest.handle);
            taken.add(rest.handle.toLowerCase()); // …so two copies don't collide with each other
          }
          return {
            id: idMap.get(n.id)!,
            type: n.type,
            selected: true,
            position: { x: n.position.x + dx, y: n.position.y + dy },
            data: { ...rest, _type: n.type },
          } as Node;
        });
        return [...ns.map((n) => (n.selected ? { ...n, selected: false } : n)), ...made];
      });
      setEdges((es) => [
        ...es.map((e) => (e.selected ? { ...e, selected: false } : e)),
        ...clip.edges.map((e, i) => ({
          id: `e-${stamp}-${i}`,
          source: idMap.get(e.source)!,
          target: idMap.get(e.target)!,
        })),
      ]);
    },
    [setNodes, setEdges]
  );

  const deleteSelection = useCallback(() => {
    const ids = new Set(nodes.filter((n) => n.selected).map((n) => n.id));
    const anyEdge = edges.some((e) => e.selected);
    if (!ids.size && !anyEdge) return;
    setNodes((ns) => ns.filter((n) => !ids.has(n.id)));
    setEdges((es) => es.filter((e) => !e.selected && !ids.has(e.source) && !ids.has(e.target)));
    setActiveId((a) => (a && ids.has(a) ? null : a));
  }, [nodes, edges, setNodes, setEdges]);

  const selectAll = useCallback(
    () => setNodes((ns) => ns.map((n) => (n.selected ? n : { ...n, selected: true }))),
    [setNodes]
  );

  // ── Undo / redo ──
  // A signature of the DURABLE graph (ignores transient previews) so result injections
  // don't create history entries; positions are rounded so a drag = one coalesced entry.
  const sigOf = useCallback((ns: Node[], es: Edge[]) => {
    const strip = (d: any) => {
      const { _result, _ext, preview, result_media_id, result_web, result_ext, ...r } = d || {};
      return r;
    };
    return JSON.stringify({
      n: ns.map((n) => ({ id: n.id, t: n.type, x: Math.round(n.position.x),
                          y: Math.round(n.position.y), d: strip(n.data) })),
      e: es.map((e) => ({ s: e.source, t: e.target })),
    });
  }, []);

  useEffect(() => {
    const tid = setTimeout(() => {
      const sig = sigOf(nodes, edges);
      if (skipHist.current) {        // change came from an undo/redo restore — don't re-record
        skipHist.current = false;
        lastSig.current = sig;
        return;
      }
      if (sig === lastSig.current) return;
      lastSig.current = sig;
      const snap = {
        nodes: nodes.map((n) => ({ ...n, position: { ...n.position }, data: { ...n.data } })),
        edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
      };
      histRef.current = histRef.current.slice(0, histIdx.current + 1);
      histRef.current.push(snap);
      if (histRef.current.length > 60) histRef.current.shift();
      histIdx.current = histRef.current.length - 1;
      setHistVer((v) => v + 1);
    }, 350);
    return () => clearTimeout(tid);
  }, [nodes, edges, sigOf]);

  const restoreHist = useCallback(
    (idx: number) => {
      const s = histRef.current[idx];
      if (!s) return;
      histIdx.current = idx;
      skipHist.current = true;
      setNodes(s.nodes.map((n) => ({ ...n, position: { ...n.position }, data: { ...n.data } })));
      setEdges(s.edges.map((e) => ({ ...e })));
      setHistVer((v) => v + 1);
    },
    [setNodes, setEdges]
  );
  // Auto-add a "Nguồn ảnh" node for `entityId` (prefilled with its image) and connect it to
  // whatever `fromId` (the prompt node) already feeds — so picking {Entity} in a prompt makes
  // that reference actually bind. Reuses an existing source node for the same entity.
  const bindEntitySource = useCallback(
    (fromId: string, entityId: string) => {
      const ent = entities.find((e) => e.id === entityId);
      if (!ent) return;
      const existing = nodes.find((n) => n.type === "source" && (n.data as any).entity_id === entityId);
      const srcId = existing?.id || `source-${Date.now()}`;
      const targets = edges.filter((e) => e.source === fromId).map((e) => e.target);
      if (!existing) {
        const from = nodes.find((n) => n.id === fromId);
        const nSources = nodes.filter((n) => n.type === "source").length;
        const pos = from
          ? { x: from.position.x, y: from.position.y + 150 + nSources * 30 }
          : { x: 0, y: 200 + nSources * 30 };
        setNodes((ns) => [
          ...ns,
          { id: srcId, type: "source", position: pos,
            data: { _type: "source", entity_id: ent.id, media_id: ent.media_id || "",
                    web: ent.image_path || "", label: ent.name } },
        ]);
      }
      setEdges((es) => {
        const add = targets
          .filter((t) => !es.some((e) => e.source === srcId && e.target === t))
          .map((t) => ({ id: `e-${srcId}-${t}`, source: srcId, target: t }));
        return add.length ? [...es, ...add] : es;
      });
    },
    [entities, nodes, edges, setNodes, setEdges]
  );

  // ── Handles ("định danh") ──
  // Every image-producing node, by the token a prompt uses to address it.
  const handles = useMemo(
    () =>
      nodes
        .filter((n) => HANDLE_TYPES.has(n.type || ""))
        .map((n) => {
          const d = n.data as any;
          return {
            id: n.id,
            type: n.type!,
            handle: effHandle(n.type!, d),
            web: results[n.id]?.web || d._result || d.result_web || d.web,
          };
        })
        .filter((h) => !!h.handle),
    [nodes, results]
  );

  // A repeated handle only misleads the model once a prompt actually writes it as {token} —
  // two untouched "image" nodes nobody references are harmless, so stay quiet about those.
  const handleDupes = useMemo(() => {
    const count = new Map<string, number>();
    for (const h of handles) {
      const k = h.handle.toLowerCase();
      count.set(k, (count.get(k) || 0) + 1);
    }
    const used = new Set<string>();
    for (const n of nodes) {
      const d = n.data as any;
      if (n.type === "prompt" || n.type === "editImage" || n.type === "replacebg")
        for (const t of tokensIn(d.text || "")) used.add(t.toLowerCase());
      if (d.base_handle) used.add(String(d.base_handle).toLowerCase());
    }
    return new Set([...count].filter(([k, c]) => c > 1 && used.has(k)).map(([k]) => k));
  }, [handles, nodes]);

  const upstreamHandles = useCallback(
    (id: string) => {
      const ups = new Set(edges.filter((e) => e.target === id).map((e) => e.source));
      return handles.filter((h) => ups.has(h.id)).map((h) => ({ id: h.id, handle: h.handle }));
    },
    [edges, handles]
  );

  // Wire an existing node into whatever `fromId` (a prompt node) already feeds, so a {handle}
  // just typed into that prompt actually reaches the generator. Skips any wire that would
  // close a loop (e.g. referencing the very node this prompt drives).
  const bindNodeSource = useCallback(
    (fromId: string, nodeId: string) => {
      setEdges((es) => {
        const reaches = (from: string, to: string) => {
          const seen = new Set<string>();
          const stack = [from];
          while (stack.length) {
            const cur = stack.pop()!;
            if (cur === to) return true;
            if (seen.has(cur)) continue;
            seen.add(cur);
            for (const e of es) if (e.source === cur) stack.push(e.target);
          }
          return false;
        };
        const add = es
          .filter((e) => e.source === fromId)
          .map((e) => e.target)
          .filter(
            (t) =>
              t !== nodeId &&
              !es.some((e) => e.source === nodeId && e.target === t) &&
              !reaches(t, nodeId)
          )
          .map((t) => ({ id: `e-${nodeId}-${t}`, source: nodeId, target: t }));
        return add.length ? [...es, ...add] : es;
      });
    },
    [setEdges]
  );

  const undo = useCallback(() => restoreHist(histIdx.current - 1), [restoreHist]);
  const redo = useCallback(() => restoreHist(histIdx.current + 1), [restoreHist]);
  const canUndo = histIdx.current > 0;
  const canRedo = histIdx.current < histRef.current.length - 1;
  void histVer; // re-render trigger for the disabled state above

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      const typing =
        tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable;
      if (e.key === "Escape") { setMenu(null); return; }
      if (!(e.ctrlKey || e.metaKey)) return;
      if (typing) return; // let inputs do their own undo / copy / paste
      const k = e.key.toLowerCase();
      if (k === "z" && !e.shiftKey) { e.preventDefault(); undo(); }
      else if ((k === "z" && e.shiftKey) || k === "y") { e.preventDefault(); redo(); }
      else if (k === "a") { e.preventDefault(); selectAll(); }
      else if (k === "c") { e.preventDefault(); copySelection(); }
      else if (k === "x") { e.preventDefault(); if (copySelection()) deleteSelection(); }
      else if (k === "v") { e.preventDefault(); pasteClipboard(lastPointer.current); }
      else if (k === "d") { e.preventDefault(); if (copySelection()) pasteClipboard(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, selectAll, copySelection, deleteSelection, pasteClipboard]);

  useEffect(() => {
    api.options().then((o) => setImageModels(o.image_models || [])).catch(() => {});
    graphApi.listTemplates().then((r) => setTemplates(r.templates)).catch(() => {});
  }, []);

  // All storyboard shot images of the project — so the "Nguồn ảnh" node can reference
  // generated frames, not just assets. Skip the shot being edited (can't reference itself).
  useEffect(() => {
    if (!projectId) return;
    storyboard.projectShots(projectId).then((r) => setShots(r.shots)).catch(() => {});
    // Every image in the project (Flow) — lets "Nguồn ảnh" reference ALL images, not just
    // assets/storyboard. Best-effort (needs the extension); failure just hides the group.
    api.projectImages(projectId)
      .then((r) => setProjMedia(r.media.map((m) => ({ media_id: m.media_id, name: m.name }))))
      .catch(() => {});
  }, [projectId]);

  // Unified reference list: project assets → storyboard shots → every OTHER project image.
  const images = useMemo<RefImage[]>(() => {
    const out: RefImage[] = [];
    const covered = new Set<string>(); // media_ids already shown as asset/shot
    for (const e of entities) {
      if (e.media_id && e.image_path) {
        out.push({ key: `e:${e.id}`, kind: "entity", label: e.name,
                   media_id: e.media_id, web: e.image_path, entity_id: e.id });
        covered.add(e.media_id);
      }
    }
    // Number scenes by first appearance (projectShots is ordered by scene then shot), so a
    // shot reads "SC001-S001-mô tả" — far easier to find in the dropdown than a bare blurb.
    const sceneNo = new Map<string, number>();
    for (const s of shots)
      if (!sceneNo.has(s.scene_id)) sceneNo.set(s.scene_id, sceneNo.size + 1);
    const pad3 = (n: number) => String(n).padStart(3, "0");
    for (const s of shots) {
      if (s.id === target.id || !s.image_media_id || !s.image_path) continue;
      const desc = (s.description || s.title || "").replace(/\s+/g, " ").trim().slice(0, 40);
      const code = `SC${pad3(sceneNo.get(s.scene_id) || 0)}-S${pad3(s.idx + 1)}`;
      out.push({ key: `s:${s.id}`, kind: "shot",
                 label: desc ? `${code}-${desc}` : code,
                 media_id: s.image_media_id, web: s.image_path });
      covered.add(s.image_media_id);
    }
    // Any remaining project image not already an asset/shot (deduped). Thumbs served locally.
    for (const m of projMedia) {
      if (!m.media_id || covered.has(m.media_id)) continue;
      covered.add(m.media_id);
      out.push({ key: `m:${m.media_id}`, kind: "media",
                 label: (m.name || m.media_id).slice(0, 44),
                 media_id: m.media_id, web: thumbUrl(m.media_id, projectId) });
    }
    return out;
  }, [entities, shots, projMedia, target.id, projectId]);

  // A shot has separate image (storyboard) and video (shots-tab) graphs — keep them apart.
  const goal: "image" | "video" =
    target.goal || (target.kind === "shot" ? "video" : "image");

  useEffect(() => {
    // Cancel a stale in-flight load: the effect re-runs when `entities` arrives, and the
    // graphApi.get of an EARLIER run (fired before entities loaded → a default graph with no
    // source nodes) must NOT overwrite the later, complete one. Without this the empty-entities
    // graph can win the race (esp. under StrictMode's double-invoke) and every "Nguồn ảnh"
    // node disappears even though the shot has reference entities.
    let cancelled = false;
    // The graph about to be loaded is by definition already saved — don't let the autosave
    // mistake it for an edit and write it straight back.
    savedSig.current = null;
    // Saved graphs are serialized WITHOUT the transient _result preview, so re-seed the
    // shot/entity's current media onto the Output node and the gen node(s) feeding it —
    // otherwise reopening a graph for an already-generated image shows blank previews.
    const curSrc = goal === "video" ? target.videoSrc : target.imageSrc;
    const curExt = goal === "video" ? "mp4" : "png";
    const entById = new Map(entities.map((e) => [e.id, e]));

    // If a loaded/default graph has NO source node but the shot DOES reference entities (and
    // those assets are loaded), seed one "Nguồn ảnh" per reference wired into the gen node — so
    // a graph built before assets loaded, or a legacy graph saved without sources, still shows
    // the references the generation actually binds. Only when there are zero sources, so a
    // curated graph (user-arranged/removed sources) is left untouched.
    const ensureRefSources = (nodes: Node[], edges: Edge[]) => {
      const refIds = (target.refEntityIds ?? []).filter((i) => entById.get(i)?.media_id);
      if (!refIds.length || nodes.some((n) => n.type === "source")) return;
      const genTypes = goal === "video" ? ["video"] : ["image", "editImage"];
      const gen = nodes.find((n) => genTypes.includes(n.type!));
      if (!gen) return;
      refIds.forEach((eid, k) => {
        const e = entById.get(eid)!;
        const sid = `src-${eid}`;
        nodes.push({
          id: sid, type: "source", position: { x: 0, y: 200 + k * 150 },
          data: { _type: "source", entity_id: e.id, media_id: e.media_id, web: e.image_path, label: e.name },
        });
        edges.push({ id: `es-${sid}`, source: sid, target: gen.id });
      });
    };

    // Bổ sung node Prompt header/footer cho ĐỒ THỊ CŨ. Trước đây header/footer của dự án
    // được chèn ngầm vào mọi prompt; giờ chỉ chèn khi có node, nên graph đã lưu mà thiếu
    // node sẽ mất phần bọc. Gắn vào MỌI node tạo ảnh/tạo video chưa có, giữ nguyên hành vi.
    // Node để text rỗng ⇒ chạy theo ⚙ Thiết lập dự án, y như cơ chế cũ.
    const ensurePromptWrap = (nodes: Node[], edges: Edge[], legacy: boolean) => {
      // CHỈ vá đồ thị cũ. Đồ thị do editor hiện tại lưu (có `v`) là cố ý, kể cả khi nó không
      // có node nào — người dùng gỡ dây hoặc xoá node là muốn prompt chạy trần.
      if (!legacy) return;
      // Và kể cả với đồ thị cũ: đã có sẵn node bọc thì thôi, đừng đẻ thêm cái thứ hai. Trước
      // đây chỉ kiểm theo id `ph-<gen>`, trong khi đồ thị mặc định đặt tên node là `ph`/`pf`,
      // nên gỡ DÂY (giữ node) là lần mở sau lại mọc ra một node header mới nối thẳng vào.
      if (nodes.some((n) => WRAP_TYPES.includes(n.type as any))) return;
      const gens = nodes.filter((n) => WRAP_TARGETS.includes(n.type!));
      for (const gen of gens) {
        const feeding = new Set(
          edges.filter((e) => e.target === gen.id).map((e) => nodes.find((n) => n.id === e.source)?.type)
        );
        WRAP_TYPES.forEach((wt, k) => {
          if (feeding.has(wt)) return;
          const wid = `${wt === "promptHeader" ? "ph" : "pf"}-${gen.id}`;
          if (nodes.some((n) => n.id === wid)) return;
          nodes.push({
            id: wid,
            type: wt,
            position: { x: (gen.position?.x ?? 340) - 300, y: (gen.position?.y ?? 80) + k * 150 },
            data: { _type: wt, text: "" },
          });
          edges.push({ id: `e-${wid}`, source: wid, target: gen.id });
        });
      }
    };
    const apply = (g: { nodes: any[]; edges: any[] }) => {
      const edges: Edge[] = (g.edges || [])
        .map((e: any, i: number) => ({
          id: e.id || `e${i}`,
          source: e.source,
          target: e.target,
        }))
        // Dọn dây auto-seed của bản defaultGraph cũ, vốn đổ MỌI frame của scene vào node tạo:
        // `sref* → v` (video) và `sshot* → i` (ảnh). Chỉ xoá đúng cặp id+nguồn do code sinh ra
        // — dây người dùng tự kéo mang id `e<timestamp>` nên không bao giờ khớp.
        .filter(
          (e) =>
            !(/^esr\d+$/.test(e.id) && /^sref\d+$/.test(e.source)) &&
            !(/^ess\d+$/.test(e.id) && /^sshot\d+$/.test(e.source))
        );
      const wired = new Set(edges.flatMap((e) => [e.source, e.target]));
      const nodes: Node[] = g.nodes
        // Dọn "kệ" node Nguồn ảnh mà defaultGraph cũ gieo sẵn: MỌI frame khác trong cùng
        // scene, mỗi cái một node không nối dây. Đường gieo đã bỏ, nhưng đồ thị đã lưu từ
        // trước vẫn mang chúng theo — mở một shot trong scene 20 frame là 20 node phải xoá
        // tay. Nhận diện bằng đúng id do code ấy sinh (`sref0`, `sshot3`…): node người dùng
        // tự thêm mang id `source-<timestamp>` nên không bao giờ khớp.
        // CÒN DÂY thì GIỮ: kéo dây vào là cố ý dùng frame đó làm tham chiếu, xoá đi là đổi
        // kết quả render sau lưng người dùng. Chỉ dọn node nằm không.
        .filter((n: any) => !(
          (n.type || n.data?._type) === "source" &&
          /^(sref|sshot)\d+$/.test(n.id || "") &&
          !wired.has(n.id)))
        .map((n: any) => ({
          id: n.id,
          type: n.type || n.data?._type || "prompt",
          position: n.position || { x: 0, y: 0 },
          data: { ...n.data, _type: n.type || n.data?._type },
        }));
      // Refresh entity-bound source nodes to the entity's CURRENT image, so regenerating a
      // location/character updates its reference node instead of keeping the stale snapshot.
      for (const n of nodes) {
        const d = n.data as any;
        if (n.type === "source" && d.entity_id) {
          const e = entById.get(d.entity_id);
          if (e && e.media_id) {
            d.media_id = e.media_id;
            d.web = e.image_path;
            d.label = e.name;
          }
        }
        // Sync the prompt node to the target's CURRENT description (e.g. after "Đa dạng góc
        // máy" / an edit) so the node editor and the storyboard table use the same prompt.
        // Only when it was untouched since seeding, so manual prompt edits are preserved.
        // Only the SEEDED prompt node (id "p", from defaultGraph) is refreshed — a prompt
        // node the user added themselves carries its own text and must never be replaced
        // by the target's description. Legacy seeded nodes have no seed_prompt → treat as
        // unedited so old stale graphs still refresh.
        if (n.type === "prompt" && target.prompt != null) {
          const unedited =
            d.seed_prompt == null ? n.id === "p" : d.text === d.seed_prompt;
          if (unedited && d.text !== target.prompt) {
            d.text = target.prompt;
            d.seed_prompt = target.prompt;
          }
        }
      }
      // Restoring each node's own stored result must NOT depend on the target having a
      // committed image: a graph whose result was never applied (quick-gen on a mid-chain
      // node, a brand-new shot/entity) still has result_web on those nodes, and gating the
      // whole loop on `curSrc` made every preview come back blank as if nothing was saved.
      const outIds = new Set(nodes.filter((n) => n.type === "output").map((n) => n.id));
      const feedsOut = new Set(
        edges.filter((e) => outIds.has(e.target)).map((e) => e.source)
      );
      const GEN = ["image", "editImage", "video"];
      for (const n of nodes) {
        const d = n.data as any;
        const seedHere =
          !!curSrc && (outIds.has(n.id) || (GEN.includes(n.type!) && feedsOut.has(n.id)));
        if (seedHere) {
          // The Output (and the gen node feeding it) shows the target's CURRENT committed
          // image, so a quick-gen done outside the editor isn't shown as the stale old one.
          d._result = curSrc;
          d._ext = curExt;
        } else if (d.result_web && !d._result) {
          // every other node keeps its own last produced result
          d._result = d.result_web;
          d._ext = d.result_ext || "png";
        }
      }
      ensureRefSources(nodes, edges);
      ensurePromptWrap(nodes, edges, !(g as any).v);
      if (cancelled) return;       // a newer load supersedes this one — don't clobber it
      setNodes(nodes);
      setEdges(edges);
    };
    graphApi
      .get(target.kind, target.id, goal)
      .then((r) => apply(r.graph && r.graph.nodes?.length
        ? r.graph
        : defaultGraph(target, entities, { engine: projEngine, aspect: projAspect })))
      .catch(() => apply(defaultGraph(target, entities,
        { engine: projEngine, aspect: projAspect })));
    return () => { cancelled = true; };
  }, [target.id, entities, goal]);

  const onConnect = useCallback(
    (c: Connection) => setEdges((es) => addEdge({ ...c, id: `e${Date.now()}` }, es)),
    [setEdges]
  );

  // Delete a connection by grabbing one of its endpoints and dropping it on empty space
  // (drag off the connector). A plain click no longer removes anything, so a misclick in
  // a busy graph is harmless. If dropped on another valid handle it's reconnected instead.
  const reconnectOk = useRef(true);
  const onReconnectStart = useCallback(() => {
    reconnectOk.current = false;
  }, []);
  const onReconnect = useCallback(
    (oldEdge: Edge, newConn: Connection) => {
      reconnectOk.current = true;
      setEdges((es) => reconnectEdge(oldEdge, newConn, es));
    },
    [setEdges]
  );
  const onReconnectEnd = useCallback(
    (_: unknown, edge: Edge) => {
      if (!reconnectOk.current) setEdges((es) => es.filter((e) => e.id !== edge.id));
      reconnectOk.current = true;
    },
    [setEdges]
  );

  // Build a fresh node of `type` at `pos` (defaults to a small random offset). Used by the
  // palette "+ " buttons AND by dragging a palette chip onto the canvas.
  const NODE_DEFAULTS: Record<string, any> = {
    // seed_prompt "" marks this as a hand-authored prompt: once the user types anything
    // text !== seed_prompt, so the load-time sync to target.prompt leaves it alone.
    prompt: { text: "", seed_prompt: "" },
    // text rỗng = chạy theo prompt_header/footer của ⚙ Thiết lập dự án
    promptHeader: { text: "" },
    promptFooter: { text: "" },
    refs: { entity_ids: [] },
    image: { aspect: "16:9", model: "", count: 1 },
    editImage: { aspect: "16:9", model: "", count: 1 },
    removebg: { bg: "white" },
    replacebg: { text: "" },
    border: { width: 0.04, color: "#000000" },
    colorgrade: { preset: "teal_orange", intensity: 1 },
    collage: { cols: 0, gap: 8, bg: "#000000" },
    watermark: { position: "bottom-right", scale: 0.18, opacity: 0.85 },
    note: { text: "" },
    // Model + tỷ lệ lấy theo ⚙ Cấu hình dự án làm giá trị khởi đầu (đổi trên node sau vẫn
    // được — đây là điểm xuất phát, không phải ràng buộc).
    // No `duration`: a fresh video node follows ⚙ Cấu hình dự án (VideoNode shows the
    // effective value, the backend falls back the same way).
    video: { aspect: projAspect, model: projEngine, lite_mode: "inference", count: 1 },
    filter: { brightness: 1, contrast: 1, saturation: 1, sharpness: 1, blur: 0, rotate: 0 },
    text: { text: "", anchor: "bottom", color: "#ffffff", font_scale: 0.06, stroke: true },
    upscale: { scale: 2, sharpen: true },
    crop: { aspect: "free", zoom: 1 },
    vignette: { strength: 0.5 },
    blend: { mode: "alpha", alpha: 0.5 },
  };
  const addNode = useCallback(
    (type: string, pos?: { x: number; y: number }) => {
      const id = `${type}-${Date.now()}`;
      const data = { _type: type, ...(NODE_DEFAULTS[type] || {}) };
      const position = pos || { x: 80 + Math.random() * 160, y: 80 + Math.random() * 200 };
      setNodes((ns) => [...ns, { id, type, position, data }]);
    },
    // projEngine/projAspect nằm trong NODE_DEFAULTS — thiếu ở deps thì callback giữ mãi bản
    // dựng ở lần render đầu và node video mới lại ra giá trị cũ.
    [setNodes, projEngine, projAspect]
  );

  // Drag a palette chip / an image file onto the canvas → create a node at the drop point.
  const rf = useReactFlow();
  const NODE_DND_MIME = "application/flowkit-node";
  const onPaneDragOver = useCallback((e: React.DragEvent) => {
    const types = Array.from(e.dataTransfer?.types || []);
    if (types.includes("Files") || types.includes(NODE_DND_MIME)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = types.includes("Files") ? "copy" : "move";
    }
  }, []);
  const onPaneDrop = useCallback(
    async (e: React.DragEvent) => {
      // 1) a node type dragged from the palette
      const dndType = e.dataTransfer?.getData(NODE_DND_MIME);
      if (dndType) {
        e.preventDefault();
        addNode(dndType, rf.screenToFlowPosition({ x: e.clientX, y: e.clientY }));
        return;
      }
      // 2) image file(s) from the desktop → uploaded "Nguồn ảnh" node(s)
      const files = Array.from(e.dataTransfer?.files || []).filter((f) => f.type.startsWith("image/"));
      if (!files.length) return;
      e.preventDefault();
      const at = rf.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        const id = `source-${Date.now()}-${i}`;
        setNodes((ns) => [
          ...ns,
          { id, type: "source", position: { x: at.x + i * 36, y: at.y + i * 36 },
            data: { _type: "source", label: "Đang tải…" } },
        ]);
        try {
          const r = await api.uploadImage(projectId, f);
          update(id, { media_id: r.media_id, web: r.web, label: r.name || "ảnh tải lên" });
        } catch (err: any) {
          update(id, { label: "Tải lỗi" });
          setErr(err.message || "Upload lỗi");
        }
      }
    },
    [rf, projectId, setNodes, update, addNode]
  );

  // Auto-arrange nodes left→right by topological layer (longest-path depth), stacked within
  // each layer. Untouched media/results — only positions change. Then fit the view.
  const autoLayout = useCallback(() => {
    const indeg = new Map(nodes.map((n) => [n.id, 0]));
    const adj = new Map<string, string[]>(nodes.map((n) => [n.id, []]));
    for (const e of edges) {
      if (indeg.has(e.source) && indeg.has(e.target)) {
        adj.get(e.source)!.push(e.target);
        indeg.set(e.target, (indeg.get(e.target) || 0) + 1);
      }
    }
    const layer = new Map<string, number>();
    const ind = new Map(indeg);
    const queue = [...indeg].filter(([, d]) => d === 0).map(([id]) => id);
    queue.forEach((id) => layer.set(id, 0));
    while (queue.length) {
      const id = queue.shift()!;
      const l = layer.get(id) || 0;
      for (const t of adj.get(id) || []) {
        layer.set(t, Math.max(layer.get(t) ?? 0, l + 1));
        ind.set(t, (ind.get(t) || 0) - 1);
        if ((ind.get(t) || 0) === 0) queue.push(t);
      }
    }
    const byLayer = new Map<number, string[]>();
    for (const n of nodes) {
      const l = layer.get(n.id) ?? 0; // cycle leftovers → layer 0
      (byLayer.get(l) || byLayer.set(l, []).get(l)!).push(n.id);
    }
    const COLW = 300, ROWH = 200;
    const pos = new Map<string, { x: number; y: number }>();
    for (const [l, ids] of byLayer)
      ids.forEach((id, i) => pos.set(id, { x: l * COLW, y: i * ROWH }));
    setNodes((ns) => ns.map((n) => (pos.has(n.id) ? { ...n, position: pos.get(n.id)! } : n)));
    setTimeout(() => rf.fitView({ padding: 0.2, duration: 300 }), 60);
  }, [nodes, edges, setNodes, rf]);

  // ── Graph presets (templates) — reuse a chain across shots/assets ──
  // A preset is a STRUCTURE, not a result: strip the per-asset output ids and the locks,
  // otherwise loading it elsewhere would reuse the preset author's media (a locked node with
  // a stored result_media_id is served as-is by the runner instead of regenerating).
  const stripAssetState = (g: { nodes: any[]; edges: any[] }) => ({
    ...g,
    nodes: g.nodes.map((n) => {
      const { result_media_id, result_web, result_ext, locked, ...data } = n.data || {};
      return { ...n, data };
    }),
  });
  const saveAsPreset = async () => {
    const name = window.prompt("Tên preset cho sơ đồ node hiện tại:");
    if (!name?.trim()) return;
    try {
      const r = await graphApi.saveTemplate(name.trim(), stripAssetState(serialize()), goal);
      setTemplates(r.templates);
    } catch (e: any) {
      setErr(e.message);
    }
  };
  const loadPreset = (tid: string) => {
    const t = templates.find((x) => x.id === tid);
    if (!t) return;
    if (!window.confirm(`Thay sơ đồ hiện tại bằng preset "${t.name}"?`)) return;
    const ns: Node[] = (t.graph.nodes || []).map((n: any) => {
      // Also strip here, so presets saved BEFORE stripAssetState existed don't drag another
      // asset's locked results into this graph.
      const { result_media_id, result_web, result_ext, locked, ...data } = n.data || {};
      return {
        id: n.id,
        type: n.type || n.data?._type || "prompt",
        position: n.position || { x: 0, y: 0 },
        data: { ...data, _type: n.type || n.data?._type },
      };
    });
    const es: Edge[] = (t.graph.edges || []).map((e: any, i: number) => ({
      id: e.id || `e${i}`, source: e.source, target: e.target,
    }));
    setResults({});
    setNodes(ns);
    setEdges(es);
  };
  const deletePreset = async (tid: string) => {
    const t = templates.find((x) => x.id === tid);
    if (!t || !window.confirm(`Xóa preset "${t.name}"?`)) return;
    try {
      const r = await graphApi.deleteTemplate(tid);
      setTemplates(r.templates);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Drop transient preview fields; keep durable ones (locked + result_* so locks persist).
  const serializeGraph = (ns: Node[], es: Edge[]) => ({
    // `v` = đồ thị này do BẢN EDITOR NÀY lưu, nên hình dạng của nó là CỐ Ý. Không có `v` là
    // đồ thị lưu từ trước khi có node prompt header/footer, và chỉ đồ thị ấy mới được vá
    // thêm node. Thiếu dấu này thì "thiếu node" và "người dùng đã xoá node" trông y hệt nhau,
    // nên bản vá cứ chạy lại mỗi lần mở và dựng lại đúng thứ vừa bị xoá — xem GRAPH_V.
    v: GRAPH_V,
    nodes: ns.map((n) => {
      const { _result, _ext, preview, ...rest } = n.data as any;
      return { id: n.id, type: n.type, data: rest, position: n.position };
    }),
    edges: es.map((e) => ({ source: e.source, target: e.target })),
  });
  const serialize = () => serializeGraph(nodes, edges);

  type Out = { web?: string; media_id?: string; ext?: string };

  // Fold a run's node_outputs into the live preview map + node data (durable result ids
  // so a locked node can be reused on the next run), and persist so it survives reopen.
  const applyOutputs = (outs: Record<string, Out>) => {
    const mapped: Record<string, { web: string; ext: string }> = {};
    for (const [k, v] of Object.entries(outs)) {
      if (v?.web) mapped[k] = { web: v.web, ext: v.ext || (v.web.toLowerCase().endsWith(".mp4") ? "mp4" : "png") };
    }
    setResults((prev) => ({ ...prev, ...mapped }));
    setNodes((ns) => {
      const next = ns.map((n) => {
        const v = outs[n.id];
        if (!v?.web) return n;
        return {
          ...n,
          data: {
            ...n.data,
            _result: v.web,
            _ext: v.ext,
            result_media_id: v.media_id,
            result_web: v.web,
            result_ext: v.ext,
          },
        };
      });
      graphApi.save(target.kind, target.id, serializeGraph(next, edges), goal).catch(() => {});
      return next;
    });
  };

  // The button used to fire a floating promise: no confirmation on success and a rejection
  // swallowed into the console, so "Lưu" looked identical whether it worked or failed.
  const save = async () => {
    try {
      await graphApi.save(target.kind, target.id, serialize(), goal);
      savedSig.current = sigOf(nodes, edges);   // keep the autosave from re-writing the same graph
      setErr(null);
      setSaveMsg("✓ Đã lưu");
      setTimeout(() => setSaveMsg(null), 2000);
    } catch (e: any) {
      setErr(e.message || "Lưu đồ thị lỗi");
    }
  };

  // Autosave. Before this, the graph reached the server only from a run or the "Lưu" button,
  // so uploading a picture into a "Nguồn ảnh" node, rewiring, or changing a setting and then
  // closing the editor threw the work away. Keyed on the same durable signature the undo
  // history uses (positions + settings + structure, results excluded — those are persisted by
  // applyOutputs), and skipped for the first settle, which is just the graph we loaded.
  useEffect(() => {
    if (!nodes.length) return;
    const sig = sigOf(nodes, edges);
    if (savedSig.current === null || savedSig.current === sig) {
      savedSig.current = sig;
      return;
    }
    const tid = setTimeout(() => {
      savedSig.current = sig;
      graphApi.save(target.kind, target.id, serializeGraph(nodes, edges), goal).catch(() => {});
    }, 700);
    return () => clearTimeout(tid);
  }, [nodes, edges, sigOf, target.kind, target.id, goal]);

  // After a generation commits, the entity/shot may SHOW a different image than the raw node
  // media (e.g. a location grid gets position labels overlaid). Reflect that committed image
  // on the Output node + the gen node feeding it, so the editor shows labels like quick-gen.
  const reflectDisplay = (path?: string, ext?: string) => {
    if (!path) return;
    const outIds = new Set(nodes.filter((n) => n.type === "output").map((n) => n.id));
    const ids = new Set<string>(outIds);
    for (const e of edges) if (outIds.has(e.target)) ids.add(e.source);
    setResults((prev) => {
      const next = { ...prev };
      for (const id of ids) next[id] = { web: path, ext: ext || "png" };
      return next;
    });
    setNodes((ns) =>
      ns.map((n) =>
        ids.has(n.id) ? { ...n, data: { ...n.data, _result: path, _ext: ext || "png" } } : n
      )
    );
  };

  const run = async () => {
    setBusy(true);
    setErr(null);
    setDone(false);
    try {
      const r = await graphApi.run(target.kind, target.id, serialize(), goal);
      applyOutputs((r.node_outputs || {}) as Record<string, Out>);
      reflectDisplay(r.display_path, r.ext);
      setDone(true);
      onApplied(r);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  // Generate one node (+ its upstream chain). propagate=true also refreshes everything
  // DOWNSTREAM of it (the ⏬ button) so a change flows through the whole chain.
  const genNode = useCallback(
    async (id: string, propagate = false) => {
      setGenningId(id);
      setErr(null);
      try {
        const r = await graphApi.run(target.kind, target.id, serialize(), goal, id, propagate);
        const outs = (r.node_outputs || {}) as Record<string, Out>;
        applyOutputs(outs);
        // If this regenerated the node feeding the Output, commit that media to the
        // shot/entity so the storyboard/asset reflects it (quick-gen alone doesn't apply).
        const outNode = nodes.find((n) => n.type === "output");
        const up = outNode && edges.find((e) => e.target === outNode.id)?.source;
        const m = up ? outs[up] : undefined;
        if (m?.media_id) {
          const ext = m.ext || "png";
          const applied = await graphApi.applyMedia(target.kind, target.id, m.media_id, ext);
          onApplied(r);
          // Show the committed media (e.g. labeled location grid) in the previews. Với mp4 phải
          // đọc `video_path` — trước đây luôn lấy `image_path`, nên quick-gen video ghi đè
          // preview bằng ảnh frame và trông như "không lấy được video về" dù clip đã tải xong.
          reflectDisplay(
            ext === "mp4"
              ? applied?.shot?.video_path || applied?.path || m.web
              : applied?.entity?.image_path || applied?.shot?.image_path || applied?.path,
            ext
          );
        }
      } catch (e: any) {
        setErr(e.message);
        // Một lượt render video hỏng vì hết giờ chờ vẫn ghi operation_json lên shot — refresh
        // để thẻ shot hiện nút "Lấy lại video" ngay, khỏi phải tải lại trang.
        onApplied({ failed: true });
      } finally {
        setGenningId(null);
      }
    },
    // serialize/applyOutputs close over nodes+edges; recreate when they change.
    [nodes, edges, goal, target.kind, target.id, onApplied]
  );

  const preview = useCallback((src: string, video: boolean) => setLightbox({ src, video }), []);

  // For each node, the effective media coming from its upstream (run result > stored
  // result > seeded preview > source image). Downstream nodes (e.g. Output) read this.
  const inputResults = useMemo(() => {
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const eff = (n?: Node): { web: string; ext: string } | null => {
      if (!n) return null;
      const r = results[n.id];
      if (r?.web) return r;
      const d = n.data as any;
      // Prefer _result (the current display/seed value, refreshed to the committed image on
      // load) over result_web (the durable stored result) so the Output node doesn't show a
      // stale image after a quick-gen done outside the editor. After a run they're equal.
      if (d._result) return { web: d._result, ext: d._ext || "png" };
      if (d.result_web) return { web: d.result_web, ext: d.result_ext || "png" };
      if (d.web) return { web: d.web, ext: "png" }; // source node
      return null;
    };
    const map: Record<string, { web: string; ext: string }> = {};
    for (const e of edges) {
      const r = eff(byId.get(e.source));
      if (r?.web) map[e.target] = r;
    }
    return map;
  }, [nodes, edges, results]);

  // The media_id currently designated by the Output node (its upstream's result) — lets
  // us commit an already-generated result to the target without re-running anything.
  const outputMedia = useMemo(() => {
    const out = nodes.find((n) => n.type === "output");
    if (!out) return null;
    const upId = edges.find((e) => e.target === out.id)?.source;
    const up = nodes.find((n) => n.id === upId);
    if (!up) return null;
    const d = up.data as any;
    const media_id = d.result_media_id || d.media_id;
    const ext = d.result_ext || (up.type === "video" ? "mp4" : "png");
    return media_id ? { media_id, ext } : null;
  }, [nodes, edges]);

  const applyOutput = async () => {
    if (!outputMedia) {
      setErr("Node Output chưa có ảnh/video — hãy nối Output tới một node có kết quả.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await graphApi.applyMedia(target.kind, target.id, outputMedia.media_id, outputMedia.ext);
      setDone(true);
      onApplied({ applied: true, media_id: outputMedia.media_id });
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const ops = useMemo(
    () => ({ update, remove, duplicate, bindEntitySource, bindNodeSource, preview, genNode, genningId, results, inputResults, entities, images, imageModels, projectId, projDur, projectHeader, projectFooter, handles, handleDupes, upstreamHandles }),
    [update, remove, duplicate, bindEntitySource, bindNodeSource, preview, genNode, genningId, results, inputResults, entities, images, imageModels, projectId, projDur, projectHeader, projectFooter, handles, handleDupes, upstreamHandles]
  );

  return (
    <div className="fixed inset-0 z-[70] flex flex-col bg-neutral-950">
      <div className="flex items-center gap-3 border-b border-neutral-800 px-4 py-2.5">
        <span className="font-medium">Node Editor — {target.title}</span>
        <div className="ml-2 flex flex-wrap gap-1">
          {PALETTE.map((p) => (
            <button
              key={p}
              onClick={() => addNode(p)}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData("application/flowkit-node", p);
                e.dataTransfer.effectAllowed = "move";
              }}
              title="Bấm để thêm, hoặc kéo thả xuống canvas"
              className="cursor-grab rounded-md border border-neutral-700 px-2 py-1 text-xs hover:bg-neutral-800 active:cursor-grabbing"
              style={{ borderLeftColor: META[p].color, borderLeftWidth: 3 }}
            >
              + {META[p].label}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          {done && <span className="text-xs text-emerald-400">✓ Đã tạo & áp dụng</span>}
          {saveMsg && <span className="text-xs text-emerald-400">{saveMsg}</span>}
          <div className="flex items-center gap-1">
            <button onClick={undo} disabled={!canUndo} title="Hoàn tác (Ctrl+Z)"
              className="rounded-lg border border-neutral-700 px-2 py-1.5 text-xs hover:bg-neutral-800 disabled:opacity-30">
              ↶
            </button>
            <button onClick={redo} disabled={!canRedo} title="Làm lại (Ctrl+Shift+Z)"
              className="rounded-lg border border-neutral-700 px-2 py-1.5 text-xs hover:bg-neutral-800 disabled:opacity-30">
              ↷
            </button>
            <button onClick={autoLayout} title="Tự sắp xếp node theo luồng"
              className="rounded-lg border border-neutral-700 px-2 py-1.5 text-xs hover:bg-neutral-800">
              ⤢ Sắp xếp
            </button>
            <button
              onClick={() => setBoxSelect((b) => !b)}
              title="Kéo chuột trái để khoanh vùng chọn nhiều node (giữ Shift cũng được). Ctrl+C/V/X/D · Del · kéo để di chuyển cả nhóm"
              className={`rounded-lg border px-2 py-1.5 text-xs ${
                boxSelect
                  ? "border-indigo-500 bg-indigo-600/20 text-indigo-300"
                  : "border-neutral-700 hover:bg-neutral-800"
              }`}
            >
              ▭ Chọn vùng
            </button>
            {selectedIds.size > 1 && (
              <span className="px-1 text-[11px] text-indigo-300">{selectedIds.size} node</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <select
              value={presetSel}
              onChange={(e) => { setPresetSel(e.target.value); if (e.target.value) loadPreset(e.target.value); }}
              title="Nạp một preset sơ đồ node đã lưu"
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-xs text-neutral-300 outline-none"
            >
              <option value="">Preset…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.name}{t.goal ? ` (${t.goal})` : ""}</option>
              ))}
            </select>
            {presetSel && (
              <button onClick={() => deletePreset(presetSel)} title="Xóa preset đang chọn"
                className="rounded-lg border border-neutral-700 px-2 py-1.5 text-xs text-rose-300 hover:bg-rose-950/40">
                🗑
              </button>
            )}
            <button onClick={saveAsPreset} title="Lưu sơ đồ hiện tại thành preset"
              className="rounded-lg border border-neutral-700 px-2 py-1.5 text-xs hover:bg-neutral-800">
              💾 Preset
            </button>
          </div>
          <button onClick={save} className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800">
            Lưu
          </button>
          <button
            onClick={applyOutput}
            disabled={busy || !outputMedia}
            title="Đưa ảnh/video ở node Output vào dự án (không tạo lại)"
            className="rounded-lg border border-emerald-700/60 px-3 py-1.5 text-sm text-emerald-300 hover:bg-emerald-950/40 disabled:opacity-40"
          >
            ✓ Áp dụng Output
          </button>
          <button
            onClick={run}
            disabled={busy}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            {busy ? "Đang chạy…" : "▶ Run"}
          </button>
          <button
            // Flush before leaving: an edit made inside the autosave debounce window would
            // otherwise die with the component.
            onClick={() => {
              graphApi.save(target.kind, target.id, serialize(), goal).catch(() => {});
              onClose();
            }}
            className="rounded-lg px-3 py-1.5 text-sm text-neutral-400 hover:bg-neutral-800"
          >
            Đóng
          </button>
        </div>
      </div>
      {err && <div className="bg-rose-950/50 px-4 py-1.5 text-sm text-rose-300">{err}</div>}
      <div
        className="relative flex-1"
        onDrop={onPaneDrop}
        onDragOver={onPaneDragOver}
        // Remember where the cursor is so Ctrl+V drops the group under it.
        onMouseMove={(e) => {
          lastPointer.current = rf.screenToFlowPosition({ x: e.clientX, y: e.clientY });
        }}
      >
        <NodeOps.Provider value={ops}>
          <ReactFlow
            nodes={nodes}
            edges={displayEdges}
            nodeTypes={NODE_TYPES}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onReconnect={onReconnect}
            onReconnectStart={onReconnectStart}
            onReconnectEnd={onReconnectEnd}
            onNodeClick={(_, n) => { setActiveId(n.id); setMenu(null); }}
            onPaneClick={() => { setActiveId(null); setMenu(null); }}
            onEdgeMouseEnter={(_, e) => setHoverEdge(e.id)}
            onEdgeMouseLeave={() => setHoverEdge(null)}
            // Right-click menus — the unambiguous way to cut a connection, and the entry
            // point for the group actions.
            onEdgeContextMenu={(ev, e) => {
              ev.preventDefault();
              setMenu({ kind: "edge", id: e.id, x: ev.clientX, y: ev.clientY });
            }}
            onNodeContextMenu={(ev, n) => {
              ev.preventDefault();
              setActiveId(n.id);
              setMenu({ kind: "node", id: n.id, x: ev.clientX, y: ev.clientY });
            }}
            onSelectionContextMenu={(ev) => {
              ev.preventDefault();
              setMenu({ kind: "selection", x: ev.clientX, y: ev.clientY });
            }}
            onPaneContextMenu={(ev) => {
              ev.preventDefault();
              const m = ev as unknown as MouseEvent;
              setMenu({
                kind: "pane",
                x: m.clientX,
                y: m.clientY,
                at: rf.screenToFlowPosition({ x: m.clientX, y: m.clientY }),
              });
            }}
            // Shift+drag always box-selects; the ▭ toggle makes a plain left-drag do it too
            // (middle-drag still pans). Ctrl/Cmd+click adds single nodes to the selection.
            selectionOnDrag={boxSelect}
            panOnDrag={boxSelect ? [1] : true}
            // Chạm vào là dính: khung chỉ cần cắt qua một phần node (mặc định của React Flow
            // là phải trùm trọn cả node mới chọn được — rất khó với các node cao).
            selectionMode={SelectionMode.Partial}
            selectionKeyCode="Shift"
            multiSelectionKeyCode={["Meta", "Control"]}
            edgesReconnectable
            deleteKeyCode={["Backspace", "Delete"]}
            connectionLineStyle={{ strokeWidth: 4, stroke: "#818cf8" }}
            defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed } }}
            fitView
            minZoom={0.3}
            colorMode="dark"
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} color="#1f2937" />
            <Controls />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => META[(n.type as string) || "output"]?.color || "#64748b"}
              maskColor="rgba(0,0,0,0.6)"
              style={{ background: "#0e1411", border: "1px solid #1f2937" }}
            />
          </ReactFlow>
        </NodeOps.Provider>
        {menu && (
          <>
            {/* click anywhere (or right-click again) to dismiss */}
            <div
              className="fixed inset-0 z-[80]"
              onMouseDown={() => setMenu(null)}
              onContextMenu={(e) => { e.preventDefault(); setMenu(null); }}
            />
            <div
              className="fixed z-[81] max-h-[70vh] min-w-[230px] max-w-[340px] overflow-y-auto rounded-lg border border-neutral-700 bg-neutral-900 py-1 text-xs shadow-2xl"
              style={{
                left: Math.min(menu.x, Math.max(8, window.innerWidth - 350)),
                top: Math.min(menu.y, Math.max(8, window.innerHeight - 320)),
              }}
            >
              {menu.kind === "edge" && (() => {
                const e = edges.find((x) => x.id === menu.id);
                if (!e) return null;
                return (
                  <>
                    <div className={menuHeadCls}>Kết nối</div>
                    <div className="px-3 pb-2 text-[11px] leading-snug text-neutral-300">
                      {nodeLabel(e.source)}
                      <span className="mx-1 text-neutral-500">→</span>
                      {nodeLabel(e.target)}
                    </div>
                    <div className={menuSepCls} />
                    <button className={menuDangerCls}
                      onClick={() => { removeEdge(e.id); setMenu(null); }}>
                      🗑 Xóa kết nối này
                    </button>
                    <button className={menuItemCls}
                      onClick={() => { removeEdgesOf(e.target, "in"); setMenu(null); }}>
                      ✂ Ngắt mọi kết nối vào {nodeLabel(e.target)}
                    </button>
                  </>
                );
              })()}

              {menu.kind === "node" && (() => {
                const id = menu.id;
                const ins = edges.filter((e) => e.target === id);
                const outs = edges.filter((e) => e.source === id);
                const inGroup = selectedIds.size > 1 && selectedIds.has(id);
                return (
                  <>
                    <div className={menuHeadCls}>{nodeLabel(id)}</div>
                    {inGroup && (
                      <>
                        <button className={menuItemCls}
                          onClick={() => { copySelection(); setMenu(null); }}>
                          ⧉ Sao chép {selectedIds.size} node <span className={menuKeyCls}>Ctrl+C</span>
                        </button>
                        <button className={menuItemCls}
                          onClick={() => { if (copySelection()) pasteClipboard(null); setMenu(null); }}>
                          ⎘ Nhân bản nhóm <span className={menuKeyCls}>Ctrl+D</span>
                        </button>
                        <button className={menuDangerCls}
                          onClick={() => { deleteSelection(); setMenu(null); }}>
                          🗑 Xóa {selectedIds.size} node <span className={menuKeyCls}>Del</span>
                        </button>
                        <div className={menuSepCls} />
                      </>
                    )}
                    <button className={menuItemCls}
                      onClick={() => { genNode(id); setMenu(null); }}>
                      ⚡ Tạo riêng node này
                    </button>
                    <button className={menuItemCls}
                      onClick={() => { duplicate(id); setMenu(null); }}>
                      ⧉ Nhân bản node
                    </button>
                    <button className={menuDangerCls}
                      onClick={() => { remove(id); setMenu(null); }}>
                      ✕ Xóa node
                    </button>
                    {(ins.length > 0 || outs.length > 0) && (
                      <>
                        <div className={menuSepCls} />
                        <div className={menuHeadCls}>Ngắt kết nối</div>
                        {ins.map((e) => (
                          <button key={e.id} className={menuItemCls}
                            onMouseEnter={() => setHoverEdge(e.id)}
                            onMouseLeave={() => setHoverEdge(null)}
                            onClick={() => { removeEdge(e.id); setMenu(null); setHoverEdge(null); }}>
                            <span className="text-sky-400">←</span> từ {nodeLabel(e.source)}
                          </button>
                        ))}
                        {outs.map((e) => (
                          <button key={e.id} className={menuItemCls}
                            onMouseEnter={() => setHoverEdge(e.id)}
                            onMouseLeave={() => setHoverEdge(null)}
                            onClick={() => { removeEdge(e.id); setMenu(null); setHoverEdge(null); }}>
                            <span className="text-emerald-400">→</span> tới {nodeLabel(e.target)}
                          </button>
                        ))}
                        {ins.length + outs.length > 1 && (
                          <button className={menuDangerCls}
                            onClick={() => { removeEdgesOf(id, "all"); setMenu(null); }}>
                            ✂ Ngắt tất cả ({ins.length + outs.length})
                          </button>
                        )}
                      </>
                    )}
                  </>
                );
              })()}

              {menu.kind === "selection" && (
                <>
                  <div className={menuHeadCls}>{selectedIds.size} node đã chọn</div>
                  <button className={menuItemCls}
                    onClick={() => { copySelection(); setMenu(null); }}>
                    ⧉ Sao chép <span className={menuKeyCls}>Ctrl+C</span>
                  </button>
                  <button className={menuItemCls}
                    onClick={() => { if (copySelection()) pasteClipboard(null); setMenu(null); }}>
                    ⎘ Nhân bản nhóm <span className={menuKeyCls}>Ctrl+D</span>
                  </button>
                  <button className={menuItemCls}
                    onClick={() => { if (copySelection()) deleteSelection(); setMenu(null); }}>
                    ✂ Cắt <span className={menuKeyCls}>Ctrl+X</span>
                  </button>
                  <button className={menuDangerCls}
                    onClick={() => { deleteSelection(); setMenu(null); }}>
                    🗑 Xóa nhóm <span className={menuKeyCls}>Del</span>
                  </button>
                </>
              )}

              {menu.kind === "pane" && (
                <>
                  <button
                    className={menuItemCls}
                    disabled={!clipCount}
                    onClick={() => { pasteClipboard(menu.at); setMenu(null); }}
                  >
                    📋 Dán {clipCount ? `${clipCount} node ` : ""}tại đây <span className={menuKeyCls}>Ctrl+V</span>
                  </button>
                  <button className={menuItemCls} onClick={() => { selectAll(); setMenu(null); }}>
                    ☑ Chọn tất cả <span className={menuKeyCls}>Ctrl+A</span>
                  </button>
                  <button className={menuItemCls}
                    onClick={() => { setBoxSelect((b) => !b); setMenu(null); }}>
                    ▭ Chọn vùng: {boxSelect ? "đang bật" : "đang tắt"}
                  </button>
                  <div className={menuSepCls} />
                  <button className={menuItemCls} onClick={() => { autoLayout(); setMenu(null); }}>
                    ⤢ Tự sắp xếp
                  </button>
                </>
              )}
            </div>
          </>
        )}
      </div>
      <div className="border-t border-neutral-800 px-4 py-1 text-[11px] text-neutral-500">
        ⓘ {"{định danh}"} trên mỗi node ảnh: gõ {"{tên}"} trong prompt để chỉ đích danh ảnh đó (vd. "cho {"{Nam}"} mặc {"{Áo khoác}"}") · ⚡ Tạo riêng 1 node · ⏬ Cập nhật xuôi dòng · 🔒 Khóa · ⧉ Nhân bản node · 💾 Preset để lưu/nạp sơ đồ ·Filter/Color grade/Crop/Vignette/Khung/Ghép/Lưới/Watermark chạy cục bộ (không gọi AI, nhanh) · Chỉ node Tạo video mới trừ credit — mọi thao tác ảnh đều miễn phí ·Kéo-thả ảnh từ máy vào canvas để tạo Nguồn ảnh · Nhấn ảnh để phóng to · <b className="text-neutral-400">Chuột phải vào đường nối để xóa</b> (hoặc kéo đầu nối ra chỗ trống) · <b className="text-neutral-400">Shift+kéo</b> hoặc ▭ để chọn nhóm → Ctrl+C/V/X/D, Del, kéo để di chuyển cả nhóm
      </div>
      {lightbox && (
        <Lightbox
          imageSrc={lightbox.video ? undefined : lightbox.src}
          videoSrc={lightbox.video ? lightbox.src : undefined}
          onClose={() => setLightbox(null)}
        />
      )}
    </div>
  );
}

export default function NodeEditor(props: {
  target: EditorTarget;
  entities: Entity[];
  projectId: string;
  videoModel?: string | null;
  videoAspect?: string | null;
  paygateTier?: string | null;
  projectHeader?: string | null;
  projectFooter?: string | null;
  onClose: () => void;
  onApplied: (r: any) => void;
}) {
  return (
    <ReactFlowProvider>
      <Editor {...props} />
    </ReactFlowProvider>
  );
}
