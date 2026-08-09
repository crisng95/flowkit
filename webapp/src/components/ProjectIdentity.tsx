import { type Project } from "../api/client";

/** Tên dự án trên thanh trên cùng của app.
 *
 *  Nó là thứ DUY NHẤT còn lại giữa nút home và StatusPills, nên được tô chữ gradient thay vì
 *  màu chữ thường: nhìn phát ra ngay mình đang ở trong dự án nào, mà không cần badge hay
 *  dòng meta chiếm chỗ. `bg-clip-text` cần chữ trong suốt — dấu … khi cắt cũng ăn theo
 *  gradient nên vẫn liền mạch. */
export default function ProjectIdentity({ project }: { project: Project }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span className="h-4 w-1 shrink-0 rounded-full bg-gradient-to-b from-indigo-400 to-fuchsia-500" />
      {/* `title=` để tên dài bị cắt vẫn xem được đầy đủ khi rê chuột */}
      <h1
        title={project.title}
        className="truncate bg-gradient-to-r from-indigo-200 via-violet-300 to-fuchsia-300 bg-clip-text text-base font-semibold tracking-tight text-transparent"
      >
        {project.title}
      </h1>
    </div>
  );
}
