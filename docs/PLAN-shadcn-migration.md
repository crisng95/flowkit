# PLAN-shadcn-migration.md
# FlowKit Desktop — Shadcn UI Migration

---

## Overview

Chuyển toàn bộ giao diện FlowKit Desktop từ hệ thống custom CSS/component sang **Shadcn UI** — bộ component chuẩn mực, tối ưu UX, dựa trên Radix UI primitives + Tailwind CSS v4.

**Tại sao?**
- UI hiện tại dùng custom `ActionButton`, `Modal`, `BatchStatusBar` với inline style và CSS variables thủ công — khó maintain, không nhất quán
- Shadcn UI cung cấp accessible, headless components (Radix) kết hợp Tailwind utility classes
- Các dependencies cốt lõi **đã sẵn có**: `@radix-ui/react-dialog`, `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`
- Không cần re-architect backend — chỉ thay UI layer

---

## Project Type

**WEB (Electron + Vite + React + TypeScript)**
- Agent: `frontend-specialist`
- Framework: React 19, Tailwind v4, electron-vite

---

## Tech Stack

| Layer | Current | Target |
|-------|---------|--------|
| Components | Custom `ActionButton`, `Modal` | Shadcn `Button`, `Dialog`, `Select`, `Input`, `Textarea`, `Badge`, `Card`, `Tooltip`, `Progress`, `ScrollArea`, `Separator`, `DropdownMenu`, `Tabs` |
| Styling | CSS Variables + inline styles | Shadcn CSS variables chuẩn + Tailwind utilities |
| Icons | `lucide-react` | `lucide-react` (giữ nguyên) |
| State | React useState | Giữ nguyên |
| Tailwind | v4 (`@import "tailwindcss"`) | v4 + Shadcn theme layer |

---

## Pre-flight: Dependencies Đã Có

✅ `@radix-ui/react-dialog` ^1.1.15  
✅ `@radix-ui/react-slot` ^1.2.4  
✅ `class-variance-authority` ^0.7.1  
✅ `clsx` ^2.1.1  
✅ `tailwind-merge` ^3.5.0  
✅ `lucide-react` ^1.7.0  
✅ `cn()` utility tại `src/lib/utils.ts`  

**Cần cài thêm (Radix primitives):**
```bash
npm install @radix-ui/react-label @radix-ui/react-select @radix-ui/react-tabs \
  @radix-ui/react-tooltip @radix-ui/react-progress @radix-ui/react-scroll-area \
  @radix-ui/react-separator @radix-ui/react-dropdown-menu @radix-ui/react-badge \
  @radix-ui/react-switch @radix-ui/react-toast
```

---

## File Structure

```
desktop/src/
├── components/
│   └── ui/                          ← Shadcn components (thay thế + mở rộng)
│       ├── button.tsx               [NEW] replaces ActionButton
│       ├── dialog.tsx               [NEW] replaces Modal
│       ├── input.tsx                [NEW]
│       ├── textarea.tsx             [NEW]
│       ├── select.tsx               [NEW]
│       ├── badge.tsx                [NEW]
│       ├── card.tsx                 [NEW]
│       ├── progress.tsx             [NEW] replaces BatchStatusBar internals
│       ├── scroll-area.tsx          [NEW]
│       ├── tooltip.tsx              [NEW]
│       ├── tabs.tsx                 [NEW]
│       ├── separator.tsx            [NEW]
│       ├── dropdown-menu.tsx        [NEW]
│       ├── switch.tsx               [NEW]
│       ├── toast.tsx                [NEW]
│       ├── ActionButton.tsx         [KEEP → wrap Shadcn Button for backward compat]
│       ├── BatchStatusBar.tsx       [REFACTOR → use Progress + Badge]
│       └── Modal.tsx                [KEEP → wrap Dialog for backward compat]
├── index.css                        [MODIFY] → Shadcn CSS variables layer
└── App.tsx                          [MODIFY] → Toaster provider
```

---

## Inventory: Components Cần Refactor

