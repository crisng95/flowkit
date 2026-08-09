import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  listVoices,
  synthesize,
  base64ToAudioUrl,
  projectExportUrl,
  storyboard,
  shots as shotsApi,
  PROMPT_KEYS,
  type Project,
  type PromptKey,
  type SettingsPreset,
  type Voice,
} from "../../api/client";
import MusicManager from "../music/MusicManager";
import AppSettingsSection from "./AppSettingsSection";
import ImplicitPrompts from "./ImplicitPrompts";
import { Field, Group, Slider, inp } from "./ui";

// Toàn bộ cấu hình của app nằm ở ĐÂY — trước kia tách làm hai chỗ (drawer ⚙ "Settings" cấp
// app + modal "Cấu hình dự án"), phải nhớ cái nào ở đâu. Giờ là một tab, chia theo NHÓM
// CÔNG VIỆC chứ không theo chỗ dữ liệu được lưu:
//   nội dung → hình ảnh → video → tiếng → sao lưu → (cuối cùng) thiết lập chung của app.
const SECTIONS = [
  { id: "content", icon: "📖", label: "Nội dung & ngôn ngữ" },
  { id: "look", icon: "🎨", label: "Phong cách & prompt" },
  { id: "implicit", icon: "🧩", label: "Prompt ngầm" },
  { id: "image", icon: "🖼", label: "Ảnh" },
  { id: "video", icon: "🎬", label: "Video" },
  { id: "voice", icon: "🎙", label: "Giọng đọc" },
  { id: "music", icon: "🎵", label: "Nhạc nền" },
  { id: "backup", icon: "💾", label: "Preset & sao lưu" },
  { id: "app", icon: "⚙", label: "Ứng dụng" },
] as const;
type SectionId = (typeof SECTIONS)[number]["id"];

