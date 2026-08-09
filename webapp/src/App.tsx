import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { type Project } from "./api/client";
import StatusPills from "./components/StatusPills";
import ProjectGrid from "./components/ProjectGrid";
import ProjectIdentity from "./components/ProjectIdentity";
import ProjectWorkspace from "./components/ProjectWorkspace";
import { useFlowAccount } from "./lib/account";

export default function App() {
  // `open` VỪA là "đang mở dự án nào" VỪA là bản dự án hiện hành: tên/khung hình/model hiện
  // trên thanh trên cùng nên phải sống ở đây, còn workspace cập nhật ngược lên qua setProject.
  const [open, setOpen] = useState<Project | null>(null);
  const { account, switches } = useFlowAccount();
  const [switchedTo, setSwitchedTo] = useState<string | null>(null);

  // Đổi tài khoản Flow trong Chrome → dự án đang mở có thể không còn thuộc về mình nữa (mọi
  // thao tác sẽ trả 403). Đóng nó lại, quay về danh sách, và ép ProjectGrid mount lại
  // (key={switches}) để danh sách tải theo tài khoản mới.
  useEffect(() => {
    if (!switches) return;
    setOpen(null);
    setSwitchedTo(account?.email ?? account?.id ?? "tài khoản khác");
    const t = setTimeout(() => setSwitchedTo(null), 8000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [switches]);

  // Workspace sửa dự án (đổi cover, lưu thiết lập, sửa kịch bản…) → đẩy ngược lên đây để
  // thanh trên cùng phản ánh ngay. Bọc lại vì state ở đây có thêm trạng thái `null`.
  const setProject = useCallback<Dispatch<SetStateAction<Project>>>((u) => {
    setOpen((p) => (p ? (typeof u === "function" ? u(p) : u) : p));
  }, []);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-neutral-800 px-5 py-3">
        {/* Nút home DUY NHẤT. Trước có cả logo chữ "Flow Studio" lẫn nút ← ngay cạnh, hai
            thứ cùng một việc; giờ chỉ còn ô ▶ (rê chuột thấy nó về danh sách dự án). */}
        <button
          onClick={() => setOpen(null)}
          title={open ? "Về danh sách dự án" : "Flow Studio"}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-sm text-white"
        >
          ▶
        </button>

        {/* Danh tính dự án nằm ở thanh TRÊN CÙNG — workspace bên dưới nhờ vậy bỏ hẳn được
            header riêng của nó (và nút ⚙: Thiết lập đã là một tab). */}
        {open && (
          <>
            <div className="h-6 w-px shrink-0 bg-neutral-800" />
            <div className="min-w-0 flex-1">
              <ProjectIdentity project={open} />
            </div>
          </>
        )}

        <div className={open ? "shrink-0" : "ml-auto shrink-0"}>
          <StatusPills />
        </div>
      </header>

      {switchedTo && (
        <div className="flex items-center gap-2 border-b border-amber-500/30 bg-amber-500/10 px-6 py-2 text-sm text-amber-200">
          <span>
            Chrome đã chuyển sang tài khoản <b>{switchedTo}</b> — đang hiển thị dự án của tài
            khoản này.
          </span>
          <button
            onClick={() => setSwitchedTo(null)}
            className="ml-auto rounded px-2 py-0.5 text-xs text-amber-300/80 hover:bg-amber-500/20"
          >
            Đóng
          </button>
        </div>
      )}

      <main className={`flex-1 ${open ? "overflow-hidden" : "overflow-auto"}`}>
        {open ? (
          <ProjectWorkspace key={open.id} project={open} setProject={setProject} />
        ) : (
          <ProjectGrid key={switches} onOpen={setOpen} />
        )}
      </main>
    </div>
  );
}
