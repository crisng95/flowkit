import { useEffect, useState } from "react";
import { api, type Scene } from "../../api/client";
import { announceSceneRenamed } from "../../lib/scenebus";

// Tên scene trên đầu mỗi dải shot — bấm vào là sửa được tại chỗ. Dùng chung Storyboard và
// Shots để hai tab không có hai kiểu đổi tên khác nhau, và để việc phát tin đồng bộ
// (scenebus) nằm ở MỘT chỗ thay vì mỗi tab tự nhớ gọi.
//
// Ô input trông như chữ thường cho tới khi rê chuột/focus: dải shot đọc bằng mắt là chính,
// một khung nhập luôn hiện viền làm cả trang trông như biểu mẫu.
export default function SceneHeading({
  scene,
  index,
  projectId,
  onRenamed,
}: {
  scene: Scene;
  /** Số thứ tự hiển thị (0-based) — không phải `scene.idx` khi danh sách đang lọc/sắp xếp. */
  index: number;
  projectId: string;
  onRenamed: (s: Scene) => void;
}) {
  const [text, setText] = useState(scene.heading || "");
  const [busy, setBusy] = useState(false);

  // Tên đổi ở TAB KHÁC (qua scenebus) hoặc scene khác được gán vào cùng ô → theo giá trị mới.
  useEffect(() => {
    setText(scene.heading || "");
  }, [scene.id, scene.heading]);

  const commit = async () => {
    const v = text.trim();
    if (!v || v === (scene.heading || "")) {
      setText(scene.heading || "");   // xoá trắng rồi rời chuột = huỷ, không phải xoá tên
      return;
    }
    setBusy(true);
    try {
      const updated = await api.renameScene(scene.id, v);
      onRenamed(updated);
      announceSceneRenamed(projectId, updated);
    } catch {
      setText(scene.heading || "");   // hỏng thì trả ô về tên thật, đừng để tên ma
    } finally {
      setBusy(false);
    }
  };

  return (
    // KHÔNG flex-1: hàng tiêu đề của cả hai tab đẩy nhóm nút bên phải bằng `ml-auto`, ô tên
    // mà nuốt hết chỗ trống thì `ml-auto` thành vô nghĩa và cả hàng xô lại.
    <h3 className="flex min-w-0 shrink items-center text-sm font-medium text-neutral-200">
      <span className="mr-1.5 shrink-0 text-neutral-500">
        {String(index + 1).padStart(2, "0")}
      </span>
      <input
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          if (e.key === "Escape") {
            setText(scene.heading || "");
            (e.target as HTMLInputElement).blur();
          }
        }}
        title="Bấm để đổi tên scene"
        placeholder="(chưa đặt tên)"
        className="w-72 min-w-0 truncate rounded border border-transparent bg-transparent px-1 py-0.5 text-sm font-medium text-neutral-200 outline-none placeholder:text-neutral-600 hover:border-neutral-700 focus:border-indigo-500 focus:bg-neutral-950 disabled:opacity-50"
      />
    </h3>
  );
}
