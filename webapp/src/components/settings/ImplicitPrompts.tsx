import { useState } from "react";
import { PROMPT_KEYS, type PromptKey } from "../../api/client";
import { Group } from "./ui";

// Các khối prompt mà agent CHÈN NGẦM vào mỗi lần chạy. Trước đây chúng chỉ nằm trong code
// (brain.py) nên không nhìn thấy, không sửa được, và khi kết quả ra sai kiểu thì không biết
// câu nào đã đẩy nó đi. Ở đây mỗi khối là một ô chứa TEXT THẬT (agent đã đổ bản mặc định vào
// dự án lúc tạo / lúc khởi động), sửa trực tiếp được:
//   sửa nội dung → dùng nguyên văn của bạn
//   "Đặt lại"    → chép lại bản mặc định của agent
//   đúng một dấu "-" → TẮT hẳn khối đó
//   để trống     → agent vẫn rơi về bản mặc định (lưới an toàn, không phải cách dùng chính)
const META: Record<PromptKey, { title: string; when: string; group: string }> = {
  single_frame: {
    group: "Ảnh frame (storyboard / shot)",
    title: "Guard khung đơn",
    when: "Mọi ảnh frame. Ép model vẽ MỘT khung ảnh liền mạch thay vì chép lại bố cục sheet " +
      "tham chiếu, và giữ nhân vật đúng danh tính nhưng tự do về tư thế.",
  },
  single_frame_grid: {
    group: "Ảnh frame (storyboard / shot)",
    title: "Guard khung đơn — phần lưới bối cảnh",
    when: "Nối thêm vào guard trên, CHỈ khi ảnh bối cảnh đang ở chế độ lưới 4 khung. " +
      "Bảo model chọn một trong bốn góc thay vì vẽ lại cả lưới.",
  },
  image_text: {
    group: "Ảnh frame (storyboard / shot)",
    title: "Ngôn ngữ chữ trong ảnh",
    when: "Câu cuối của MỌI prompt ảnh. {lang} lấy từ “Chữ viết/vẽ trong ảnh” ở nhóm Nội dung.",
  },
  video_text: {
    group: "Video (clip)",
    title: "Ngôn ngữ chữ trong video",
    when: "Câu cuối của MỌI prompt video — cả node “Tạo video” lẫn nút render ở tab Shots. " +
      "Dùng chung ngôn ngữ với ảnh nhưng phải tách khối riêng: nói “in the image” thì model " +
      "video hiểu là ảnh tham chiếu, rồi vẫn tự vẽ biển hiệu tiếng Trung vào các frame sau.",
  },
  sheet_character: {
    group: "Ảnh tham chiếu (asset)",
    title: "Nhân vật — bảng sheet",
    when: "Ảnh tham chiếu của entity loại character khi KHÔNG bật “ảnh tham chiếu đơn”: " +
      "bảng nhiều mục (turnaround, biểu cảm, chi tiết trang phục, chất liệu), nền trắng, " +
      "đúng MỘT người trên sheet.",
  },
  sheet_character_one: {
    group: "Ảnh tham chiếu (asset)",
    title: "Nhân vật — một ảnh",
    when: "Ảnh tham chiếu của entity loại character khi BẬT “ảnh tham chiếu đơn”: một ảnh " +
      "toàn thân chính diện, nền trơn, không bảng không panel — để Flow chú thích ảnh này " +
      "là một con người chứ không phải “character design sheet”.",
  },
  sheet_prop: {
    group: "Ảnh tham chiếu (asset)",
    title: "Sheet đạo cụ",
    when: "Ảnh tham chiếu của entity loại prop: nhiều góc, vật thể tách nền trắng.",
  },
  sheet_location: {
    group: "Ảnh tham chiếu (asset)",
    title: "Bối cảnh — lưới 4 khung",
    when: "Ảnh tham chiếu của entity loại location khi chọn “Lưới 2x2”. Thứ tự bốn ô là CỐ " +
      "ĐỊNH vì nhãn Toàn cảnh / Góc ngược / Trên cao / Cận cảnh được dán theo đúng thứ tự đó.",
  },
  sheet_location_one: {
    group: "Ảnh tham chiếu (asset)",
    title: "Bối cảnh — một ảnh",
    when: "Ảnh tham chiếu của entity loại location khi chọn “Một ảnh”. Một góc máy duy nhất, " +
      "không lưới nên cũng không dán nhãn.",
  },
  cine_continuous: {
    group: "Prompt gửi cho AI viết shot",
    title: "CINEMATOGRAPHY — liên tục",
    when: "Thay cho khối trên khi BẬT “Shot liên tục trong scene” ở nhóm Nội dung. Các khung " +
      "là lát cắt liên tiếp của MỘT hành động: giữ đường 180°, đổi cỡ cảnh từng nấc, vị trí " +
      "nhân vật tiến dần trong không gian — để nối clip lại thành phim không bị rời rạc.",
  },
  cine: {
    group: "Prompt gửi cho AI viết shot",
    title: "CINEMATOGRAPHY",
    when: "Chèn vào các lượt AI TÁCH SHOT / viết lại góc máy (tách beat, autofill storyboard, " +
      "đổi góc máy, sinh visual/motion prompt). Buộc mỗi shot có cỡ cảnh, góc máy, ống kính, " +
      "ánh sáng, bố cục, tư thế cụ thể và khác shot liền kề.",
  },
  motion: {
    group: "Prompt gửi cho AI viết shot",
    title: "MOTION",
    when: "Chèn vào các lượt AI viết `motion_prompt`. Ảnh frame đã khoá bố cục tĩnh nên khối " +
      "này bắt model chỉ tả cái gì CHUYỂN ĐỘNG.",
  },
  omni_timeline: {
    group: "Prompt gửi cho AI viết shot",
    title: "Mốc thời gian (Omni Flash)",
    when: "Nối sau khối MOTION, CHỈ khi model video là Omni Flash — engine này đọc cue " +
      "[mm:ss]. {clip_s} = độ dài clip, {n_beats} = số mốc gợi ý.",
  },
};

