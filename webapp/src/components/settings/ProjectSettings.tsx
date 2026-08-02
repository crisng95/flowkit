import { useEffect, useRef, useState } from "react";
import {
  api,
  listVoices,
  synthesize,
  base64ToAudioUrl,
  projectExportUrl,
  type Project,
  storyboard,
  shots as shotsApi,
  type SettingsPreset,
  type Voice,
} from "../../api/client";
import MusicManager from "../music/MusicManager";

// Per-project settings: prompt header/footer (always prepended/appended to every
// image & video prompt), culture hint, style, and the image model.
export default function ProjectSettings({
  project,
  onClose,
  onSaved,
}: {
  project: Project;
  onClose: () => void;
  onSaved: (p: Project) => void;
}) {
  const [opts, setOpts] = useState<any>(null);
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
  const [shotDuration, setShotDuration] = useState<number>(project.shot_duration ?? 8);
  const [storytelling, setStorytelling] = useState<boolean>(!!project.storytelling);
  const [autoHires, setAutoHires] = useState<boolean>(!!project.auto_hires);
  const [hiresInfo, setHiresInfo] = useState<{ label: string; done: number; total: number; missing: number } | null>(null);
  const [autoUpVideo, setAutoUpVideo] = useState<boolean>(!!project.auto_upscale_video);
  const [upInfo, setUpInfo] = useState<
    { label: string; done: number; total: number; missing: number;
      choices: { value: string; label: string }[] } | null>(null);
  const [upscaleRes, setUpscaleRes] = useState<string>(project.upscale_res ?? "");
  const [seed, setSeed] = useState<number>(project.seed ?? 0);
  const [showMusicManager, setShowMusicManager] = useState(false);
  const [bgmPath, setBgmPath] = useState(project.bgm_path ?? null);
  const [bgmVol, setBgmVol] = useState(project.bgm_volume ?? 0.18);
  const [bgmDuck, setBgmDuck] = useState<boolean>(project.bgm_duck == null ? true : !!project.bgm_duck);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState<number>(project.voice_id ?? 0);
  const [ttsSpeed, setTtsSpeed] = useState<number>(project.tts_speed ?? 1.0);
  const [ttsGap, setTtsGap] = useState<number>(project.tts_gap ?? 0.4);
  const [ttsSentenceGap, setTtsSentenceGap] = useState<number>(project.tts_sentence_gap ?? 0.3);
  const [ttsEdgePad, setTtsEdgePad] = useState<number>(project.tts_edge_pad ?? 0.5);
  const [testing, setTesting] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [presets, setPresets] = useState<SettingsPreset[]>([]);
  const [presetSel, setPresetSel] = useState("");

  useEffect(() => {
    api.options().then(setOpts).catch(() => {});
    listVoices().then(setVoices).catch(() => {});
    api.listSettingsPresets().then((r) => setPresets(r.presets)).catch(() => {});
    // Tier quyết định trần độ phân giải (ONE → 2K, TWO → 4K) → hỏi server, không đoán ở client.
    storyboard.hiresStatus(project.id).then(setHiresInfo).catch(() => {});
    shotsApi.upscaleStatus(project.id).then(setUpInfo).catch(() => {});
  }, [project.id]);

  // Upscale bù video chưa có bản độ phân giải cao. Mỗi video là một lượt render → tốn credit.
  const upscaleMissingVideos = async () => {
    const n = upInfo?.missing ?? 0;
    // 4K (tier TWO) chưa đo được nên vẫn hỏi trước khi chạy hàng loạt; 1080p đo được là miễn phí.
    if (!window.confirm(
      `Upscale ${n} video lên ${upInfo?.label}?\n\n` +
      `Mỗi video là một lượt render thật trên Flow (~1 phút/video)` +
      (upInfo?.label === "4K" ? " và bản 4K có thể tốn credit." : ", đo được là không tốn credit.")
    )) return;
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const r = await shotsApi.upscaleAll(project.id);
      setMsg(r.total ? `Đang upscale ${r.total} video lên ${r.resolution} (chạy nền).`
                     : "Mọi video đã có bản độ phân giải cao.");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  // Tải bù bản 2K/4K cho những ảnh còn thiếu (ảnh sinh trước khi bật tuỳ chọn này).
  const fetchMissingHires = async () => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const r = await storyboard.genProjectHires(project.id);
      setMsg(r.total ? `Đang tải ${r.total} ảnh ${r.resolution} (chạy nền, xem ở thanh tiến trình).`
                     : "Mọi ảnh đã có bản độ phân giải cao.");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const testVoice = async () => {
    setTesting(true);
    setErr(null);
    try {
      const r = await synthesize("Xin chào, đây là giọng đọc của dự án.", voiceId, ttsSpeed);
      if (r.audio && audioRef.current) {
        audioRef.current.src = base64ToAudioUrl(r.audio);
        await audioRef.current.play().catch(() => {});
      } else setErr("TTS không trả về audio (kiểm tra OmniVoice URL trong Settings).");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setTesting(false);
    }
  };

  const set = (k: keyof typeof s, v: string) => setS((p) => ({ ...p, [k]: v }));

  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.updateProject(project.id, {
        ...s,
        bgm_volume: bgmVol,
        bgm_duck: bgmDuck,
        voice_id: voiceId,
        shot_duration: shotDuration,
        storytelling,
        auto_hires: autoHires,
        auto_upscale_video: autoUpVideo,
        upscale_res: upscaleRes,
        tts_speed: ttsSpeed,
        tts_gap: ttsGap,
        tts_sentence_gap: ttsSentenceGap,
        tts_edge_pad: ttsEdgePad,
        seed,
      });
      onSaved(updated);
      onClose();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const onPickBgm = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.uploadBgm(project.id, file, bgmVol);
      setBgmPath(updated.bgm_path ?? null);
      onSaved(updated);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const removeBgm = async () => {
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.clearBgm(project.id);
      setBgmPath(null);
      onSaved(updated);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  // ── Export / import REUSABLE settings (not project content) so the same setup can be
  // applied to other projects without redoing it by hand. The BGM travels too — as the source
  // project's path, which applySettings COPIES into this project (see copyBgm). Without it,
  // loading a preset still left you hunting for the same music file by hand every time.
  const STR_KEYS = ["style", "script_lang", "image_text_lang", "culture_hint",
    "prompt_header", "prompt_footer", "image_model", "aspect_ratio", "video_model", "upscale_res"] as const;
  const NUM_KEYS = ["shot_duration", "seed", "bgm_volume", "voice_id",
    "tts_speed", "tts_gap", "tts_sentence_gap", "tts_edge_pad"] as const;
  const BOOL_KEYS = ["storytelling", "auto_hires", "auto_upscale_video", "bgm_duck"] as const;

  const collectSettings = () => ({
    ...s, shot_duration: shotDuration, storytelling, auto_hires: autoHires,
    auto_upscale_video: autoUpVideo, upscale_res: upscaleRes,
    seed, bgm_volume: bgmVol, bgm_duck: bgmDuck, bgm_path: bgmPath,
    voice_id: voiceId, tts_speed: ttsSpeed, tts_gap: ttsGap, tts_sentence_gap: ttsSentenceGap,
    tts_edge_pad: ttsEdgePad,
  });

  // Apply a settings object (from a file OR a saved preset) to this project immediately,
  // type-guarding each field, then reflect the persisted values back into the form.
  const applySettings = async (obj: any, label = "thiết lập") => {
    if (!obj || typeof obj !== "object") { setErr("Dữ liệu thiết lập không hợp lệ"); return; }
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const fields: any = {};
      for (const k of STR_KEYS) if (typeof obj[k] === "string") fields[k] = obj[k];
      for (const k of NUM_KEYS) if (typeof obj[k] === "number") fields[k] = obj[k];
      for (const k of BOOL_KEYS) if (typeof obj[k] === "boolean") fields[k] = obj[k];
      if (!Object.keys(fields).length) throw new Error("Không có thiết lập hợp lệ");
      const u = await api.updateProject(project.id, fields);
      setS((p) => ({
        style: u.style ?? p.style, script_lang: u.script_lang ?? p.script_lang,
        image_text_lang: u.image_text_lang ?? p.image_text_lang, culture_hint: u.culture_hint ?? p.culture_hint,
        prompt_header: u.prompt_header ?? p.prompt_header, prompt_footer: u.prompt_footer ?? p.prompt_footer,
        image_model: u.image_model ?? p.image_model, aspect_ratio: u.aspect_ratio ?? p.aspect_ratio,
        video_model: u.video_model ?? p.video_model,
      }));
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

      // Nhạc nền đi kèm preset: chép file của dự án nguồn sang dự án này. Bỏ qua nếu preset
      // không có nhạc, hoặc dự án này đã dùng đúng file đó rồi. Lỗi ở đây KHÔNG được làm hỏng
      // cả lượt áp dụng — các thiết lập khác đã lưu xong.
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
    } finally {
      setBusy(false);
    }
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
    } catch {
      setErr("File JSON không hợp lệ");
    }
  };

  // ── In-app presets (server-side, like the node-graph presets) ──
  const saveAsPreset = async () => {
    const name = window.prompt("Tên preset thiết lập:");
    if (!name?.trim()) return;
    try {
      const r = await api.saveSettingsPreset(name.trim(), collectSettings());
      setPresets(r.presets);
      setMsg(`Đã lưu preset "${name.trim()}".`);
    } catch (e: any) {
      setErr(e.message);
    }
  };
  const deletePreset = async (id: string) => {
    const p = presets.find((x) => x.id === id);
    if (!p || !window.confirm(`Xóa preset "${p.name}"?`)) return;
    try {
      const r = await api.deleteSettingsPreset(id);
      setPresets(r.presets);
      setPresetSel("");
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const bgmName = bgmPath ? bgmPath.replace(/\\/g, "/").split("/").pop() : null;

  return (
    <div className="fixed inset-0 z-[80] flex justify-end bg-black/50" onClick={onClose}>
      <div
        className="flex h-full w-[440px] flex-col bg-neutral-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-neutral-800 px-5 py-3">
          <h2 className="font-semibold">⚙ Cấu hình dự án</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-300">✕</button>
        </div>

        <div className="flex-1 space-y-5 overflow-auto p-5">
          {err && <div className="rounded-lg bg-rose-950/40 px-3 py-2 text-sm text-rose-300">{err}</div>}
          {msg && <div className="rounded-lg bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">{msg}</div>}

          <Field label="Style (luôn được đưa lên đầu mỗi prompt)">
            <input value={s.style} onChange={(e) => set("style", e.target.value)}
              placeholder="vd: chibi ghibli, watercolor" className={inp} />
          </Field>

          <Field label="Ngôn ngữ kịch bản / lời thoại / lời đọc">
            <input value={s.script_lang} onChange={(e) => set("script_lang", e.target.value)}
              placeholder="Tiếng Việt" className={inp} />
            <p className="mt-1 text-xs text-neutral-600">
              Kịch bản, hội thoại, lời đọc (voiceover) và SEO sẽ viết bằng ngôn ngữ này (mặc định
              Tiếng Việt). Áp dụng cho các lần sinh/sửa kịch bản sau.
            </p>
          </Field>

          <Field label="Ngôn ngữ chữ viết/vẽ trong ảnh">
            <input value={s.image_text_lang} onChange={(e) => set("image_text_lang", e.target.value)}
              placeholder="Tiếng Việt" className={inp} />
            <p className="mt-1 text-xs text-neutral-600">
              Mọi chữ/biển/nhãn hiện trong ảnh sẽ viết bằng ngôn ngữ này (mặc định Tiếng Việt). Từ đặc
              thù ngôn ngữ khác (vd thuật ngữ/nhãn hiệu tiếng Anh) được giữ nguyên.
            </p>
          </Field>

          <Field label="Culture hint (tự nhận từ kịch bản — phong cách văn hoá)">
            <textarea value={s.culture_hint} onChange={(e) => set("culture_hint", e.target.value)}
              placeholder="vd: Vietnamese folk tale, traditional Vietnamese architecture, áo dài…"
              className={`${inp} h-20 resize-none`} />
            <p className="mt-1 text-xs text-neutral-600">
              Giữ hình ảnh đúng với gốc câu chuyện (truyện VN ra phong cách VN, truyện Nhật ra Nhật…).
            </p>
          </Field>

          <Field label="Prompt header (chèn vào ĐẦU mỗi prompt ảnh/video)">
            <textarea value={s.prompt_header} onChange={(e) => set("prompt_header", e.target.value)}
              placeholder="vd: always output in Vietnamese" className={`${inp} h-16 resize-none`} />
          </Field>

          <Field label="Prompt footer (chèn vào CUỐI mỗi prompt ảnh/video)">
            <textarea value={s.prompt_footer} onChange={(e) => set("prompt_footer", e.target.value)}
              placeholder="vd: super detailed, aspect ratio 16:9, cinematic lighting, 8k, sharp focus"
              className={`${inp} h-16 resize-none`} />
          </Field>

          <Field label="Image model">
            <select value={s.image_model} onChange={(e) => set("image_model", e.target.value)} className={inp}>
              <option value="">(mặc định)</option>
              {(opts?.image_models || []).map((m: string) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>

          <div className="grid grid-cols-2 gap-3">
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

          <Field label="Model video">
            <select value={s.video_model} onChange={(e) => set("video_model", e.target.value)} className={inp}>
              {(opts?.video_engines || [{ value: "", label: "Veo i2v (mặc định)" }]).map(
                (m: { value: string; label: string }) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
            </select>
            <p className="mt-1 text-xs text-neutral-600">
              Veo i2v dựng video TỪ ảnh frame (model cụ thể tự chọn theo tier + khung hình).
              Omni Flash là r2v — ảnh frame thành ảnh tham chiếu — và cho chọn thẳng độ dài
              clip, nên beat 10s chỉ cần MỘT clip thay vì hai clip Veo 8s nối nhau; motion
              prompt cũng được viết theo mốc thời gian <code>[00:04]</code> để clip có nhiều
              pha chuyển động thay vì một cú máy đơn điệu.
            </p>
            <p className="mt-1 text-xs text-neutral-600">
              ⚠ <b>Watermark</b>: cả hai đều đóng dấu ở góc dưới phải và hiện suốt clip. Omni
              đóng dấu <b>✦ Gemini</b> trắng, to và lùi vào trong khung — rõ hơn nhiều so với
              chữ <b>“Veo”</b> xám nhỏ sát mép của Veo. Bản upscale 1080p còn làm dấu Veo đậm
              hơn bản 720p. Nếu góc dưới phải là vùng quan trọng của khung hình, cân nhắc bố
              cục chừa chỗ hoặc chèn overlay/lower-third của kênh vào đó.
            </p>
          </Field>

          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" checked={storytelling}
              onChange={(e) => setStorytelling(e.target.checked)}
              className="h-4 w-4 accent-indigo-500" />
            Chế độ Storytelling (giọng đọc dẫn dắt, đọc nguyên văn nội dung gốc)
          </label>

          <div>
            <label className="flex items-center gap-2 text-sm text-neutral-300">
              <input type="checkbox" checked={autoHires}
                onChange={(e) => setAutoHires(e.target.checked)}
                className="h-4 w-4 accent-indigo-500" />
              Tự tải ảnh độ phân giải cao{hiresInfo ? ` (${hiresInfo.label})` : " (2K/4K)"}
            </label>
            <p className="mt-1 text-xs text-neutral-600">
              Ảnh Flow trả về chỉ là bản HD. Bật tuỳ chọn này để sau mỗi lần sinh ảnh tải thêm
              bản phóng to — dùng khi <b>dựng video từ ảnh</b> và <b>export DaVinci Resolve</b>.
              Trần độ phân giải theo tier tài khoản: TIER ONE → 2K, TIER TWO → 4K. Ảnh hiển thị
              trong app vẫn là bản HD cho nhẹ.
            </p>
            {hiresInfo && (
              <div className="mt-2 flex items-center gap-2">
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
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm text-neutral-300">
              <input type="checkbox" checked={autoUpVideo}
                onChange={(e) => setAutoUpVideo(e.target.checked)}
                className="h-4 w-4 accent-indigo-500" />
              Tự upscale video{upInfo ? ` (${upInfo.label})` : " (1080p/4K)"}
            </label>
            <p className="mt-1 text-xs text-neutral-600">
              Video render ra cũng chỉ là bản HD. Bật để tự upscale sau mỗi lần render. Trần
              theo tier: TIER ONE → Full HD 1080p, TIER TWO → 4K.{" "}
              <b className="text-amber-500/90">Mỗi video mất ~1 phút</b> (Flow render lại, không
              trả về ngay như ảnh). Đo thực tế: lên 1080p KHÔNG trừ credit; bản 4K (tier TWO)
              chưa kiểm chứng, có thể tốn. Shot ghép từ nhiều clip (chained) không upscale được.
            </p>
            {(upInfo?.choices?.length ?? 0) > 1 && (
              <div className="mt-2 flex items-center gap-2">
                <span className="shrink-0 text-xs text-neutral-500">Mức upscale</span>
                <select value={upscaleRes} onChange={(e) => setUpscaleRes(e.target.value)}
                  title="Tier TWO có thể chọn Full HD thay vì 4K cho file nhẹ và rẻ hơn"
                  className="flex-1 rounded-lg border border-neutral-700 bg-neutral-950 px-2 py-1 text-xs outline-none focus:border-indigo-500">
                  <option value="">Cao nhất tier cho phép</option>
                  {upInfo!.choices.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
            )}
            {upInfo && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-neutral-500">
                  {upInfo.done}/{upInfo.total} video đã có bản {upInfo.label}
                </span>
                {upInfo.missing > 0 && (
                  <button onClick={upscaleMissingVideos} disabled={busy}
                    title="Upscale bù các video đã render trước đó (tốn credit)"
                    className="rounded-lg border border-neutral-700 px-2.5 py-1 text-xs hover:bg-neutral-800 disabled:opacity-40">
                    ⬆ Upscale {upInfo.missing} video
                  </button>
                )}
              </div>
            )}
          </div>

          <Field label="🔒 Seed (khóa để tái lập ảnh giống hệt)">
            <input type="number" min={0} value={seed}
              onChange={(e) => setSeed(Math.max(0, Number(e.target.value) || 0))}
              placeholder="0 = ngẫu nhiên" className={inp} />
            <p className="mt-1 text-xs text-neutral-600">
              Đặt số &gt; 0 để mọi lần tạo ảnh dùng cùng seed → tái tạo giống nhau (cùng prompt/ref).
              0 hoặc trống = ngẫu nhiên. (Tạo nhiều mẫu 🎲 vẫn random để có lựa chọn.)
            </p>
          </Field>

          <Field label="🎙 Giọng đọc (lồng tiếng dự án)">
            <div className="flex gap-2">
              <select
                value={voiceId}
                onChange={(e) => setVoiceId(Number(e.target.value))}
                className={inp}
              >
                <option value={0}>Mặc định (id 0)</option>
                {voices.map((v) => (
                  <option key={v.voice_id} value={v.voice_id}>
                    {v.title} (id {v.voice_id})
                  </option>
                ))}
              </select>
              <button
                onClick={testVoice}
                disabled={testing}
                title="Nghe thử giọng đã chọn"
                className="shrink-0 rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-40"
              >
                {testing ? "…" : "▶ Test"}
              </button>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs text-neutral-500">Tốc độ đọc</span>
              <input type="range" min={0.5} max={1.5} step={0.05} value={ttsSpeed}
                onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500" />
              <span className="w-10 text-right text-xs tabular-nums text-neutral-400">
                {ttsSpeed.toFixed(2)}×
              </span>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs text-neutral-500">Nghỉ giữa đoạn</span>
              <input type="range" min={0} max={2} step={0.05} value={ttsGap}
                onChange={(e) => setTtsGap(parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500" />
              <span className="w-10 text-right text-xs tabular-nums text-neutral-400">
                {ttsGap.toFixed(2)}s
              </span>
            </div>
            <p className="mt-1 text-xs text-neutral-600">
              Scene được đọc LIỀN MẠCH theo từng đoạn (tách ở dòng trống); đây là khoảng lặng
              chèn GIỮA CÁC ĐOẠN. Đặt ≈1.0s nếu dùng cross-dissolve để hiệu ứng nằm trọn trong
              khoảng lặng. Cần "Dựng theo lời đọc" (hoặc "Dựng lại audio") lại.
            </p>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs text-neutral-500">Nghỉ cuối câu</span>
              <input type="range" min={0} max={1.5} step={0.05} value={ttsSentenceGap}
                onChange={(e) => setTtsSentenceGap(parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500" />
              <span className="w-10 text-right text-xs tabular-nums text-neutral-400">
                {ttsSentenceGap.toFixed(2)}s
              </span>
            </div>
            <p className="mt-1 text-xs text-neutral-600">
              Khoảng lặng chèn thêm sau mỗi câu (dấu . ! ? … ; : —) để OmniVoice không đọc dồn
              quá nhanh. Dùng WhisperX canh mốc nên chỉ chèn ĐÚNG cuối câu, không cắt giữa câu.
              Cần "Dựng theo lời đọc" (hoặc "Dựng lại audio") lại.
            </p>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs text-neutral-500">Đệm 2 đầu</span>
              <input type="range" min={0} max={2} step={0.05} value={ttsEdgePad}
                onChange={(e) => setTtsEdgePad(parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500" />
              <span className="w-10 text-right text-xs tabular-nums text-neutral-400">
                {ttsEdgePad.toFixed(2)}s
              </span>
            </div>
            <p className="mt-1 text-xs text-neutral-600">
              Khoảng lặng đệm ở ĐẦU và CUỐI mỗi WAV scene, làm "tay cầm" cho cross-dissolve
              khi dựng (DaVinci…) — hiệu ứng nằm trọn trong khoảng lặng, không nuốt lời đọc
              đầu/cuối. ≈0.5s phủ một dissolve 24 frame. Cần "Dựng theo lời đọc" lại.
            </p>
            <p className="mt-1 text-xs text-neutral-600">
              Quản lý / thêm giọng trong ⚙ Settings. Cần đặt OmniVoice URL để test.
            </p>
            <audio ref={audioRef} className="hidden" />
          </Field>

          <Field label="🎵 Nhạc nền (tự trộn dưới giọng đọc khi ghép video)">
            {bgmName ? (
              <div className="flex items-center justify-between rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm">
                <span className="truncate text-neutral-200">🎵 {bgmName}</span>
                <div className="ml-2 flex shrink-0 gap-3">
                  <button onClick={() => setShowMusicManager(true)} disabled={busy}
                    className="text-indigo-400 hover:text-indigo-300 disabled:opacity-40">
                    Đổi bài
                  </button>
                  <button onClick={removeBgm} disabled={busy}
                    className="text-rose-400 hover:text-rose-300 disabled:opacity-40">
                    Gỡ
                  </button>
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
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs text-neutral-500">Âm lượng nhạc</span>
              <input type="range" min={0} max={0.6} step={0.02} value={bgmVol}
                onChange={(e) => setBgmVol(parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500" />
              <span className="w-10 text-right text-xs tabular-nums text-neutral-400">
                {Math.round(bgmVol * 100)}%
              </span>
            </div>
            <label className="mt-2 flex items-center gap-2 text-sm text-neutral-300">
              <input type="checkbox" checked={bgmDuck}
                onChange={(e) => setBgmDuck(e.target.checked)}
                className="h-4 w-4 accent-indigo-500" />
              Tự giảm nhạc khi có giọng đọc (ducking)
            </label>
            <p className="mt-1 text-xs text-neutral-600">
              Giọng đọc giữ nguyên âm lượng. Bật ducking: nhạc tự nhỏ lại lúc đang đọc và to lên ở
              khoảng lặng. Tắt: nhạc giữ mức cố định ở trên. Bỏ trống file → không chèn nhạc.
            </p>
          </Field>
        </div>

        <div className="space-y-2 border-t border-neutral-800 p-4">
          <div className="flex gap-2">
            <select
              value={presetSel}
              onChange={(e) => {
                setPresetSel(e.target.value);
                const p = presets.find((x) => x.id === e.target.value);
                if (p) applySettings(p.settings, `preset "${p.name}"`);
              }}
              title="Nạp một preset thiết lập đã lưu (áp dụng ngay)"
              className="min-w-0 flex-1 rounded-lg border border-neutral-700 bg-neutral-950 px-2 py-1.5 text-sm text-neutral-300 outline-none"
            >
              <option value="">Preset thiết lập…</option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            {presetSel && (
              <button onClick={() => deletePreset(presetSel)} title="Xóa preset đang chọn"
                className="rounded-lg border border-neutral-700 px-2.5 py-1.5 text-sm text-rose-300 hover:bg-rose-950/40">
                🗑
              </button>
            )}
            <button onClick={saveAsPreset} title="Lưu thiết lập hiện tại thành preset trong app"
              className="rounded-lg border border-neutral-700 px-2.5 py-1.5 text-sm hover:bg-neutral-800">
              💾 Preset
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={exportSettings}
              title="Tải các THIẾT LẬP của dự án (style, prompt header/footer, model, TTS, BGM volume…) thành .json để tái dùng cho dự án khác"
              className="flex-1 rounded-lg border border-neutral-700 py-2 text-center text-sm text-neutral-300 hover:bg-neutral-800"
            >
              ⤓ Xuất thiết lập
            </button>
            <label
              title="Nạp thiết lập từ file .json và áp dụng ngay cho dự án này (không đụng tới nội dung/kịch bản/ảnh)"
              className="flex-1 cursor-pointer rounded-lg border border-neutral-700 py-2 text-center text-sm text-neutral-300 hover:bg-neutral-800"
            >
              ⤒ Nhập thiết lập
              <input type="file" accept="application/json,.json" className="hidden" disabled={busy}
                onChange={(e) => { importSettings(e.target.files?.[0]); e.target.value = ""; }} />
            </label>
          </div>
          <a
            href={projectExportUrl(project.id)}
            download
            className="block rounded-lg border border-neutral-700 py-2 text-center text-sm text-neutral-300 hover:bg-neutral-800"
            title="Tải dự án (rows DB + media) thành .zip để sao lưu / chuyển máy"
          >
            ⬇ Xuất dự án (.zip)
          </a>
          <button onClick={save} disabled={busy}
            className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40">
            {busy ? "Đang lưu…" : "Lưu cấu hình dự án"}
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

const inp = "w-full rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs text-neutral-400">{label}</label>
      {children}
    </div>
  );
}
