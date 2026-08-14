import { useEffect, useState } from "react";
import { api, getTtsConfig, setTtsConfig, listVoices, type Voice } from "../../api/client";
import VoiceManager from "./VoiceManager";
import { Field, Group, inp } from "./ui";

// Thiết lập ở phạm vi ỨNG DỤNG — dùng chung cho mọi dự án. Trước đây nằm trong một drawer
// riêng mở từ ⚙ trên header (SettingsDrawer); nay là một nhóm trong tab Thiết lập để chỉ còn
// MỘT chỗ chỉnh cấu hình. Nội dung chia làm ba tầng rõ ràng:
//   1. Hạ tầng    — thứ phải đúng thì app mới chạy (agent CLI, OmniVoice, font)
//   2. Mặc định   — giá trị áp cho DỰ ÁN MỚI, không đụng tới dự án đang mở
//   3. Kho giọng  — quản lý voice template dùng chung
export default function AppSettingsSection({
  onDirty,
  registerSave,
}: {
  onDirty: () => void;
  registerSave: (fn: () => Promise<void>) => void;
}) {
  const [opts, setOpts] = useState<any>(null);
  const [s, setS] = useState<Record<string, any>>({});
  const [ttsUrl, setTtsUrl] = useState("");
  const [fonts, setFonts] = useState<{ name: string; path: string }[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);

  useEffect(() => {
    api.options().then(setOpts).catch(() => {});
    api.getSettings().then(setS).catch(() => {});
    getTtsConfig().then((c) => setTtsUrl(c.base_url || "")).catch(() => {});
    api.listFonts().then((r) => setFonts(r.fonts)).catch(() => {});
    listVoices().then(setVoices).catch(() => {});
  }, []);

  // Thanh Lưu nằm ở tab cha, nên phần này chỉ đăng ký hàm lưu của mình lên đó.
  useEffect(() => {
    registerSave(async () => {
      await api.putSettings(s);
      if (ttsUrl.trim()) await setTtsConfig(ttsUrl.trim());
    });
  }, [s, ttsUrl, registerSave]);

  const set = (k: string, v: any) => {
    setS((p) => ({ ...p, [k]: v }));
    onDirty();
  };

  const agents = opts?.agents || [];
  const deps = [
    { ok: agents.some((a: any) => a.available), label: "AI agent CLI (claude / antigravity)" },
    { ok: !!opts, label: "Studio API" },
    { ok: !!ttsUrl.trim(), label: "OmniVoice URL đã đặt" },
  ];

  return (
    <div className="space-y-6">
      <Group
        title="Hạ tầng"
        hint="Những thứ phải đúng thì app mới chạy được. Áp dụng cho toàn bộ máy này."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="AI Agent">
            <select value={s.agent || "claude"} onChange={(e) => set("agent", e.target.value)} className={inp}>
              {(agents.length ? agents.map((a: any) => a.key) : ["claude", "antigravity"]).map((k: string) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </Field>
          <Field label="AI Agent model" hint="Để trống = mặc định của CLI. Truyền qua --model; chọn model nhanh (gemini-flash) để tăng tốc sinh script/scene/shot. Phải đúng tên model mà CLI chấp nhận.">
            <input value={s.agent_model || ""} onChange={(e) => set("agent_model", e.target.value)}
              placeholder="vd: gemini-flash-3-5" className={inp} />
          </Field>
        </div>
        <Field label="OmniVoice base URL (TTS)" hint="URL Colab xoay vòng. Phải đặt trước khi test/quản lý giọng.">
          <input value={ttsUrl} onChange={(e) => { setTtsUrl(e.target.value); onDirty(); }}
            placeholder="https://xxxx.ngrok-free.app" className={inp} />
        </Field>
        <Field label="Font caption" hint="Font dùng khi vẽ chữ lên ảnh/video.">
          <select value={s.caption_font || ""} onChange={(e) => set("caption_font", e.target.value)} className={inp}>
            <option value="">(tự dò theo hệ điều hành)</option>
            {fonts.map((f) => <option key={f.path} value={f.path}>{f.name}</option>)}
          </select>
        </Field>
        <div className="flex flex-wrap gap-x-5 gap-y-1.5 pt-1">
          {deps.map((d) => (
            <div key={d.label} className="flex items-center gap-2 text-sm text-neutral-400">
              <span className={`h-2 w-2 rounded-full ${d.ok ? "bg-emerald-400" : "bg-rose-500"}`} />
              {d.label}
            </div>
          ))}
        </div>
      </Group>

      <Group
        title="Mặc định cho dự án mới"
        hint="Chỉ áp cho dự án TẠO SAU khi lưu — không đụng tới dự án đang mở. Muốn đổi dự án này thì dùng các nhóm bên trên."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Style mặc định">
            <input value={s.style || ""} onChange={(e) => set("style", e.target.value)}
              placeholder="vd: Cinematic, teal-orange, 35mm" className={inp} />
            <div className="mt-1.5 flex flex-wrap gap-1">
              {(opts?.style_presets || []).map((p: string) => (
                <button key={p} onClick={() => set("style", p)}
                  className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300 hover:bg-neutral-700">{p}</button>
              ))}
            </div>
          </Field>
          <Field label="Ngôn ngữ kịch bản / lời đọc">
            <input value={s.script_lang || ""} onChange={(e) => set("script_lang", e.target.value)}
              placeholder="Tiếng Việt" className={inp} />
          </Field>
          <Field label="Image model">
            <select value={s.image_model || ""} onChange={(e) => set("image_model", e.target.value)} className={inp}>
              <option value="">(mặc định)</option>
              {(opts?.image_models || []).map((m: string) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          {/* Cùng danh sách với ⚙ Cấu hình dự án (`video_engines`) — dropdown cũ liệt kê tên
              TIER như thể là model, chọn vào là lưu rác vào project.video_model. */}
          <Field label="Video model" hint="Mặc định cho dự án mới. Veo 3.1 Lite [Lower Priority] không trừ credit (chỉ Ultra).">
            <select value={s.video_model || ""} onChange={(e) => set("video_model", e.target.value)} className={inp}>
              {(opts?.video_engines || [{ value: "", label: "(mặc định)" }]).map(
                (m: { value: string; label: string }) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
            </select>
          </Field>
          <Field label="Khung hình">
            <select value={s.aspect_ratio || "VIDEO_ASPECT_RATIO_LANDSCAPE"}
              onChange={(e) => set("aspect_ratio", e.target.value)} className={inp}>
              <option value="VIDEO_ASPECT_RATIO_LANDSCAPE">16:9 ngang</option>
              <option value="VIDEO_ASPECT_RATIO_PORTRAIT">9:16 dọc</option>
            </select>
          </Field>
          <Field label="Độ dài shot (giây)">
            <input type="number" min={1} max={10} value={s.shot_duration ?? 8}
              onChange={(e) => set("shot_duration", Math.min(10, Math.max(1, Number(e.target.value) || 8)))}
              className={inp} />
          </Field>
          <Field label="Giọng đọc mặc định">
            <select value={s.voice_id ?? 0} onChange={(e) => set("voice_id", Number(e.target.value))} className={inp}>
              <option value={0}>Mặc định (id 0)</option>
              {voices.map((v) => <option key={v.voice_id} value={v.voice_id}>{v.title} (id {v.voice_id})</option>)}
            </select>
          </Field>
          <Field label="Tốc độ đọc mặc định">
            <div className="flex items-center gap-3">
              <input type="range" min={0.5} max={1.5} step={0.05} value={s.tts_speed ?? 1.0}
                onChange={(e) => set("tts_speed", parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500" />
              <span className="w-12 text-right text-xs tabular-nums text-neutral-400">
                {(s.tts_speed ?? 1.0).toFixed(2)}×
              </span>
            </div>
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input type="checkbox" checked={s.storytelling ?? true}
            onChange={(e) => set("storytelling", e.target.checked)}
            className="h-4 w-4 accent-indigo-500" />
          Bật Storytelling mặc định
        </label>
      </Group>

      <Group title="Kho giọng đọc" hint="Voice template dùng chung cho mọi dự án. Cần OmniVoice URL ở trên.">
        <VoiceManager />
      </Group>
    </div>
  );
}