const GROUPS = [
  "Ảnh frame (storyboard / shot)",
  "Ảnh tham chiếu (asset)",
  "Video (clip)",
  "Prompt gửi cho AI viết shot",
];

export default function ImplicitPrompts({
  values,
  defaults,
  onChange,
}: {
  values: Record<string, string>;
  /** Bản mặc định trong code của agent (GET /options → prompt_defaults). */
  defaults: Record<string, string>;
  onChange: (key: PromptKey, value: string) => void;
}) {
  const [open, setOpen] = useState<PromptKey | null>(null);

  return (
    <>
      <p className="rounded-lg border border-neutral-800 bg-neutral-900/30 px-3 py-2 text-xs leading-relaxed text-neutral-500">
        Những đoạn dưới đây được agent tự nối vào prompt mỗi lần chạy — kể cả khi bạn tạo từ
        Node Editor. Mỗi ô là <b className="text-neutral-300">văn bản thật của dự án này</b>,
        sửa trực tiếp rồi bấm Lưu. <b className="text-neutral-300">Đặt lại</b> để lấy lại bản
        mặc định, hoặc gõ đúng một dấu{" "}
        <code className="rounded bg-neutral-800 px-1 text-neutral-300">-</code> để{" "}
        <b className="text-neutral-300">tắt</b> khối đó. Dự án mới được đổ sẵn bản mặc định;
        sửa mặc định trong code về sau không tự lan sang dự án cũ.
      </p>

      {GROUPS.map((g) => (
        <Group key={g} title={g}>
          {PROMPT_KEYS.filter((k) => META[k].group === g).map((k) => {
            const v = values[k] ?? "";
            const def = defaults[k] ?? "";
            const off = v.trim() === "-";
            const same = v.trim() === def.trim();
            const expanded = open === k;
            return (
              <div key={k} className="min-w-0">
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-xs font-medium text-neutral-300">{META[k].title}</span>
                  {off ? (
                    <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] text-rose-300">
                      đã tắt
                    </span>
                  ) : same || !v.trim() ? (
                    <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] text-neutral-500">
                      mặc định
                    </span>
                  ) : (
                    <span className="rounded bg-indigo-500/15 px-1.5 py-0.5 text-[10px] text-indigo-300">
                      đã sửa
                    </span>
                  )}
                  <span className="text-[10px] tabular-nums text-neutral-700">
                    {v.length.toLocaleString("vi-VN")} ký tự
                  </span>
                  <div className="ml-auto flex shrink-0 gap-2 text-[11px]">
                    <button
                      onClick={() => setOpen(expanded ? null : k)}
                      className="text-neutral-500 hover:text-neutral-300"
                    >
                      {expanded ? "Thu gọn" : "Mở rộng"}
                    </button>
                    <button
                      onClick={() => onChange(k, off ? def : "-")}
                      title={off ? "Chèn lại khối này" : "Không chèn khối này vào prompt"}
                      className="text-neutral-500 hover:text-neutral-300"
                    >
                      {off ? "Bật lại" : "Tắt"}
                    </button>
                    {!same && (
                      <button
                        onClick={() => onChange(k, def)}
                        title="Chép lại nguyên văn bản mặc định của agent"
                        className="text-neutral-500 hover:text-neutral-300"
                      >
                        Đặt lại
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  value={v}
                  onChange={(e) => onChange(k, e.target.value)}
                  placeholder={def}
                  spellCheck={false}
                  className={`w-full resize-y rounded-lg border bg-neutral-950 px-2.5 py-1.5 font-mono text-[11px] leading-relaxed outline-none focus:border-indigo-500 ${
                    expanded ? "h-72" : "h-24"
                  } ${off ? "border-rose-900/60 text-rose-300" : "border-neutral-700"}`}
                />
                <p className="mt-1 text-xs leading-relaxed text-neutral-600">{META[k].when}</p>
              </div>
            );
          })}
        </Group>
      ))}
    </>
  );
}