### Phase A — Shadcn Foundation (UI primitives)
| Tệp | Thay đổi |
|-----|----------|
| `index.css` | Thêm Shadcn CSS variable layer (hsl tokens), giữ backward-compat aliases |
| `components/ui/button.tsx` | Shadcn Button component mới |
| `components/ui/dialog.tsx` | Shadcn Dialog wrapping Radix |
| `components/ui/input.tsx` | Shadcn Input |
| `components/ui/textarea.tsx` | Shadcn Textarea |
| `components/ui/select.tsx` | Shadcn Select (Radix) |
| `components/ui/badge.tsx` | Shadcn Badge |
| `components/ui/card.tsx` | Shadcn Card |
| `components/ui/progress.tsx` | Shadcn Progress |
| `components/ui/scroll-area.tsx` | Shadcn ScrollArea |
| `components/ui/tooltip.tsx` | Shadcn Tooltip |
| `components/ui/tabs.tsx` | Shadcn Tabs |
| `components/ui/separator.tsx` | Shadcn Separator |
| `components/ui/dropdown-menu.tsx` | Shadcn DropdownMenu |
| `components/ui/switch.tsx` | Shadcn Switch |
| `components/ui/toast.tsx` + `toaster.tsx` | Shadcn Toast + Toaster |

### Phase B — Compatibility Shims
| Tệp | Thay đổi |
|-----|----------|
| `ActionButton.tsx` | Wrap `Button` từ Shadcn, giữ API cũ (variant, size, onClick) |
| `Modal.tsx` | Wrap `Dialog` từ Shadcn, giữ API cũ (title, onClose, width) |
| `BatchStatusBar.tsx` | Refactor dùng `Progress` + `Badge` từ Shadcn |

### Phase C — Page & Modal Refactor
| Trang/Modal | Refactor |
|-------------|----------|
| `App.tsx` | Sidebar dùng Shadcn `NavigationMenu` / `Button ghost`, thêm `Toaster` |
| `DashboardPage.tsx` | Select → Shadcn `Select`, status pills → `Badge` |
| `ProjectsPage.tsx` | Card → `Card`, buttons → `Button` |
| `ProjectDetailPage.tsx` | Tabs → Shadcn `Tabs`, badges → `Badge`, inputs → `Input` |
| `VideoDetailPage.tsx` | Buttons → `Button`, status → `Badge`, scene list → `ScrollArea` |
| `LogsPage.tsx` | Log viewer → `ScrollArea` |
| `GalleryPage.tsx` | Media cards → `Card` |
| `SettingsPage.tsx` | Form fields → `Input`, `Switch`, `Select` |
| Tất cả 14 Modals | `Dialog` từ Shadcn (qua Modal shim) |
| `EditableText.tsx` | Dùng `Input` / `Textarea` Shadcn |
| `AddCharacterModal` | `Input`, `Textarea`, `Select` |
| `CreateProjectModal` | `Input`, `Textarea`, `Select` |
| `AISetupModal` | `Select`, `Textarea`, `Button` |

---

## Task Breakdown

### Task 1 — Cài dependencies & thiết lập Shadcn CSS layer
**Agent:** `frontend-specialist` | **Skill:** `tailwind-patterns`  
**Priority:** P0 — Blocker cho mọi task khác

**INPUT:** `package.json`, `index.css`  
**OUTPUT:**
- Cài thêm 11 Radix primitives
- `index.css` cập nhật: thêm Shadcn HSL variable tokens, giữ backward-compat aliases
- Xác nhận `tailwind.config` không conflict với v4

**VERIFY:** `npm run build` không có lỗi

---

### Task 2 — Tạo 16 Shadcn UI components (Phase A)
**Agent:** `frontend-specialist` | **Skill:** `frontend-design`  
**Priority:** P1 — Phụ thuộc Task 1  
**Parallel:** Tất cả 16 files có thể tạo song song

**INPUT:** Shadcn component source (copy từ shadcn/ui registry)  
**OUTPUT:** 16 files trong `src/components/ui/`  
**VERIFY:** TypeScript `tsc --noEmit` sạch sau khi tạo

