import { type Project } from "../api/client";

// Chữ cái đầu của tối đa 2 từ → nhãn cho ô badge cạnh tên dự án.
const initialsOf = (title: string) =>
  (title.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("") || "?")
    .toUpperCase();

/** Badge chữ cái đầu + tên dự án, một dòng. Sống trên thanh trên cùng của app, cạnh nút
 *  home — workspace bên dưới nhờ vậy không cần thanh header riêng.
 *
 *  Badge để MÀU TRUNG TÍNH, không dùng gradient: nút home ngay cạnh đã là ô gradient, hai ô
 *  gradient sát nhau trông như hai logo. Khung hình / model đã hiện ở Thiết lập, không cần
 *  nhắc lại thành dòng phụ ở đây. */
export default function ProjectIdentity({ project }: { project: Project }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-neutral-800 text-[12px] font-semibold tracking-tight text-neutral-300 ring-1 ring-white/5">
        {initialsOf(project.title)}
      </div>
      {/* `title=` để tên dài bị cắt vẫn xem được đầy đủ khi rê chuột */}
      <h1
        title={project.title}
        className="truncate text-[15px] font-semibold tracking-tight text-neutral-100"
      >
        {project.title}
      </h1>
    </div>
  );
}
