import { useEffect, useMemo, useState } from "react";
import { Activity, Bot, PlayCircle, RefreshCw } from "lucide-react";
import Modal from "../ui/Modal";
import ActionButton from "../ui/ActionButton";
import { fetchAPI } from "../../api/client";
import { normalizeOrientation } from "../../lib/orientation";

interface Props {
  projectId: string;
  videoId: string;
  orientation: string;
  onClose: () => void;
}

interface WorkflowStatus {
  project: { id: string; name: string; status: string; material: string };
  video: { id: string; title: string; orientation: string };
  counts: {
    refs_done: number;
    refs_total: number;
    images_done: number;
    images_total: number;
    videos_done: number;
    videos_total: number;
    upscales_done: number;
    upscales_total: number;
    tts_done?: number;
    tts_total?: number;
    downloads_done?: number;
    downloads_total?: number;
  };
  queue: { pending: number; processing: number; failed: number };
  characters: Array<{
    id: string;
    name: string;
    media_id: string | null;
    ready: boolean;
  }>;
  scenes: Array<{
    id: string;
    display_order: number;
    narrator_text: string | null;
    image_status: string;
    video_status: string;
    upscale_status: string;
  }>;
  suggested_next_action: string;
}

interface SmartContinueResult {
  project_id: string;
  video_id: string;
  orientation: string;
  action: string;
  message: string;
  queued_requests: number;
  requested_types: string[];
  review?: {
    mode: string;
    threshold: number;
    overall_score: number;
    failed_count: number;
    failed_scene_ids: string[];
  };
  downloaded?: {
    downloaded: number;
    skipped: number;
    failed: number;
  };
  concat_output?: string | null;
}

interface VoiceTemplate {
  name: string;
  audio_path: string;
  duration?: number;
}

function StageBar({
  label,
  done,
  total,
}: {
  label: string;
  done: number;
  total: number;
}) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span style={{ color: "var(--muted)", width: 72 }}>{label}</span>
      <div
        className="flex-1 h-2 rounded-full overflow-hidden"
        style={{ background: "var(--border)" }}
      >
        <div
          className="h-full"
          style={{
            width: `${pct}%`,
            background: pct >= 100 ? "var(--green)" : "var(--accent)",
          }}
        />
      </div>
      <span style={{ color: "var(--text)", width: 56, textAlign: "right" }}>
        {done}/{total}
      </span>
    </div>
  );
}