> **Lưu ý Tailwind v4:** Shadcn registry mặc định dùng v3. Cần điều chỉnh:
> - Dùng `@import "tailwindcss"` thay vì `@tailwind` directives
> - CSS variables dùng `hsl(var(--token))` pattern chuẩn Shadcn

---

### Task 3 — Cập nhật compatibility shims
**Agent:** `frontend-specialist`  
**Priority:** P1 — Sau Task 2  
**Parallel:** ActionButton, Modal, BatchStatusBar song song

**INPUT:** Shadcn Button + Dialog + Progress (Task 2)  
**OUTPUT:**
- `ActionButton.tsx` → wrap `<Button>` Shadcn, map variants (`primary`→`default`, `danger`→`destructive`, `ghost`→`ghost`)
- `Modal.tsx` → wrap `<Dialog>` Shadcn, expose `title`, `onClose`, `width` props
- `BatchStatusBar.tsx` → dùng `<Progress>` + `<Badge>` Shadcn

**VERIFY:** Không có breaking change — các pages hiện tại vẫn chạy

---

### Task 4 — Refactor App.tsx + Layout Shell
**Agent:** `frontend-specialist` | **Skill:** `frontend-design`  
**Priority:** P2 — Sau Task 3

**INPUT:** `App.tsx`, Shadcn `Button`, `Separator`, `Badge`  
**OUTPUT:**
- Sidebar nav dùng `Button variant="ghost"` + active state chuẩn Shadcn
- Header: `Badge` cho WS status
- Thêm `<Toaster />` provider
- "Open Google Flow" button → `Button variant="default"`

**VERIFY:** Visual screenshot, navigation hoạt động

---

### Task 5 — Refactor Pages (Dashboard, Projects, Gallery, Logs)
**Agent:** `frontend-specialist`  
**Priority:** P2 — Sau Task 3  
**Parallel:** 4 pages song song

**OUTPUT:**
- `DashboardPage`: native `<select>` → Shadcn `<Select>`, status pills → `<Badge>`
- `ProjectsPage`: project cards → `<Card>`, search → `<Input>`
- `GalleryPage`: media items → `<Card>`
- `LogsPage`: viewer → `<ScrollArea>`

---

### Task 6 — Refactor Project & Video Detail Pages
**Agent:** `frontend-specialist`  
**Priority:** P2 — Sau Task 3

**OUTPUT:**
- `ProjectDetailPage`: native tabs → Shadcn `<Tabs>`, badges → `<Badge>`, inputs inline → `<Input>`
- `VideoDetailPage`: Shadcn `<Button>` thay ActionButton, scene list panel → `<ScrollArea>`

---

### Task 7 — Refactor SettingsPage
**Agent:** `frontend-specialist`  
**Priority:** P2 — Sau Task 3

**OUTPUT:** `<Input>`, `<Switch>`, `<Select>` Shadcn thay các form elements thủ công

---

### Task 8 — Refactor tất cả Modals (14 modals)
**Agent:** `frontend-specialist`  
**Priority:** P2 — Sau Task 3  
**Parallel:** Có thể xử lý song song theo nhóm

Danh sách modals:
1. `AISetupModal.tsx`
2. `AddCharacterModal.tsx`
3. `AddSceneModal.tsx`
4. `CreateProjectModal.tsx`
5. `CreateVideoModal.tsx`
6. `ChainVideosModal.tsx`
7. `ExportModal.tsx`
8. `FixUUIDsModal.tsx`
9. `GenNarratorModal.tsx`
10. `MusicModal.tsx`
11. `RefreshURLsModal.tsx`
12. `ReviewVideoModal.tsx`
13. `TTSSetupModal.tsx`
14. `ThumbnailModal.tsx`
15. `YouTubeSEOModal.tsx`
16. `YouTubeUploadModal.tsx`

**OUTPUT:** Mỗi modal dùng `Dialog` (qua shim hoặc trực tiếp), `Input`, `Textarea`, `Select`, `Button` Shadcn  
**VERIFY:** Mở từng modal, kiểm tra không có lỗi layout