export default function SettingsTab({
  project,
  onSaved,
}: {
  project: Project;
  onSaved: (p: Project) => void;
}) {
  const [sec, setSec] = useState<SectionId>("content");
  const [opts, setOpts] = useState<any>(null);

  // ── state của dự án ───────────────────────────────────────
  const [s, setS] = useState({
    style: project.style ?? "",
    script_lang: project.script_lang ?? "Vietnamese",
    image_text_lang: project.image_text_lang ?? "Vietnamese",
    culture_hint: project.culture_hint ?? "",
    prompt_header: project.prompt_header ?? "",
    prompt_footer: project.prompt_footer ?? "",
    image_model: project.image_model ?? "",
    aspect_ratio: project.aspect_ratio ?? "VIDEO_ASPECT_RATIO_LANDSCAPE",
    video_model: project.video_model ?? "",
  });
  // Ghi đè prompt ngầm — một ô cho mỗi khoá của PROMPT_KEYS, trống = mặc định của agent.
  const [tpl, setTpl] = useState<Record<string, string>>(() =>
    Object.fromEntries(PROMPT_KEYS.map((k) => [k, (project as any)[`tpl_${k}`] ?? ""])));
  const [locFrames, setLocFrames] = useState(project.location_frames === 1 ? 1 : 4);
  const [shotDuration, setShotDuration] = useState(project.shot_duration ?? 8);
  const [storytelling, setStorytelling] = useState(!!project.storytelling);
  const [autoHires, setAutoHires] = useState(!!project.auto_hires);
  const [autoUpVideo, setAutoUpVideo] = useState(!!project.auto_upscale_video);
  const [upscaleRes, setUpscaleRes] = useState(project.upscale_res ?? "");
  const [seed, setSeed] = useState(project.seed ?? 0);
  const [bgmPath, setBgmPath] = useState(project.bgm_path ?? null);
  const [bgmVol, setBgmVol] = useState(project.bgm_volume ?? 0.18);
  const [bgmDuck, setBgmDuck] = useState(project.bgm_duck == null ? true : !!project.bgm_duck);
  const [voiceId, setVoiceId] = useState(project.voice_id ?? 0);
  const [ttsSpeed, setTtsSpeed] = useState(project.tts_speed ?? 1.0);
  const [ttsGap, setTtsGap] = useState(project.tts_gap ?? 0.4);
  const [ttsSentenceGap, setTtsSentenceGap] = useState(project.tts_sentence_gap ?? 0.3);
  const [ttsEdgePad, setTtsEdgePad] = useState(project.tts_edge_pad ?? 0.5);

  const [hiresInfo, setHiresInfo] = useState<
    { label: string; done: number; total: number; missing: number } | null>(null);
  const [upInfo, setUpInfo] = useState<
    { label: string; done: number; total: number; missing: number;
      choices: { value: string; label: string }[] } | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [presets, setPresets] = useState<SettingsPreset[]>([]);
  const [presetSel, setPresetSel] = useState("");
  const [showMusicManager, setShowMusicManager] = useState(false);
  const [testing, setTesting] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  // Nhóm "Ứng dụng" tự giữ state của nó và đăng ký hàm lưu lên đây, để thanh Lưu ở dưới
  // lưu được CẢ HAI phạm vi trong một lần bấm — không ai phải nhớ mình vừa sửa cái nào.
  const appSave = useRef<(() => Promise<void>) | null>(null);
  const [appDirty, setAppDirty] = useState(false);
  const registerAppSave = useCallback((fn: () => Promise<void>) => { appSave.current = fn; }, []);
  const markAppDirty = useCallback(() => setAppDirty(true), []);

  useEffect(() => {
    api.options().then(setOpts).catch(() => {});
    listVoices().then(setVoices).catch(() => {});
    api.listSettingsPresets().then((r) => setPresets(r.presets)).catch(() => {});
    // Tier quyết định trần độ phân giải (ONE → 2K, TWO → 4K) → hỏi server, không đoán ở client.
    storyboard.hiresStatus(project.id).then(setHiresInfo).catch(() => {});
    shotsApi.upscaleStatus(project.id).then(setUpInfo).catch(() => {});
  }, [project.id]);

  // Dự án chưa được agent bù mặc định (server bản cũ, hoặc khối ngầm vừa thêm) sẽ có ô rỗng.
  // Đổ bản mặc định vào ĐÚNG những ô đang rỗng ngay khi /options về, để lúc nào cũng có text
  // thật mà sửa. Không đụng ô đã có chữ nên không bao giờ đè lên cái người dùng đang gõ.
  useEffect(() => {
    const def = opts?.prompt_defaults;
    if (!def) return;
    setTpl((p) => {
      const next = { ...p };
      let changed = false;
      for (const k of PROMPT_KEYS) {
        if (!(next[k] ?? "").trim() && def[k]) { next[k] = def[k]; changed = true; }
      }
      return changed ? next : p;
    });
  }, [opts]);

  const set = (k: keyof typeof s, v: string) => setS((p) => ({ ...p, [k]: v }));

  const save = async () => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const updated = await api.updateProject(project.id, {
        ...s,
        bgm_volume: bgmVol, bgm_duck: bgmDuck, voice_id: voiceId,
        shot_duration: shotDuration, storytelling,
        auto_hires: autoHires, auto_upscale_video: autoUpVideo, upscale_res: upscaleRes,
        tts_speed: ttsSpeed, tts_gap: ttsGap, tts_sentence_gap: ttsSentenceGap,
        tts_edge_pad: ttsEdgePad, seed, location_frames: locFrames,
        ...Object.fromEntries(PROMPT_KEYS.map((k) => [`tpl_${k}`, tpl[k] ?? ""])),
      });
      onSaved(updated);
      if (appDirty && appSave.current) {
        await appSave.current();
        setAppDirty(false);
        setMsg("Đã lưu thiết lập dự án và thiết lập ứng dụng.");
      } else {
        setMsg("Đã lưu thiết lập dự án.");
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  // ── hành động rời rạc ─────────────────────────────────────
  const fetchMissingHires = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try {
      const r = await storyboard.genProjectHires(project.id);
      setMsg(r.total ? `Đang tải ${r.total} ảnh ${r.resolution} (chạy nền, xem ở thanh tiến trình).`
                     : "Mọi ảnh đã có bản độ phân giải cao.");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const upscaleMissingVideos = async () => {
    const n = upInfo?.missing ?? 0;
    // 4K (tier TWO) chưa đo được nên vẫn hỏi trước khi chạy hàng loạt; 1080p đo được là miễn phí.
    if (!window.confirm(
      `Upscale ${n} video lên ${upInfo?.label}?\n\n` +
      `Mỗi video là một lượt render thật trên Flow (~1 phút/video)` +
      (upInfo?.label === "4K" ? " và bản 4K có thể tốn credit." : ", đo được là không tốn credit.")
    )) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      const r = await shotsApi.upscaleAll(project.id);
      setMsg(r.total ? `Đang upscale ${r.total} video lên ${r.resolution} (chạy nền).`
                     : "Mọi video đã có bản độ phân giải cao.");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const testVoice = async () => {
    setTesting(true); setErr(null);
    try {
      const r = await synthesize("Xin chào, đây là giọng đọc của dự án.", voiceId, ttsSpeed);
      if (r.audio && audioRef.current) {
        audioRef.current.src = base64ToAudioUrl(r.audio);
        await audioRef.current.play().catch(() => {});
      } else setErr("TTS không trả về audio (kiểm tra OmniVoice URL ở nhóm Ứng dụng).");
    } catch (e: any) { setErr(e.message); } finally { setTesting(false); }
  };

  const onPickBgm = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true); setErr(null);
    try {
      const updated = await api.uploadBgm(project.id, file, bgmVol);
      setBgmPath(updated.bgm_path ?? null);
      onSaved(updated);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const removeBgm = async () => {
    setBusy(true); setErr(null);
    try {
      const updated = await api.clearBgm(project.id);
      setBgmPath(null);
      onSaved(updated);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  // ── Xuất/nhập THIẾT LẬP tái dùng được (không phải nội dung dự án) ─────────
  // Nhạc nền đi kèm: preset mang path của dự án nguồn, applySettings CHÉP sang dự án này.
  const STR_KEYS = ["style", "script_lang", "image_text_lang", "culture_hint",
    "prompt_header", "prompt_footer", "image_model", "aspect_ratio", "video_model", "upscale_res",
    // Prompt ngầm đi theo preset: đó chính là thứ làm nên "chất" của một kênh.
    ...PROMPT_KEYS.map((k) => `tpl_${k}`)] as const;
  const NUM_KEYS = ["shot_duration", "seed", "bgm_volume", "voice_id",
    "tts_speed", "tts_gap", "tts_sentence_gap", "tts_edge_pad", "location_frames"] as const;
  const BOOL_KEYS = ["storytelling", "auto_hires", "auto_upscale_video", "bgm_duck"] as const;

  const collectSettings = () => ({
    ...s, ...Object.fromEntries(PROMPT_KEYS.map((k) => [`tpl_${k}`, tpl[k] ?? ""])),
    location_frames: locFrames,
    shot_duration: shotDuration, storytelling, auto_hires: autoHires,
    auto_upscale_video: autoUpVideo, upscale_res: upscaleRes,
    seed, bgm_volume: bgmVol, bgm_duck: bgmDuck, bgm_path: bgmPath,
    voice_id: voiceId, tts_speed: ttsSpeed, tts_gap: ttsGap,
    tts_sentence_gap: ttsSentenceGap, tts_edge_pad: ttsEdgePad,
  });

  const applySettings = async (obj: any, label = "thiết lập") => {
    if (!obj || typeof obj !== "object") { setErr("Dữ liệu thiết lập không hợp lệ"); return; }
    setBusy(true); setErr(null); setMsg(null);
    try {
      const fields: any = {};
      for (const k of STR_KEYS) if (typeof obj[k] === "string") fields[k] = obj[k];
      for (const k of NUM_KEYS) if (typeof obj[k] === "number") fields[k] = obj[k];
      for (const k of BOOL_KEYS) if (typeof obj[k] === "boolean") fields[k] = obj[k];
      if (!Object.keys(fields).length) throw new Error("Không có thiết lập hợp lệ");
      const u = await api.updateProject(project.id, fields);
      setS((p) => ({
        style: u.style ?? p.style, script_lang: u.script_lang ?? p.script_lang,
        image_text_lang: u.image_text_lang ?? p.image_text_lang,
        culture_hint: u.culture_hint ?? p.culture_hint,
        prompt_header: u.prompt_header ?? p.prompt_header,
        prompt_footer: u.prompt_footer ?? p.prompt_footer,
        image_model: u.image_model ?? p.image_model, aspect_ratio: u.aspect_ratio ?? p.aspect_ratio,
        video_model: u.video_model ?? p.video_model,
      }));
      setTpl(Object.fromEntries(PROMPT_KEYS.map((k) => [k, (u as any)[`tpl_${k}`] ?? ""])));
      if (u.location_frames != null) setLocFrames(u.location_frames === 1 ? 1 : 4);
      if (u.shot_duration != null) setShotDuration(u.shot_duration);
      if (u.storytelling != null) setStorytelling(!!u.storytelling);
      if (u.auto_hires != null) setAutoHires(!!u.auto_hires);
      if (u.auto_upscale_video != null) setAutoUpVideo(!!u.auto_upscale_video);
      if (u.upscale_res != null) setUpscaleRes(u.upscale_res);
      if (u.seed != null) setSeed(u.seed);
      if (u.bgm_volume != null) setBgmVol(u.bgm_volume);
      if (u.bgm_duck != null) setBgmDuck(!!u.bgm_duck);
      if (u.voice_id != null) setVoiceId(u.voice_id);
      if (u.tts_speed != null) setTtsSpeed(u.tts_speed);
      if (u.tts_gap != null) setTtsGap(u.tts_gap);
      if (u.tts_sentence_gap != null) setTtsSentenceGap(u.tts_sentence_gap);
      if (u.tts_edge_pad != null) setTtsEdgePad(u.tts_edge_pad);

      // Lỗi chép nhạc KHÔNG được làm hỏng cả lượt áp dụng — thiết lập khác đã lưu xong.
      let applied = u;
      let bgmNote = "";
      const srcBgm = typeof obj.bgm_path === "string" ? obj.bgm_path.trim() : "";
      if (srcBgm && srcBgm !== (u.bgm_path ?? "")) {
        try {
          applied = await api.copyBgm(project.id, srcBgm, obj.bgm_volume);
          setBgmPath(applied.bgm_path ?? null);
          bgmNote = " (kèm nhạc nền)";
        } catch {
          bgmNote = " — nhưng KHÔNG chép được nhạc nền (file nguồn đã bị xoá?)";
        }
      }
      onSaved(applied);
      setMsg(`Đã áp dụng ${Object.keys(fields).length} ${label}${bgmNote}.`);
    } catch (e: any) {
      setErr("Áp dụng thiết lập lỗi: " + (e.message || e));
    } finally { setBusy(false); }
  };

  const exportSettings = () => {
    const payload = { _type: "flowkit-project-settings", version: 1, ...collectSettings() };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `flowkit-settings-${(project.title || "project").replace(/[^\w-]+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importSettings = async (file: File | undefined) => {
    if (!file) return;
    try {
      await applySettings(JSON.parse(await file.text()), "thiết lập từ file");
    } catch { setErr("File JSON không hợp lệ"); }
  };

  const saveAsPreset = async () => {
    const name = window.prompt("Tên preset thiết lập:");
    if (!name?.trim()) return;
    try {
      const r = await api.saveSettingsPreset(name.trim(), collectSettings());
      setPresets(r.presets);
      setMsg(`Đã lưu preset "${name.trim()}".`);
    } catch (e: any) { setErr(e.message); }
  };

  const deletePreset = async (id: string) => {
    const p = presets.find((x) => x.id === id);
    if (!p || !window.confirm(`Xóa preset "${p.name}"?`)) return;
    try {
      const r = await api.deleteSettingsPreset(id);
      setPresets(r.presets);
      setPresetSel("");
    } catch (e: any) { setErr(e.message); }
  };

  const bgmName = bgmPath ? bgmPath.replace(/\\/g, "/").split("/").pop() : null;
  const current = SECTIONS.find((x) => x.id === sec)!;

  return (
    <div className="flex h-full">
      {/* sub-nav: các nhóm thiết lập. Tách khỏi nội dung để còn chỗ thêm option về sau mà
          không biến trang thành một cuộn dài vô tận như modal cũ. */}
      <nav className="w-56 shrink-0 space-y-0.5 overflow-y-auto border-r border-neutral-800 p-3">
        <div className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wide text-neutral-600">
          Dự án này
        </div>
        {SECTIONS.map((x) => (
          <div key={x.id}>
            {x.id === "app" && (
              <div className="mb-2 mt-4 px-2 text-[11px] font-medium uppercase tracking-wide text-neutral-600">
                Mọi dự án
              </div>
            )}
            <button
              onClick={() => setSec(x.id)}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition ${
                sec === x.id
                  ? "bg-neutral-800 text-white"
                  : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
              }`}
            >
              <span className="text-base leading-none">{x.icon}</span>
              <span className="truncate">{x.label}</span>
              {x.id === "app" && appDirty && (
                <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
              )}
            </button>
          </div>
        ))}
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 overflow-auto px-8 py-6">
          <div className="mx-auto max-w-3xl space-y-6">
            <h2 className="text-xl font-semibold">
              <span className="mr-2">{current.icon}</span>{current.label}
            </h2>

            {err && <div className="rounded-lg bg-rose-950/40 px-3 py-2 text-sm text-rose-300">{err}</div>}
            {msg && <div className="rounded-lg bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">{msg}</div>}

            {sec === "content" && (
              <>
                <Group title="Ngôn ngữ">
                  <Field
                    label="Kịch bản / lời thoại / lời đọc"
                    hint="Kịch bản, hội thoại, voiceover và SEO viết bằng ngôn ngữ này. Áp dụng cho các lần sinh/sửa kịch bản SAU."
                  >
                    <input value={s.script_lang} onChange={(e) => set("script_lang", e.target.value)}
                      placeholder="Tiếng Việt" className={inp} />
                  </Field>
                  <Field
                    label="Chữ viết/vẽ trong ảnh"
                    hint="Mọi chữ/biển/nhãn hiện trong ảnh viết bằng ngôn ngữ này. Từ đặc thù ngôn ngữ khác (thuật ngữ, nhãn hiệu) được giữ nguyên."
                  >
                    <input value={s.image_text_lang} onChange={(e) => set("image_text_lang", e.target.value)}
                      placeholder="Tiếng Việt" className={inp} />
                  </Field>
                </Group>

                <Group title="Bối cảnh văn hoá">
                  <Field
                    label="Culture hint (tự nhận từ kịch bản)"
                    hint="Giữ hình ảnh đúng với gốc câu chuyện — truyện VN ra phong cách VN, truyện Nhật ra Nhật…"
                  >
                    <textarea value={s.culture_hint} onChange={(e) => set("culture_hint", e.target.value)}
                      placeholder="vd: Vietnamese folk tale, traditional Vietnamese architecture, áo dài…"
                      className={`${inp} h-24 resize-none`} />
                  </Field>
                </Group>

                <Group title="Cách kể">
                  <label className="flex items-start gap-2.5 text-sm text-neutral-300">
                    <input type="checkbox" checked={storytelling}
                      onChange={(e) => setStorytelling(e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-indigo-500" />
                    <span>
                      Chế độ Storytelling
                      <span className="block text-xs text-neutral-600">
                        Giọng đọc dẫn dắt, đọc nguyên văn nội dung gốc.
                      </span>
                    </span>
                  </label>
                </Group>
              </>
            )}

            {sec === "look" && (
              <>
                <Group title="Style" hint="Luôn được đưa lên ĐẦU mỗi prompt ảnh/video.">
                  <input value={s.style} onChange={(e) => set("style", e.target.value)}
                    placeholder="vd: chibi ghibli, watercolor" className={inp} />
                  <div className="flex flex-wrap gap-1">
                    {(opts?.style_presets || []).map((p: string) => (
                      <button key={p} onClick={() => set("style", p)}
                        className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300 hover:bg-neutral-700">
                        {p}
                      </button>
                    ))}
                  </div>
                </Group>

                <Group
                  title="Prompt bao ngoài"
                  hint="Chèn vào mọi prompt ảnh/video. Dùng cho quy ước cố định của kênh (tỉ lệ, chất lượng, ngôn ngữ chữ…)."
                >
                  {/* Cao ~9 dòng và cho kéo dãn thêm (resize-y): header/footer thường là cả
                      một đoạn quy ước dài, ô 4 dòng cũ phải cuộn mới đọc hết. */}
                  <Field label="Header — chèn vào ĐẦU">
                    <textarea value={s.prompt_header} onChange={(e) => set("prompt_header", e.target.value)}
                      placeholder="vd: always output in Vietnamese" className={`${inp} h-48 resize-y`} />
                  </Field>
                  <Field label="Footer — chèn vào CUỐI">
                    <textarea value={s.prompt_footer} onChange={(e) => set("prompt_footer", e.target.value)}
                      placeholder="vd: super detailed, cinematic lighting, 8k, sharp focus"
                      className={`${inp} h-48 resize-y`} />
                  </Field>
                </Group>

                <Group title="Tái lập kết quả">
                  <Field
                    label="🔒 Seed"
                    hint="Số > 0 → mọi lần tạo ảnh dùng cùng seed, cùng prompt/ref cho ra ảnh giống nhau. 0 hoặc trống = ngẫu nhiên. (Tạo nhiều mẫu 🎲 vẫn random để có lựa chọn.)"
                  >
                    <input type="number" min={0} value={seed}
                      onChange={(e) => setSeed(Math.max(0, Number(e.target.value) || 0))}
                      placeholder="0 = ngẫu nhiên" className={`${inp} max-w-[12rem]`} />
                  </Field>
                </Group>
              </>
            )}

            {sec === "implicit" && (
              <ImplicitPrompts
                values={tpl}
                defaults={opts?.prompt_defaults || {}}
                onChange={(k: PromptKey, v: string) => setTpl((p) => ({ ...p, [k]: v }))}
              />
            )}

            {sec === "image" && (
              <>
                <Group title="Model">
                  <Field label="Image model">
                    <select value={s.image_model} onChange={(e) => set("image_model", e.target.value)} className={inp}>
                      <option value="">(mặc định)</option>
                      {(opts?.image_models || []).map((m: string) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </Field>
                </Group>

                <Group
                  title="Ảnh tham chiếu bối cảnh"
                  hint="Áp dụng cho các lần sinh ảnh bối cảnh SAU. Ảnh cũ giữ nguyên — muốn đổi thì tạo lại ảnh của entity đó."
                >
                  <div className="grid gap-2 sm:grid-cols-2">
                    {[
                      { n: 4, t: "Lưới 2x2 — 4 góc máy", d: "Một ảnh chia bốn ô: toàn cảnh, góc ngược, trên cao, cận cảnh — có dán nhãn từng ô. Shot chọn một góc phù hợp." },
                      { n: 1, t: "Một ảnh — 1 góc máy", d: "Một khung establishing duy nhất, không lưới, không nhãn. Ảnh nét hơn vì không phải chia tư, nhưng shot chỉ có một góc để bám." },
                    ].map((o) => (
                      <button key={o.n} type="button" onClick={() => setLocFrames(o.n)}
                        className={`rounded-lg border p-3 text-left transition ${
                          locFrames === o.n
                            ? "border-indigo-500 bg-indigo-500/10"
                            : "border-neutral-700 hover:border-neutral-600 hover:bg-neutral-900"
                        }`}>
                        <div className="flex items-center gap-2 text-sm text-neutral-200">
                          <span className={`h-3 w-3 shrink-0 rounded-full border ${
                            locFrames === o.n ? "border-indigo-400 bg-indigo-500" : "border-neutral-600"
                          }`} />
                          {o.t}
                        </div>
                        <p className="mt-1 text-xs leading-relaxed text-neutral-500">{o.d}</p>
                      </button>
                    ))}
                  </div>
                  <p className="text-xs leading-relaxed text-neutral-600">
                    Chọn cái nào thì prompt tương ứng ở nhóm <b>🧩 Prompt ngầm</b> được dùng
                    (“Bối cảnh — lưới 4 khung” hoặc “Bối cảnh — một ảnh”).
                  </p>
                </Group>

                <Group
                  title="Độ phân giải cao"
                  hint="Ảnh Flow trả về chỉ là bản HD. Bản phóng to dùng khi DỰNG VIDEO TỪ ẢNH và EXPORT DaVinci Resolve. Trần theo tier: ONE → 2K, TWO → 4K. Ảnh hiển thị trong app vẫn là bản HD cho nhẹ."
                >
                  <label className="flex items-center gap-2.5 text-sm text-neutral-300">
                    <input type="checkbox" checked={autoHires}
                      onChange={(e) => setAutoHires(e.target.checked)}
                      className="h-4 w-4 accent-indigo-500" />
                    Tự tải bản {hiresInfo?.label ?? "2K/4K"} sau mỗi lần sinh ảnh
                  </label>
                  {hiresInfo && (
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-neutral-500">
                        {hiresInfo.done}/{hiresInfo.total} ảnh đã có bản {hiresInfo.label}
                      </span>
                      {hiresInfo.missing > 0 && (
                        <button onClick={fetchMissingHires} disabled={busy}
                          title="Tải bù bản độ phân giải cao cho các ảnh đã sinh trước đó"
                          className="rounded-lg border border-neutral-700 px-2.5 py-1 text-xs hover:bg-neutral-800 disabled:opacity-40">
                          ⬇ Tải bù {hiresInfo.missing} ảnh
                        </button>
                      )}
                    </div>
                  )}
                </Group>
              </>
            )}

            {sec === "video" && (
              <>
                <Group title="Khung hình & nhịp">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Khung hình">
                      <select value={s.aspect_ratio} onChange={(e) => set("aspect_ratio", e.target.value)} className={inp}>
                        <option value="VIDEO_ASPECT_RATIO_LANDSCAPE">16:9 ngang</option>
                        <option value="VIDEO_ASPECT_RATIO_PORTRAIT">9:16 dọc</option>
                      </select>
                    </Field>
                    <Field label="Độ dài shot (giây)">
                      <input type="number" min={1} max={10} value={shotDuration}
                        onChange={(e) => setShotDuration(Math.min(10, Math.max(1, Number(e.target.value) || 8)))}
                        className={inp} />
                    </Field>
                  </div>
                </Group>

                <Group title="Model video">
                  <select value={s.video_model} onChange={(e) => set("video_model", e.target.value)} className={inp}>
                    {(opts?.video_engines || [{ value: "", label: "Veo i2v (mặc định)" }]).map(
                      (m: { value: string; label: string }) => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                  </select>
                  <p className="text-xs leading-relaxed text-neutral-600">
                    Veo i2v dựng video TỪ ảnh frame (model cụ thể tự chọn theo tier + khung hình).
                    Omni Flash là r2v — ảnh frame thành ảnh tham chiếu — và cho chọn thẳng độ dài
                    clip, nên beat 10s chỉ cần MỘT clip thay vì hai clip Veo 8s nối nhau; motion
                    prompt cũng được viết theo mốc thời gian <code>[00:04]</code> để clip có nhiều
                    pha chuyển động thay vì một cú máy đơn điệu.
                  </p>
                  <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs leading-relaxed text-neutral-400">
                    ⚠ <b className="text-amber-500/90">Watermark</b>: cả hai đều đóng dấu ở góc dưới
                    phải và hiện suốt clip. Omni đóng dấu <b>✦ Gemini</b> trắng, to và lùi vào trong
                    khung — rõ hơn nhiều so với chữ <b>“Veo”</b> xám nhỏ sát mép. Bản upscale 1080p
                    còn làm dấu Veo đậm hơn bản 720p. Nếu góc dưới phải là vùng quan trọng, cân nhắc
                    bố cục chừa chỗ hoặc chèn overlay/lower-third của kênh vào đó.
                  </p>
                </Group>

                <Group
                  title="Upscale"
                  hint="Video render ra cũng chỉ là bản HD. Trần theo tier: ONE → Full HD 1080p, TWO → 4K. Mỗi video mất ~1 phút (Flow render lại). Đo thực tế: lên 1080p KHÔNG trừ credit; bản 4K chưa kiểm chứng. Shot ghép từ nhiều clip (chained) không upscale được."
                >
                  <label className="flex items-center gap-2.5 text-sm text-neutral-300">
                    <input type="checkbox" checked={autoUpVideo}
                      onChange={(e) => setAutoUpVideo(e.target.checked)}
                      className="h-4 w-4 accent-indigo-500" />
                    Tự upscale {upInfo?.label ? `(${upInfo.label})` : "(1080p/4K)"} sau mỗi lần render
                  </label>
                  {(upInfo?.choices?.length ?? 0) > 1 && (
                    <Field label="Mức upscale">
                      <select value={upscaleRes} onChange={(e) => setUpscaleRes(e.target.value)}
                        title="Tier TWO có thể chọn Full HD thay vì 4K cho file nhẹ và rẻ hơn"
                        className={`${inp} max-w-xs`}>
                        <option value="">Cao nhất tier cho phép</option>
                        {upInfo!.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                      </select>
                    </Field>
                  )}
                  {upInfo && (
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-neutral-500">
                        {upInfo.done}/{upInfo.total} video đã có bản {upInfo.label}
                      </span>
                      {upInfo.missing > 0 && (
                        <button onClick={upscaleMissingVideos} disabled={busy}
                          title="Upscale bù các video đã render trước đó"
                          className="rounded-lg border border-neutral-700 px-2.5 py-1 text-xs hover:bg-neutral-800 disabled:opacity-40">
                          ⬆ Upscale {upInfo.missing} video
                        </button>
                      )}
                    </div>
                  )}
                </Group>
              </>
            )}

            {sec === "voice" && (
              <>
                <Group title="Giọng đọc">
                  <div className="flex gap-2">
                    <select value={voiceId} onChange={(e) => setVoiceId(Number(e.target.value))} className={inp}>
                      <option value={0}>Mặc định (id 0)</option>
                      {voices.map((v) => (
                        <option key={v.voice_id} value={v.voice_id}>{v.title} (id {v.voice_id})</option>
                      ))}
                    </select>
                    <button onClick={testVoice} disabled={testing} title="Nghe thử giọng đã chọn"
                      className="shrink-0 rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-40">
                      {testing ? "…" : "▶ Test"}
                    </button>
                  </div>
                  <p className="text-xs text-neutral-600">
                    Thêm/quản lý giọng ở nhóm <b>⚙ Ứng dụng → Kho giọng đọc</b>. Cần OmniVoice URL để test.
                  </p>
                  <Slider label="Tốc độ đọc" value={ttsSpeed} onChange={setTtsSpeed}
                    min={0.5} max={1.5} format={(v) => `${v.toFixed(2)}×`} />
                  <audio ref={audioRef} className="hidden" />
                </Group>

                <Group
                  title="Khoảng lặng"
                  hint="Cả ba đều cần chạy lại “Dựng theo lời đọc” (hoặc “Dựng lại audio”) mới có hiệu lực."
                >
                  <Slider label="Nghỉ giữa đoạn" value={ttsGap} onChange={setTtsGap} min={0} max={2}
                    hint="Scene được đọc LIỀN MẠCH theo từng đoạn (tách ở dòng trống); đây là khoảng lặng chèn GIỮA CÁC ĐOẠN. Đặt ≈1.0s nếu dùng cross-dissolve để hiệu ứng nằm trọn trong khoảng lặng." />
                  <Slider label="Nghỉ cuối câu" value={ttsSentenceGap} onChange={setTtsSentenceGap} min={0} max={1.5}
                    hint="Chèn thêm sau mỗi câu (. ! ? … ; : —) để OmniVoice không đọc dồn. WhisperX canh mốc nên chỉ chèn ĐÚNG cuối câu, không cắt giữa câu." />
                  <Slider label="Đệm 2 đầu" value={ttsEdgePad} onChange={setTtsEdgePad} min={0} max={2}
                    hint="Khoảng lặng ở ĐẦU và CUỐI mỗi WAV scene, làm “tay cầm” cho cross-dissolve khi dựng — hiệu ứng nằm trọn trong khoảng lặng, không nuốt lời đọc. ≈0.5s phủ một dissolve 24 frame." />
                </Group>
              </>
            )}

            {sec === "music" && (
              <Group
                title="Nhạc nền"
                hint="MỘT bài trộn CHÌM dưới lời đọc khi ghép video. Khác với playlist của chế độ music video (tab Nhạc), nơi nhạc là tiếng duy nhất và quyết định độ dài video."
              >
                {bgmName ? (
                  <div className="flex items-center justify-between rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
                    <span className="truncate text-neutral-200">🎵 {bgmName}</span>
                    <div className="ml-2 flex shrink-0 gap-3">
                      <button onClick={() => setShowMusicManager(true)} disabled={busy}
                        className="text-indigo-400 hover:text-indigo-300 disabled:opacity-40">Đổi bài</button>
                      <button onClick={removeBgm} disabled={busy}
                        className="text-rose-400 hover:text-rose-300 disabled:opacity-40">Gỡ</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <label className="flex flex-1 cursor-pointer items-center justify-center rounded-lg border border-dashed border-neutral-700 px-3 py-3 text-sm text-neutral-400 hover:border-indigo-500 hover:text-neutral-200">
                      {busy ? "Đang tải…" : "＋ Chọn file nhạc"}
                      <input type="file" accept="audio/*" className="hidden"
                        onChange={(e) => onPickBgm(e.target.files?.[0])} />
                    </label>
                    <button type="button" onClick={() => setShowMusicManager(true)} disabled={busy}
                      className="flex-1 rounded-lg border border-dashed border-neutral-700 px-3 py-3 text-sm text-neutral-400 hover:border-indigo-500 hover:text-neutral-200 disabled:opacity-40">
                      🎧 Sinh bằng Flow Music
                    </button>
                  </div>
                )}
                <Slider label="Âm lượng nhạc" value={bgmVol} onChange={setBgmVol} min={0} max={0.6} step={0.02}
                  format={(v) => `${Math.round(v * 100)}%`} />
                <label className="flex items-start gap-2.5 text-sm text-neutral-300">
                  <input type="checkbox" checked={bgmDuck}
                    onChange={(e) => setBgmDuck(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-indigo-500" />
                  <span>
                    Tự giảm nhạc khi có giọng đọc (ducking)
                    <span className="block text-xs text-neutral-600">
                      Bật: nhạc tự nhỏ lại lúc đang đọc và to lên ở khoảng lặng. Tắt: giữ mức cố định
                      ở trên. Giọng đọc luôn giữ nguyên âm lượng.
                    </span>
                  </span>
                </label>
              </Group>
            )}

            {sec === "backup" && (
              <>
                <Group
                  title="Preset thiết lập"
                  hint="Lưu toàn bộ thiết lập của dự án này thành preset để áp cho dự án khác. Nạp preset là ÁP DỤNG NGAY (không cần bấm Lưu)."
                >
                  <div className="flex gap-2">
                    <select
                      value={presetSel}
                      onChange={(e) => {
                        setPresetSel(e.target.value);
                        const p = presets.find((x) => x.id === e.target.value);
                        if (p) applySettings(p.settings, `preset "${p.name}"`);
                      }}
                      className={inp}
                    >
                      <option value="">Chọn preset để nạp…</option>
                      {presets.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                    {presetSel && (
                      <button onClick={() => deletePreset(presetSel)} title="Xóa preset đang chọn"
                        className="shrink-0 rounded-lg border border-neutral-700 px-2.5 py-1.5 text-sm text-rose-300 hover:bg-rose-950/40">
                        🗑
                      </button>
                    )}
                    <button onClick={saveAsPreset} title="Lưu thiết lập hiện tại thành preset trong app"
                      className="shrink-0 rounded-lg border border-neutral-700 px-2.5 py-1.5 text-sm hover:bg-neutral-800">
                      💾 Lưu thành preset
                    </button>
                  </div>
                </Group>

                <Group
                  title="Xuất / nhập thiết lập"
                  hint="File .json chỉ chứa THIẾT LẬP (style, prompt, model, TTS, nhạc nền…), không đụng tới kịch bản/ảnh/video. Nhạc nền đi kèm sẽ được chép sang dự án đích."
                >
                  <div className="flex gap-2">
                    <button onClick={exportSettings}
                      className="flex-1 rounded-lg border border-neutral-700 py-2 text-center text-sm text-neutral-300 hover:bg-neutral-800">
                      ⤓ Xuất thiết lập (.json)
                    </button>
                    <label className="flex-1 cursor-pointer rounded-lg border border-neutral-700 py-2 text-center text-sm text-neutral-300 hover:bg-neutral-800">
                      ⤒ Nhập thiết lập
                      <input type="file" accept="application/json,.json" className="hidden" disabled={busy}
                        onChange={(e) => { importSettings(e.target.files?.[0]); e.target.value = ""; }} />
                    </label>
                  </div>
                </Group>

                <Group title="Sao lưu dự án" hint="Toàn bộ dữ liệu (rows DB + media) để chuyển máy hoặc lưu trữ.">
                  <a href={projectExportUrl(project.id)} download
                    className="block rounded-lg border border-neutral-700 py-2 text-center text-sm text-neutral-300 hover:bg-neutral-800">
                    ⬇ Xuất dự án (.zip)
                  </a>
                </Group>
              </>
            )}

            {/* Luôn mounted, chỉ ẩn đi: nhóm này tự giữ state của nó, unmount là mất phần
                đang sửa dở trong khi chấm "chưa lưu" vẫn sáng — vừa mất công vừa khó hiểu. */}
            <div className={sec === "app" ? "" : "hidden"}>
              <AppSettingsSection onDirty={markAppDirty} registerSave={registerAppSave} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 border-t border-neutral-800 px-8 py-3">
          <span className="text-xs text-neutral-600">
            {appDirty
              ? "Lưu cả thiết lập dự án và thiết lập ứng dụng."
              : "Áp dụng cho dự án đang mở."}
          </span>
          <button onClick={save} disabled={busy}
            className="ml-auto rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40">
            {busy ? "Đang lưu…" : "Lưu thiết lập"}
          </button>
        </div>
      </div>

      {showMusicManager && (
        <MusicManager
          project={project}
          volume={bgmVol}
          onApplied={(updated) => {
            setBgmPath(updated.bgm_path ?? null);
            if (updated.bgm_volume != null) setBgmVol(updated.bgm_volume);
            onSaved(updated);
          }}
          onClose={() => setShowMusicManager(false)}
        />
      )}
    </div>
  );
}
