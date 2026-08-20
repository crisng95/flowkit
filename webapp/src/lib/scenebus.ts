import { useEffect, useRef } from "react";
import type { Scene, Shot } from "../api/client";

// Tab Storyboard và tab Shots hiển thị CÙNG một danh sách scene, và ProjectWorkspace giữ mọi
// tab đã mở sống trong DOM (chỉ ẩn đi) để job nền không chết khi chuyển tab. Hệ quả: mỗi tab
// giữ một bản sao `scenes` riêng, nạp một lần lúc mở. Đổi tên scene bên Storyboard thì bên
// Shots vẫn hiện tên cũ cho tới khi bấm ⟳ — hai tab nói về cùng một scene bằng hai cái tên.
//
// Kênh phát này giữ các bản sao ấy khớp nhau. Hai loại tin, cố ý tách:
//   "renamed"      — vá đúng một scene, khỏi gọi lại API (đổi tên là việc làm thường xuyên);
//   "shot-renamed" — y hệt, cho TÊN SHOT: thẻ shot hiện `title` ở cả hai tab nên nó lệch
//                    theo đúng kiểu tên scene lệch;
//   "list-changed" — thêm/xoá scene, người nhận nạp lại cả danh sách (hiếm, nên nạp lại rẻ).
//
// Chỉ trong MỘT tab trình duyệt: đây là bộ nhớ của trang, không phải BroadcastChannel. Mở dự
// án ở hai cửa sổ thì vẫn phải ⟳ như trước — cùng mức đồng bộ như mọi thứ khác trong app.

export type SceneEvent =
  | { type: "renamed"; projectId: string; id: string; heading: string }
  | { type: "shot-renamed"; projectId: string; sceneId: string; id: string; title: string }
  | { type: "list-changed"; projectId: string };

type Listener = (e: SceneEvent) => void;

const listeners = new Set<Listener>();

export function announceScene(e: SceneEvent): void {
  for (const fn of listeners) fn(e);
}

/** Tiện ích: phát tin đổi tên sau khi server đã xác nhận. */
export function announceSceneRenamed(projectId: string, scene: Scene): void {
  announceScene({ type: "renamed", projectId, id: scene.id, heading: scene.heading });
}

export function announceShotRenamed(projectId: string, shot: Shot): void {
  announceScene({ type: "shot-renamed", projectId, sceneId: shot.scene_id,
                  id: shot.id, title: shot.title });
}

/**
 * Nghe thay đổi scene của MỘT dự án. Tin do chính tab này phát vẫn quay về, nên người gọi
 * cứ xử lý idempotent (đặt lại đúng giá trị đã có = không đổi gì).
 */
export function useSceneEvents(projectId: string, onEvent: (e: SceneEvent) => void): void {
  // Giữ callback mới nhất trong ref: nếu đăng ký lại mỗi lần callback đổi (mà nó đổi mỗi
  // render vì đóng gói state), listener sẽ tháo/gắn liên tục và dễ trượt mất tin.
  const cb = useRef(onEvent);
  cb.current = onEvent;
  useEffect(() => {
    const fn: Listener = (e) => {
      if (e.projectId === projectId) cb.current(e);
    };
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  }, [projectId]);
}
