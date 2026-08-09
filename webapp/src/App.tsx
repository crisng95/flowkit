import { useEffect, useState } from "react";
import { type Project } from "./api/client";
import StatusPills from "./components/StatusPills";
import ProjectGrid from "./components/ProjectGrid";
import ProjectWorkspace from "./components/ProjectWorkspace";
import { useFlowAccount } from "./lib/account";

export default function App() {
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

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-neutral-800 px-6 py-3">
        <button
          onClick={() => setOpen(null)}
          className="flex items-center gap-2 text-lg font-semibold tracking-tight"
        >
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-sm text-white">
            ▶
          </span>
          Flow Studio
        </button>

        {/* Không còn nút ⚙ riêng ở đây: thiết lập cấp app đã gộp vào tab "Thiết lập" của
            workspace (nhóm "Ứng dụng"), để chỉ có MỘT chỗ chỉnh cấu hình. */}
        <StatusPills />
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
          <ProjectWorkspace project={open} onBack={() => setOpen(null)} />
        ) : (
          <ProjectGrid key={switches} onOpen={setOpen} />
        )}
      </main>
    </div>
  );
}
