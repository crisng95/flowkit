import { type Project } from "../api/client";

// Chữ cái đầu của tối đa 2 từ → nhãn cho ô badge cạnh tên dự án.
const initialsOf = (title: string) =>
  (title.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("") || "?")
    .toUpperCase();

const aspectLabel = (a?: string | null) =>
  a === "VIDEO_ASPECT_RATIO_PORTRAIT" ? "9:16" : "16:9";

// "10" | "abra_r2v_10s" → "Omni 10s"; rỗng/rác → "Veo". Cùng luật với _video_engine bên
// agent/api/studio.py.
const engineLabel = (videoModel?: string | null) => {
  const m = String(videoModel || "").trim().match(/^(?:abra_r2v_)?(\d+)s?$/);
  const n = m ? Number(m[1]) : NaN;
  return [4, 6, 8, 10].includes(n) ? `Omni ${n}s` : "Veo";
};

/** Badge + tên dự án + dòng meta. Sống trên thanh trên cùng của app, cạnh logo — workspace
 *  bên dưới nhờ vậy không cần thanh header riêng, dành trọn chiều cao cho nội dung. */
export default function ProjectIdentity({ project }: { project: Project }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
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
  );
}