---

### Task 9 — Refactor EditableText
**Agent:** `frontend-specialist`  
**Priority:** P2 — Sau Task 2

**OUTPUT:** `EditableText` dùng Shadcn `<Input>` / `<Textarea>` thay `<input>/<textarea>` native

---

### Task 10 — Visual Polish & Dark Mode Prep
**Agent:** `frontend-specialist` | **Skill:** `frontend-design`  
**Priority:** P3 — Sau tất cả refactor

**OUTPUT:**
- Kiểm tra color contrast WCAG AA
- Thêm `data-[state=active]` variants cho nav items
- Shadcn `<Tooltip>` cho các nút icon-only
- Consistent spacing với Shadcn conventions

---

### Task 11 — Build & Verification (Phase X)
**Agent:** `frontend-specialist`  
**Priority:** FINAL

```bash
cd desktop && npx tsc --noEmit          # TypeScript clean
npm run build                           # Build thành công
npm run dev                             # Dev server chạy
```

---

## Dependency Graph

```
Task 1 (deps + CSS)
    └── Task 2 (16 UI components)
            ├── Task 3 (shims: ActionButton, Modal, BatchStatusBar)
            │       ├── Task 4 (App.tsx layout)
            │       ├── Task 5 (Dashboard, Projects, Gallery, Logs)
            │       ├── Task 6 (ProjectDetail, VideoDetail)
            │       ├── Task 7 (Settings)
            │       └── Task 8 (14+ modals)
            └── Task 9 (EditableText)
                        └── Task 10 (Visual polish)
                                    └── Task 11 (Build verify)
```

---

## Success Criteria

- [ ] 0 TypeScript errors sau khi migrate
- [ ] Build thành công (`npm run build`)
- [ ] Tất cả modals mở/đóng đúng (Radix Dialog)
- [ ] Button variants (`default`, `ghost`, `destructive`, `secondary`) nhất quán
- [ ] `Select` có keyboard navigation (Radix)
- [ ] `Progress` trong BatchStatusBar hiển thị đúng %
- [ ] Toast notifications hoạt động khi regen ảnh/video
- [ ] Không có hardcoded inline styles (chỉ dùng Tailwind utilities + CSS vars)
- [ ] WCAG AA color contrast (4.5:1 cho text)

---

## Rủi ro & Mitigation

| Rủi ro | Xác suất | Mitigation |
|--------|----------|------------|
| Shadcn CSS tokens conflict với Tailwind v4 | Cao | Dùng HSL vars theo chuẩn Shadcn, test kỹ sau Task 1 |
| Breaking change ở Modal API | Trung bình | Giữ backward-compat shim ở Task 3 |
| `@radix-ui/*` peer dep conflicts | Thấp | Lock version theo Shadcn registry |
| Inline styles khó tìm để remove | Trung bình | Grep `style={{` và audit từng file |

---

## Phase X: Verification Checklist

- [ ] **Task 11:** `tsc --noEmit` — 0 errors
- [ ] **Task 11:** `npm run build` — success
- [ ] **Manual:** Sidebar navigation, active state đúng
- [ ] **Manual:** Tạo dự án mới (CreateProjectModal)
- [ ] **Manual:** AI Setup wizard đến Review step
- [ ] **Manual:** Video detail page — regen buttons hoạt động
- [ ] **Manual:** Tất cả Select dropdowns có keyboard nav
- [ ] **Manual:** BatchStatusBar hiển thị progress bar đúng
- [ ] **Manual:** Toast notification sau khi regen

---

## Ước tính Thời gian

| Phase | Tasks | Ước tính |
|-------|-------|----------|
| Foundation (T1+T2+T3) | 3 tasks | 30-45 phút |
| Pages (T4-T7) | 4 tasks | 45-60 phút |
| Modals (T8) | 16 modals | 45-60 phút |
| Polish + Verify (T9-T11) | 3 tasks | 20-30 phút |
| **Tổng** | **11 tasks** | **~2.5-3 giờ** |