export default function PipelineOrchestratorModal({
  projectId,
  videoId,
  orientation,
  onClose,
}: Props) {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [templates, setTemplates] = useState<VoiceTemplate[]>([]);
  const [ttsTemplate, setTtsTemplate] = useState("");

  const [autoPoll, setAutoPoll] = useState(true);
  const [intervalSec, setIntervalSec] = useState(10);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState("");

  const [includeUpscale, setIncludeUpscale] = useState(true);
  const [includeTTS, setIncludeTTS] = useState(false);
  const [includeConcat, setIncludeConcat] = useState(false);
  const [autoDownloadUpscales, setAutoDownloadUpscales] = useState(false);
  const [fitNarrator, setFitNarrator] = useState(true);
  const [narratorBuffer, setNarratorBuffer] = useState("0.5");
  const [reviewBeforeUpscale, setReviewBeforeUpscale] = useState(true);
  const [reviewMode, setReviewMode] = useState<"light" | "deep">("light");
  const [reviewThreshold, setReviewThreshold] = useState("7.5");
  const [maxReviewRegens, setMaxReviewRegens] = useState("12");

  const ori = normalizeOrientation(orientation);

  const addLog = (line: string) => {
    setLogs((prev) =>
      [`${new Date().toLocaleTimeString()} · ${line}`, ...prev].slice(0, 80),
    );
  };

  const load = async () => {
    const [s, tpls] = await Promise.all([
      fetchAPI<WorkflowStatus>(
        `/api/workflows/status?project_id=${projectId}&video_id=${videoId}`,
      ),
      fetchAPI<VoiceTemplate[]>("/api/tts/templates").catch(() => []),
    ]);
    setStatus(s);
    setTemplates(tpls);
    if (!ttsTemplate && tpls[0]) setTtsTemplate(tpls[0].name);
  };

  useEffect(() => {
    load().catch(() => {});
  }, [projectId, videoId]);

  useEffect(() => {
    if (!autoPoll) return;
    const ms = Math.max(3000, Math.min(60000, intervalSec * 1000));
    const timer = setInterval(() => {
      load().catch(() => {});
    }, ms);
    return () => clearInterval(timer);
  }, [autoPoll, intervalSec, projectId, videoId]);

  const queueStage = async (
    stage: "refs" | "images" | "videos" | "upscale",
  ) => {
    if (!status) return;
    const requests: any[] = [];

    if (stage === "refs") {
      status.characters
        .filter((c) => !c.ready)
        .forEach((c) =>
          requests.push({
            type: "GENERATE_CHARACTER_IMAGE",
            project_id: projectId,
            character_id: c.id,
            orientation: ori,
          }),
        );
    }

    if (stage === "images") {
      status.scenes
        .filter((s) => s.image_status !== "COMPLETED")
        .forEach((s) =>
          requests.push({
            type: "GENERATE_IMAGE",
            project_id: projectId,
            video_id: videoId,
            scene_id: s.id,
            orientation: ori,
          }),
        );
    }

    if (stage === "videos") {
      status.scenes
        .filter(
          (s) =>
            s.video_status !== "COMPLETED" &&
            s.image_status === "COMPLETED",
        )
        .forEach((s) =>
          requests.push({
            type: "GENERATE_VIDEO",
            project_id: projectId,
            video_id: videoId,
            scene_id: s.id,
            orientation: ori,
          }),
        );
    }

    if (stage === "upscale") {
      status.scenes
        .filter((s) => s.upscale_status !== "COMPLETED")
        .forEach((s) =>
          requests.push({
            type: "UPSCALE_VIDEO_LOCAL",
            project_id: projectId,
            video_id: videoId,
            scene_id: s.id,
            orientation: ori,
          }),
        );
    }

    if (requests.length === 0) {
      if (
        stage === "videos" &&
        status.scenes.some(
          (s) => s.video_status !== "COMPLETED" && s.image_status !== "COMPLETED",
        )
      ) {
        addLog(
          "Chưa có scene nào đủ điều kiện gen video (cần image_status=COMPLETED).",
        );
      } else {
        addLog(`Không có tác vụ chờ ở bước ${stage}`);
      }
      return;
    }

    await fetchAPI("/api/requests/batch", {
      method: "POST",
      body: JSON.stringify({ requests }),
    });
    addLog(`Đã xếp hàng ${requests.length} request cho bước ${stage}`);
    await load();
  };

  const runPreflightSmart = async (): Promise<{
    ok: boolean;
    reason?: string;
  }> => {
    if (!status) {
      return {
        ok: false,
        reason: "Chưa có dữ liệu trạng thái workflow để chạy Smart Continue",
      };
    }

    const health = await fetchAPI<{ extension_connected?: boolean }>(
      "/health",
    ).catch(() => ({ extension_connected: false }));
    if (!health.extension_connected) {
      return {
        ok: false,
        reason:
          "Extension chưa kết nối. Mở Google Flow và kết nối extension trước khi chạy Smart Continue.",
      };
    }

    if ((status.scenes?.length ?? 0) === 0) {
      return {
        ok: false,
        reason:
          "Video chưa có scene nào. Hãy thêm scene trước khi chạy Smart Continue.",
      };
    }

    if (
      includeUpscale &&
      (status.counts.videos_total ?? 0) > 0 &&
      (status.counts.videos_done ?? 0) === 0
    ) {
      addLog(
        "Cảnh báo preflight: chưa có video COMPLETED, Smart Continue sẽ ưu tiên queue bước video trước upscale.",
      );
    }

    if (includeTTS && !ttsTemplate) {
      addLog(
        "Cảnh báo preflight: chưa chọn template TTS, Smart Continue sẽ dùng cấu hình mặc định.",
      );
    }

    return { ok: true };
  };

  const runSmart = async () => {
    if (!status) return;
    setRunning(true);
    setError("");
    try {
      const preflight = await runPreflightSmart();
      if (!preflight.ok) {
        const reason = preflight.reason ?? "Preflight thất bại";
        setError(reason);
        addLog(`Preflight chặn chạy: ${reason}`);
        return;
      }

      const res = await fetchAPI<SmartContinueResult>(
        `/api/workflows/videos/${videoId}/smart-continue`,
        {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId,
            orientation: ori,
            include_upscale: includeUpscale,
            include_tts: includeTTS,
            include_concat: includeConcat,
            auto_download_upscales: autoDownloadUpscales,
            fit_narrator: fitNarrator,
            narrator_buffer: Number(narratorBuffer || "0.5"),
            tts_template: includeTTS && ttsTemplate ? ttsTemplate : null,
            review_before_upscale: reviewBeforeUpscale,
            review_mode: reviewMode,
            review_threshold: Number(reviewThreshold || "7.5"),
            max_review_regens: Math.max(1, Number(maxReviewRegens || "12")),
          }),
        },
      );

      addLog(`[${res.action}] ${res.message}`);
      if ((res.queued_requests ?? 0) > 0) {
        addLog(
          `Đã xếp hàng: ${res.queued_requests} request · ${(res.requested_types ?? []).join(", ")}`,
        );
      } else if ((res.requested_types ?? []).length > 0) {
        addLog(`Đã kích hoạt: ${(res.requested_types ?? []).join(", ")}`);
      }
      if (res.review) {
        addLog(
          `Review ${res.review.mode}: score=${res.review.overall_score.toFixed(2)} failed=${res.review.failed_count}`,
        );
      }
      if (res.downloaded) {
        addLog(
          `Tải xuống: +${res.downloaded.downloaded} / bỏ qua ${res.downloaded.skipped} / lỗi ${res.downloaded.failed}`,
        );
      }
      if (res.concat_output) {
        addLog(`File concat: ${res.concat_output}`);
      }
    } catch (e: any) {
      const msg = e.message ?? "Smart pipeline thất bại";
      setError(msg);
      addLog(`Lỗi: ${msg}`);
    } finally {
      setRunning(false);
      load().catch(() => {});
    }
  };

  const counts = status?.counts;

  return (
    <Modal
      title="Pipeline Thông Minh (fk:pipeline + fk:monitor + fk:status)"
      onClose={onClose}
      width={760}
    >
      <div className="flex flex-col gap-4">
        <div
          className="flex items-center gap-2 text-xs"
          style={{ color: "var(--muted)" }}
        >
          <Activity size={12} />
          Orchestrator tự phát hiện bước còn thiếu và xếp hàng batch phù hợp.
        </div>

        {status && (
          <div
            className="rounded p-3 flex flex-col gap-2"
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
            }}
          >
            <div
              className="text-xs font-semibold"
              style={{ color: "var(--text)" }}
            >
              {status.project.name} · {status.video.title} ·{" "}
              {status.video.orientation}
            </div>
            <StageBar
              label="Ref"
              done={counts?.refs_done ?? 0}
              total={counts?.refs_total ?? 0}
            />
            <StageBar
              label="Ảnh"
              done={counts?.images_done ?? 0}
              total={counts?.images_total ?? 0}
            />
            <StageBar
              label="Video"
              done={counts?.videos_done ?? 0}
              total={counts?.videos_total ?? 0}
            />
            <StageBar
              label="Upscale"
              done={counts?.upscales_done ?? 0}
              total={counts?.upscales_total ?? 0}
            />
            {typeof counts?.tts_total === "number" && (
              <StageBar
                label="TTS"
                done={counts?.tts_done ?? 0}
                total={counts?.tts_total ?? 0}
              />
            )}
            {typeof counts?.downloads_total === "number" && (
              <StageBar
                label="4K DL"
                done={counts?.downloads_done ?? 0}
                total={counts?.downloads_total ?? 0}
              />
            )}
            <div
              className="text-xs flex items-center gap-3"
              style={{ color: "var(--muted)" }}
            >
              <span>Hàng đợi: {status.queue.pending} chờ</span>
              <span>{status.queue.processing} đang xử lý</span>
              <span>{status.queue.failed} lỗi</span>
              <span>
                Gợi ý:{" "}
                <strong style={{ color: "var(--text)" }}>
                  {status.suggested_next_action}
                </strong>
              </span>
            </div>
          </div>
        )}

        <div
          className="rounded p-3 flex flex-col gap-2"
          style={{
            background: "var(--card)",
            border: "1px solid var(--border)",
          }}
        >
          <div
            className="text-xs font-semibold"
            style={{ color: "var(--muted)" }}
          >
            Các Bước / Tuỳ Chọn
          </div>
          <div
            className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs"
            style={{ color: "var(--text)" }}
          >
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeUpscale}
                onChange={(e) => setIncludeUpscale(e.target.checked)}
              />{" "}
              Gồm bước upscale
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeTTS}
                onChange={(e) => setIncludeTTS(e.target.checked)}
              />{" "}
              Gồm bước TTS
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeConcat}
                onChange={(e) => setIncludeConcat(e.target.checked)}
              />{" "}
              Tự concat khi sẵn sàng
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoDownloadUpscales}
                onChange={(e) => setAutoDownloadUpscales(e.target.checked)}
              />{" "}
              Tự tải file upscale
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={reviewBeforeUpscale}
                onChange={(e) => setReviewBeforeUpscale(e.target.checked)}
              />{" "}
              Review trước upscale
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={fitNarrator}
                onChange={(e) => setFitNarrator(e.target.checked)}
              />{" "}
              Concat khớp độ dài narrator
            </label>
          </div>

          {reviewBeforeUpscale && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <select
                className="input"
                value={reviewMode}
                onChange={(e) =>
                  setReviewMode((e.target.value as "light" | "deep") || "light")
                }
              >
                <option value="light">Chế độ review: nhẹ</option>
                <option value="deep">Chế độ review: sâu</option>
              </select>
              <input
                className="input"
                value={reviewThreshold}
                onChange={(e) => setReviewThreshold(e.target.value)}
                placeholder="Ngưỡng review (mặc định 7.5)"
              />
              <input
                className="input"
                value={maxReviewRegens}
                onChange={(e) => setMaxReviewRegens(e.target.value)}
                placeholder="Số cảnh regen tối đa mỗi vòng"
              />
            </div>
          )}

          {includeTTS && (
            <select
              className="input"
              value={ttsTemplate}
              onChange={(e) => setTtsTemplate(e.target.value)}
            >
              <option value="">Chọn mẫu TTS...</option>
              {templates.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>
          )}

          {includeConcat && fitNarrator && (
            <input
              className="input"
              value={narratorBuffer}
              onChange={(e) => setNarratorBuffer(e.target.value)}
              placeholder="Đệm narrator (giây, ví dụ 0.5)"
            />
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            <ActionButton
              variant="ghost"
              size="sm"
              onClick={() => queueStage("refs")}
            >
              Xếp hàng ref
            </ActionButton>
            <ActionButton
              variant="ghost"
              size="sm"
              onClick={() => queueStage("images")}
            >
              Xếp hàng ảnh
            </ActionButton>
            <ActionButton
              variant="ghost"
              size="sm"
              onClick={() => queueStage("videos")}
            >
              Xếp hàng video
            </ActionButton>
            <ActionButton
              variant="ghost"
              size="sm"
              onClick={() => queueStage("upscale")}
            >
              Xếp hàng upscale
            </ActionButton>
            <ActionButton
              variant="ghost"
              size="sm"
              onClick={async () => {
                try {
                  const dl = await fetchAPI<{
                    downloaded: string[];
                    failed: string[];
                    skipped: string[];
                  }>(
                    "/api/workflows/videos/" + videoId + "/download-upscales",
                    {
                      method: "POST",
                      body: JSON.stringify({
                        project_id: projectId,
                        orientation: ori,
                      }),
                    },
                  );
                  addLog(
                    `Tải upscale: ${dl.downloaded.length}, lỗi: ${dl.failed.length}, bỏ qua: ${dl.skipped.length}`,
                  );
                } catch (e: any) {
                  const msg = e.message ?? "Tải upscale thất bại";
                  setError(msg);
                  addLog(`Lỗi: ${msg}`);
                }
              }}
            >
              Tải 4K
            </ActionButton>
          </div>
        </div>

        <div
          className="rounded p-3 flex flex-col gap-2"
          style={{
            background: "var(--card)",
            border: "1px solid var(--border)",
          }}
        >
          <div
            className="flex items-center gap-2 text-xs"
            style={{ color: "var(--muted)" }}
          >
            <Bot size={12} /> Theo dõi
            <label className="inline-flex items-center gap-1">
              <input
                type="checkbox"
                checked={autoPoll}
                onChange={(e) => setAutoPoll(e.target.checked)}
              />{" "}
              tự làm mới
            </label>
            <input
              className="input"
              style={{
                width: 90,
                minHeight: 28,
                paddingTop: 4,
                paddingBottom: 4,
              }}
              value={intervalSec}
              onChange={(e) => setIntervalSec(Number(e.target.value) || 10)}
            />
            <span>s</span>
            <ActionButton
              variant="ghost"
              size="sm"
              onClick={() => load().catch(() => {})}
            >
              <RefreshCw size={11} /> Tải lại
            </ActionButton>
          </div>
          <div
            className="max-h-[160px] overflow-y-auto text-xs"
            style={{ color: "var(--text)", fontFamily: "monospace" }}
          >
            {logs.length === 0 ? (
              <div style={{ color: "var(--muted)" }}>Chưa có log</div>
            ) : (
              logs.map((line, idx) => <div key={idx}>{line}</div>)
            )}
          </div>
        </div>

        {error && (
          <div
            className="text-xs p-2 rounded"
            style={{ background: "rgba(239,68,68,0.1)", color: "var(--red)" }}
          >
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <ActionButton variant="ghost" onClick={onClose}>
            Đóng
          </ActionButton>
          <ActionButton
            variant="primary"
            onClick={runSmart}
            disabled={running || !status}
          >
            <PlayCircle size={12} />{" "}
            {running ? "Đang chạy..." : "Chạy Smart Continue"}
          </ActionButton>
        </div>
      </div>
    </Modal>
  );
}
