import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Clapperboard,
  Download,
  Play,
  RefreshCw,
  Trash2,
  Upload,
  Video,
} from "lucide-react";
import { fetchAPI } from "../api/client";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";

interface MaterialOption {
  id: string;
  name: string;
}

interface ManualContextResponse {
  project_id: string;
  user_paygate_tier: string;
}

interface UploadResponse {
  media_id?: string;
  url?: string | null;
}

interface ManualVideoResultItem {
  index: number;
  status: "SUBMITTED" | "COMPLETED" | "FAILED";
  error: string | null;
  media_id: string | null;
  url: string | null;
  operations: Array<Record<string, unknown>>;
  start_image_media_id: string;
  end_image_media_id?: string | null;
}

interface ManualVideoBatchResponse {
  project_id: string;
  user_paygate_tier: string;
  items: ManualVideoResultItem[];
}

interface ModelsPayload {
  video_models?: Record<string, Record<string, Record<string, string>>>;
}

interface VideoModelOption {
  value: string;
  label: string;
}

interface CheckStatusResponse {
  operations?: Array<Record<string, unknown>>;
}

type RowStatus =
  | "IDLE"
  | "UPLOADING"
  | "SUBMITTED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";
type GenerationMode =
  | "frame_2_video"
  | "start_end_frame_2_video"
  | "reference_frame_2_video";

interface VideoRow {
  id: string;
  prompt: string;
  style: string;
  generationMode: GenerationMode;
  aspectRatio: string;
  startMediaId: string;
  startFilePath: string;
  endMediaId: string;
  endFilePath: string;
  referenceMediaId1: string;
  referenceFilePath1: string;
  referenceMediaId2: string;
  referenceFilePath2: string;
  operations: Array<Record<string, unknown>>;
  status: RowStatus;
  mediaId: string | null;
  url: string | null;
  error: string | null;
}

const MATERIAL_NONE = "__none__";
const VIDEO_ASPECT_OPTIONS = [
  { value: "VIDEO_ASPECT_RATIO_PORTRAIT", label: "9:16 — Dọc" },
  { value: "VIDEO_ASPECT_RATIO_LANDSCAPE", label: "16:9 — Ngang" },
];

const GENERATION_MODE_OPTIONS: Array<{
  value: GenerationMode;
  label: string;
  description: string;
}> = [
  {
    value: "frame_2_video",
    label: "Ảnh sang video",
    description: "Dùng 1 ảnh đầu (start image)",
  },
  {
    value: "start_end_frame_2_video",
    label: "Khung đầu + khung cuối",
    description: "Dùng ảnh đầu và ảnh cuối để điều hướng chuyển động",
  },
  {
    value: "reference_frame_2_video",
    label: "Ảnh tham chiếu",
    description: "Dùng 1-2 ảnh tham chiếu để sinh video r2v",
  },
];

const QUICK_PRESETS: Array<{
  id: string;
  label: string;
  mode: GenerationMode;
  prompts: string;
  style?: string;
}> = [
  {
    id: "fast-test",
    label: "Fast Test",
    mode: "frame_2_video",
    prompts:
      "0-3s: camera push-in nhẹ vào chủ thể. 3-6s: giữ khung ổn định, tăng chi tiết chuyển động nhỏ. 6-8s: dừng camera, kết thúc mượt.",
  },
  {
    id: "doc-chain",
    label: "Documentary Chain",
    mode: "start_end_frame_2_video",
    prompts:
      "0-3s: pan chậm bối cảnh tổng quan. 3-6s: chuyển focus vào nhân vật chính. 6-8s: giữ khung kết nối sang cảnh kế tiếp.",
    style: "cinematic documentary tone, natural motion, grounded camera",
  },
  {
    id: "ref-heavy",
    label: "Reference-heavy",
    mode: "reference_frame_2_video",
    prompts:
      "0-3s: camera follow nhẹ theo subject. 3-6s: giữ consistency ngoại hình và trang phục. 6-8s: kết cảnh bằng framing ổn định.",
    style:
      "strict visual consistency, reference-driven composition, realistic motion",
  },
];

function endpointByMode(mode: GenerationMode) {
  if (mode === "reference_frame_2_video")
    return "/api/flow/generate-video-refs";
  return "/api/flow/manual/videos";
}

function getModeValidationError(
  mode: GenerationMode,
  startProvided: boolean,
  endProvided: boolean,
): string | null {
  if (mode === "frame_2_video") {
    if (!startProvided) return "Mode Ảnh sang video cần ảnh đầu (start).";
    return null;
  }
  if (mode === "start_end_frame_2_video") {
    if (!startProvided)
      return "Mode Khung đầu + khung cuối cần ảnh đầu (start).";
    if (!endProvided) return "Mode Khung đầu + khung cuối cần ảnh cuối (end).";
    return null;
  }
  // reference_frame_2_video
  if (!startProvided && !endProvided) {
    return "Mode Ảnh tham chiếu cần ít nhất 1 ảnh tham chiếu (ref 1 hoặc ref 2).";
  }
  return null;
}

function detectVeoName(modelKey: string) {
  const m = /^veo_(\d+)_(\d+)/i.exec(modelKey);
  if (!m) return "Google Veo";
  return `Google Veo ${m[1]}.${m[2]}`;
}

function videoModeLabel(genType: string) {
  if (genType === "frame_2_video") return "Ảnh sang video";
  if (genType === "start_end_frame_2_video") return "Khung đầu + khung cuối";
  if (genType === "reference_frame_2_video") return "Ảnh tham chiếu sang video";
  return genType.replace(/_/g, " ");
}

function aspectLabel(aspect: string) {
  if (aspect.includes("PORTRAIT")) return "9:16";
  if (aspect.includes("LANDSCAPE")) return "16:9";
  return aspect;
}

function speedLabel(modelKey: string) {
  const lower = modelKey.toLowerCase();
  if (lower.includes("ultra_relaxed")) return "Siêu chậm";
  if (lower.includes("relaxed")) return "Thư thả";
  if (lower.includes("fast")) return "Nhanh";
  return "";
}

function buildVideoModelLabel(
  modelKey: string,
  genType: string,
  aspect: string,
) {
  const base = detectVeoName(modelKey);
  const mode = videoModeLabel(genType);
  const asp = aspectLabel(aspect);
  const speed = speedLabel(modelKey);
  return [base, mode, asp, speed].filter(Boolean).join(" • ");
}

function newId() {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createRow(
  prompt = "",
  aspectRatio = VIDEO_ASPECT_OPTIONS[0].value,
  generationMode: GenerationMode = "frame_2_video",
): VideoRow {
  return {
    id: newId(),
    prompt,
    style: "",
    generationMode,
    aspectRatio,
    startMediaId: "",
    startFilePath: "",
    endMediaId: "",
    endFilePath: "",
    referenceMediaId1: "",
    referenceFilePath1: "",
    referenceMediaId2: "",
    referenceFilePath2: "",
    operations: [],
    status: "IDLE",
    mediaId: null,
    url: null,
    error: null,
  };
}

function aspectCss(value: string) {
  if (value.includes("LANDSCAPE") || value.includes("16:9")) return "16 / 9";
  if (value.includes("SQUARE") || value.includes("1:1")) return "1 / 1";
  if (value.includes("4:3")) return "4 / 3";
  return "9 / 16";
}

function safeFileName(name: string) {
  return name.replace(/[^\w.-]+/g, "_");
}

async function downloadFromUrl(url: string, fileName: string) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const blob = await resp.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
    return;
  } catch {
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.target = "_blank";
    a.rel = "noreferrer";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function extractFirstUrl(payload: unknown): string | null {
  if (!payload) return null;
  if (typeof payload === "string") {
    return payload.startsWith("http") ? payload : null;
  }
  if (Array.isArray(payload)) {
    for (const item of payload) {
      const found = extractFirstUrl(item);
      if (found) return found;
    }
    return null;
  }
  if (typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    for (const key of [
      "fifeUrl",
      "servingUri",
      "url",
      "videoUri",
      "imageUri",
    ]) {
      const val = obj[key];
      if (typeof val === "string" && val.startsWith("http")) return val;
    }
    for (const val of Object.values(obj)) {
      const found = extractFirstUrl(val);
      if (found) return found;
    }
  }
  return null;
}

function summarizeOperations(operations: Array<Record<string, unknown>>) {
  if (!operations.length) {
    return {
      done: false,
      failed: false,
      mediaId: null as string | null,
      url: null as string | null,
      error: null as string | null,
    };
  }

  let done = true;
  let failed = false;
  let error: string | null = null;

  for (const op of operations) {
    const status = typeof op.status === "string" ? op.status : "";
    if (status === "MEDIA_GENERATION_STATUS_FAILED") {
      failed = true;
      done = false;
      const fallback =
        typeof (op as any)?.operation?.name === "string"
          ? (op as any).operation.name
          : "Operation failed";
      error = fallback;
      break;
    }
    if (status !== "MEDIA_GENERATION_STATUS_SUCCESSFUL") {
      done = false;
    }
  }

  const firstVideo = (operations[0] as any)?.operation?.metadata?.video ?? null;
  const mediaId =
    typeof firstVideo?.mediaId === "string" ? firstVideo.mediaId : null;
  const url = extractFirstUrl(firstVideo);

  return { done, failed, mediaId, url, error };
}

function explainContextError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e ?? "");
  if (msg.includes("API 404") || msg.includes("Not Found")) {
    return "Agent đang chạy không có endpoint context (khả năng tiến trình cũ). Hãy khởi động lại FlowKit để sidecar thay tiến trình đúng phiên bản.";
  }
  if (msg.includes("Extension not connected")) {
    return 'Google Flow extension chưa kết nối. Mở tab Google Flow trong app rồi bấm "Lấy context" lại.';
  }
  return msg || "Không lấy được Flow context";
}

function StatusBadge({ status }: { status: RowStatus }) {
  if (status === "COMPLETED") return <Badge variant="success">HOÀN TẤT</Badge>;
  if (status === "FAILED") return <Badge variant="destructive">THẤT BẠI</Badge>;
  if (status === "PROCESSING")
    return <Badge variant="warning">ĐANG XỬ LÝ</Badge>;
  if (status === "UPLOADING")
    return <Badge variant="warning">ĐANG UPLOAD</Badge>;
  if (status === "SUBMITTED") return <Badge variant="secondary">ĐÃ GỬI</Badge>;
  return <Badge variant="secondary">CHỜ</Badge>;
}

export default function ManualVideosPage() {
  const [projectId, setProjectId] = useState("");
  const [tier, setTier] = useState("PAYGATE_TIER_ONE");
  const [materials, setMaterials] = useState<MaterialOption[]>([]);
  const [videoModelOptions, setVideoModelOptions] = useState<
    VideoModelOption[]
  >([]);
  const [selectedVideoModel, setSelectedVideoModel] = useState("");
  const [material, setMaterial] = useState(MATERIAL_NONE);
  const [customStyle, setCustomStyle] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [defaultAspectRatio, setDefaultAspectRatio] = useState(
    VIDEO_ASPECT_OPTIONS[0].value,
  );
  const [defaultGenerationMode, setDefaultGenerationMode] =
    useState<GenerationMode>("frame_2_video");
  const [inputMode, setInputMode] = useState<"single" | "multiple">("multiple");
  const [singlePrompt, setSinglePrompt] = useState("");
  const [singleStyle, setSingleStyle] = useState("");
  const [singleGenerationMode, setSingleGenerationMode] =
    useState<GenerationMode>("frame_2_video");
  const [singleAspectRatio, setSingleAspectRatio] = useState(
    VIDEO_ASPECT_OPTIONS[0].value,
  );
  const [singleStartMediaId, setSingleStartMediaId] = useState("");
  const [singleStartFilePath, setSingleStartFilePath] = useState("");
  const [singleEndMediaId, setSingleEndMediaId] = useState("");
  const [singleEndFilePath, setSingleEndFilePath] = useState("");
  const [singleReferenceMediaId1, setSingleReferenceMediaId1] = useState("");
  const [singleReferenceFilePath1, setSingleReferenceFilePath1] = useState("");
  const [singleReferenceMediaId2, setSingleReferenceMediaId2] = useState("");
  const [singleReferenceFilePath2, setSingleReferenceFilePath2] = useState("");
  const [bulkPrompts, setBulkPrompts] = useState("");
  const [rows, setRows] = useState<VideoRow[]>([]);
  const [resolvingContext, setResolvingContext] = useState(false);
  const [runningAll, setRunningAll] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");

  const rowsRef = useRef<VideoRow[]>([]);
  const pollingIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    rowsRef.current = rows;
  }, [rows]);

  const refreshContext = async (
    createIfMissing: boolean,
  ): Promise<ManualContextResponse | null> => {
    setResolvingContext(true);
    try {
      const ctx = await fetchAPI<ManualContextResponse>(
        "/api/flow/manual/context",
        {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId.trim() || undefined,
            create_if_missing: createIfMissing,
          }),
        },
      );
      setProjectId(ctx.project_id ?? "");
      setTier(ctx.user_paygate_tier ?? "PAYGATE_TIER_ONE");
      return ctx;
    } catch (e: any) {
      if (createIfMissing) {
        setError(explainContextError(e));
      }
      return null;
    } finally {
      setResolvingContext(false);
    }
  };

  useEffect(() => {
    fetchAPI<MaterialOption[]>("/api/materials")
      .then((mats) => {
        setMaterials(mats);
        if (mats.length > 0) setMaterial(mats[0].id);
      })
      .catch(() => {});

    fetchAPI<ModelsPayload>("/api/models")
      .then((models) => {
        const seen = new Set<string>();
        const options: VideoModelOption[] = [];
        const videoModels = models.video_models ?? {};
        Object.entries(videoModels).forEach(([, byType]) => {
          Object.entries(byType ?? {}).forEach(([genType, byAspect]) => {
            Object.entries(byAspect ?? {}).forEach(([aspect, modelKey]) => {
              if (!modelKey || seen.has(modelKey)) return;
              seen.add(modelKey);
              options.push({
                value: modelKey,
                label: buildVideoModelLabel(modelKey, genType, aspect),
              });
            });
          });
        });
        setVideoModelOptions(options);
        if (options[0]) {
          setSelectedVideoModel(options[0].value);
        }
      })
      .catch(() => {});

    refreshContext(false).catch(() => {});
  }, []);

  const updateRow = (id: string, patch: Partial<VideoRow>) => {
    setRows((prev) =>
      prev.map((row) => (row.id === id ? { ...row, ...patch } : row)),
    );
  };

  const toggleRowExpanded = (id: string) => {
    setExpandedRows((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const appendBulkRows = () => {
    const prompts = bulkPrompts
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (prompts.length === 0) return;
    setRows((prev) => [
      ...prev,
      ...prompts.map((prompt) =>
        createRow(prompt, defaultAspectRatio, defaultGenerationMode),
      ),
    ]);
    setBulkPrompts("");
  };

  const applyPreset = (presetId: string) => {
    const preset = QUICK_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;
    setDefaultGenerationMode(preset.mode);
    setSingleGenerationMode(preset.mode);
    setBulkPrompts(preset.prompts);
    if (preset.style) {
      setCustomStyle((prev) => (prev.trim() ? prev : (preset.style ?? "")));
    }
  };

  const appendSingleRow = () => {
    const prompt = singlePrompt.trim();
    if (!prompt) return;
    const row = createRow(
      prompt,
      singleAspectRatio || defaultAspectRatio,
      singleGenerationMode,
    );
    row.style = singleStyle.trim();
    if (singleGenerationMode === "reference_frame_2_video") {
      row.referenceMediaId1 = singleReferenceMediaId1.trim();
      row.referenceFilePath1 = singleReferenceFilePath1.trim();
      row.referenceMediaId2 = singleReferenceMediaId2.trim();
      row.referenceFilePath2 = singleReferenceFilePath2.trim();
    } else {
      row.startMediaId = singleStartMediaId.trim();
      row.startFilePath = singleStartFilePath.trim();
      row.endMediaId = singleEndMediaId.trim();
      row.endFilePath = singleEndFilePath.trim();
    }
    setRows((prev) => [...prev, row]);
    setSinglePrompt("");
    setSingleStyle("");
    setSingleStartMediaId("");
    setSingleStartFilePath("");
    setSingleEndMediaId("");
    setSingleEndFilePath("");
    setSingleReferenceMediaId1("");
    setSingleReferenceFilePath1("");
    setSingleReferenceMediaId2("");
    setSingleReferenceFilePath2("");
  };

  const pickLocalImagePath = async (): Promise<string | null> => {
    const picker = window.electron?.pickImageFile;
    if (!picker) {
      alert("Chỉ hỗ trợ chọn file trong ứng dụng desktop Electron.");
      return null;
    }
    return picker();
  };

  const pickImageFile = async (
    rowId: string,
    target: "start" | "end" | "ref1" | "ref2",
  ) => {
    const filePath = await pickLocalImagePath();
    if (!filePath) return;
    if (target === "start") {
      updateRow(rowId, { startFilePath: filePath, status: "IDLE" });
      return;
    }
    if (target === "end") {
      updateRow(rowId, { endFilePath: filePath, status: "IDLE" });
      return;
    }
    if (target === "ref1") {
      updateRow(rowId, { referenceFilePath1: filePath, status: "IDLE" });
      return;
    }
    updateRow(rowId, { referenceFilePath2: filePath, status: "IDLE" });
  };

  const pickSingleImageFile = async (
    target: "start" | "end" | "ref1" | "ref2",
  ) => {
    const filePath = await pickLocalImagePath();
    if (!filePath) return;
    if (target === "start") {
      setSingleStartFilePath(filePath);
      return;
    }
    if (target === "end") {
      setSingleEndFilePath(filePath);
      return;
    }
    if (target === "ref1") {
      setSingleReferenceFilePath1(filePath);
      return;
    }
    setSingleReferenceFilePath2(filePath);
  };

  const uploadLocalImage = async (
    filePath: string,
    resolvedProjectId: string,
  ): Promise<string> => {
    const fileName = filePath.split(/[\\/]/).pop() || "image.png";
    const uploaded = await fetchAPI<UploadResponse>("/api/flow/upload-image", {
      method: "POST",
      body: JSON.stringify({
        file_path: filePath,
        project_id: resolvedProjectId,
        file_name: fileName,
      }),
    });
    if (!uploaded.media_id) {
      throw new Error("Upload thành công nhưng không có media_id");
    }
    return uploaded.media_id;
  };

  const pollRow = async (
    id: string,
    seedOperations?: Array<Record<string, unknown>>,
  ) => {
    if (pollingIdsRef.current.has(id)) return;
    pollingIdsRef.current.add(id);
    if ((seedOperations?.length ?? 0) > 0) {
      updateRow(id, { operations: seedOperations, status: "PROCESSING" });
    }
    try {
      for (let attempt = 0; attempt < 180; attempt += 1) {
        const current = rowsRef.current.find((row) => row.id === id);
        const operationsToCheck =
          (current?.operations?.length ?? 0) > 0
            ? current!.operations
            : (seedOperations ?? []);
        if (!current || operationsToCheck.length === 0) {
          return;
        }

        if (attempt > 0) {
          // eslint-disable-next-line no-await-in-loop
          await sleep(5000);
        }

        const statusData = await fetchAPI<CheckStatusResponse>(
          "/api/flow/check-status",
          {
            method: "POST",
            body: JSON.stringify({ operations: operationsToCheck }),
          },
        );
        const operations = Array.isArray(statusData.operations)
          ? statusData.operations
          : [];
        const summary = summarizeOperations(operations);
        updateRow(id, {
          operations,
          status: summary.failed
            ? "FAILED"
            : summary.done
              ? "COMPLETED"
              : "PROCESSING",
          mediaId: summary.mediaId ?? current.mediaId,
          url: summary.url ?? current.url,
          error: summary.failed
            ? (summary.error ?? "Video generation failed")
            : null,
        });

        if (summary.failed || summary.done) return;
      }

      updateRow(id, {
        status: "FAILED",
        error: "Polling timeout sau 15 phút",
      });
    } catch (e: any) {
      updateRow(id, {
        status: "FAILED",
        error: e.message ?? "Poll trạng thái thất bại",
      });
    } finally {
      pollingIdsRef.current.delete(id);
    }
  };

  const submitRow = async (id: string) => {
    const row = rowsRef.current.find((item) => item.id === id);
    if (!row) return;
    if (!row.prompt.trim()) {
      updateRow(id, { status: "FAILED", error: "Prompt không được để trống" });
      return;
    }

    setError("");
    updateRow(id, { status: "UPLOADING", error: null });
    const ctx = await refreshContext(true);
    if (!ctx) {
      updateRow(id, {
        status: "FAILED",
        error: "Không resolve được Flow project context",
      });
      return;
    }

    try {
      let startMediaId = row.startMediaId.trim();
      let endMediaId = row.endMediaId.trim();
      let referenceMediaId1 = row.referenceMediaId1.trim();
      let referenceMediaId2 = row.referenceMediaId2.trim();

      if (row.generationMode === "reference_frame_2_video") {
        if (!referenceMediaId1 && row.referenceFilePath1.trim()) {
          referenceMediaId1 = await uploadLocalImage(
            row.referenceFilePath1.trim(),
            ctx.project_id,
          );
          updateRow(id, { referenceMediaId1 });
        }
        if (!referenceMediaId2 && row.referenceFilePath2.trim()) {
          referenceMediaId2 = await uploadLocalImage(
            row.referenceFilePath2.trim(),
            ctx.project_id,
          );
          updateRow(id, { referenceMediaId2 });
        }
      } else {
        if (!startMediaId && row.startFilePath.trim()) {
          startMediaId = await uploadLocalImage(
            row.startFilePath.trim(),
            ctx.project_id,
          );
          updateRow(id, { startMediaId });
        }

        if (!endMediaId && row.endFilePath.trim()) {
          endMediaId = await uploadLocalImage(
            row.endFilePath.trim(),
            ctx.project_id,
          );
          updateRow(id, { endMediaId });
        }
      }

      if (row.generationMode === "frame_2_video" && !startMediaId) {
        updateRow(id, {
          status: "FAILED",
          error: "Mode Ảnh sang video cần start media_id hoặc ảnh đầu",
        });
        return;
      }

      if (row.generationMode === "start_end_frame_2_video") {
        if (!startMediaId) {
          updateRow(id, {
            status: "FAILED",
            error:
              "Mode Khung đầu + khung cuối cần start media_id hoặc ảnh đầu",
          });
          return;
        }
        if (!endMediaId) {
          updateRow(id, {
            status: "FAILED",
            error: "Mode Khung đầu + khung cuối cần end media_id hoặc ảnh cuối",
          });
          return;
        }
      }

      if (
        row.generationMode === "reference_frame_2_video" &&
        !referenceMediaId1 &&
        !referenceMediaId2
      ) {
        updateRow(id, {
          status: "FAILED",
          error:
            "Mode Ảnh tham chiếu cần ít nhất 1 ảnh tham chiếu (ref 1 hoặc ref 2)",
        });
        return;
      }

      if (row.generationMode === "reference_frame_2_video") {
        const references = [referenceMediaId1, referenceMediaId2].filter(
          Boolean,
        ) as string[];
        const sceneId = `manual-${row.id}`;
        const direct = await fetchAPI<any>("/api/flow/generate-video-refs", {
          method: "POST",
          body: JSON.stringify({
            reference_media_ids: references,
            prompt: row.prompt,
            project_id: ctx.project_id,
            scene_id: sceneId,
            aspect_ratio: row.aspectRatio || defaultAspectRatio,
            user_paygate_tier: tier,
            video_model_key: selectedVideoModel || null,
          }),
        });

        const operations = Array.isArray(direct?.operations)
          ? direct.operations
          : [];
        const summary = summarizeOperations(operations);
        const nextStatus: RowStatus = summary.failed
          ? "FAILED"
          : summary.done
            ? "COMPLETED"
            : operations.length > 0
              ? "SUBMITTED"
              : "FAILED";

        updateRow(id, {
          status: nextStatus,
          operations,
          mediaId: summary.mediaId,
          url: summary.url,
          error: summary.failed
            ? (summary.error ?? "Reference video generation failed")
            : null,
          referenceMediaId1: referenceMediaId1 || row.referenceMediaId1,
          referenceMediaId2: referenceMediaId2 || row.referenceMediaId2,
        });

        if (nextStatus === "SUBMITTED" && operations.length > 0) {
          void pollRow(id, operations);
        }
      } else {
        const response = await fetchAPI<ManualVideoBatchResponse>(
          "/api/flow/manual/videos",
          {
            method: "POST",
            body: JSON.stringify({
              project_id: ctx.project_id,
              user_paygate_tier: tier,
              material: material === MATERIAL_NONE ? null : material,
              custom_style: customStyle.trim() || null,
              video_model_key: selectedVideoModel || null,
              aspect_ratio: defaultAspectRatio,
              items: [
                {
                  prompt: row.prompt,
                  style: row.style.trim() || null,
                  aspect_ratio: row.aspectRatio || defaultAspectRatio,
                  video_model_key: selectedVideoModel || null,
                  start_image_media_id: startMediaId,
                  end_image_media_id:
                    row.generationMode === "start_end_frame_2_video"
                      ? endMediaId || null
                      : null,
                },
              ],
            }),
          },
        );

        const item = response.items?.[0];
        if (!item) {
          updateRow(id, {
            status: "FAILED",
            error: "Không nhận được kết quả submit",
          });
          return;
        }

        const nextStatus: RowStatus =
          item.status === "FAILED"
            ? "FAILED"
            : item.status === "COMPLETED"
              ? "COMPLETED"
              : "SUBMITTED";

        updateRow(id, {
          status: nextStatus,
          operations: item.operations ?? [],
          mediaId: item.media_id,
          url: item.url,
          error: item.error,
          startMediaId: item.start_image_media_id ?? startMediaId,
          endMediaId: item.end_image_media_id ?? endMediaId,
        });

        if (nextStatus === "SUBMITTED" && (item.operations?.length ?? 0) > 0) {
          void pollRow(id, item.operations ?? []);
        }
      }
    } catch (e: any) {
      updateRow(id, {
        status: "FAILED",
        error: e.message ?? "Submit video thất bại",
      });
    }
  };

  const submitAll = async () => {
    const ids = rows.map((row) => row.id);
    if (ids.length === 0) return;
    setRunningAll(true);
    for (const id of ids) {
      // eslint-disable-next-line no-await-in-loop
      await submitRow(id);
    }
    setRunningAll(false);
  };

  const pollPending = () => {
    rows.forEach((row) => {
      if (
        (row.status === "SUBMITTED" || row.status === "PROCESSING") &&
        row.operations.length > 0
      ) {
        void pollRow(row.id);
      }
    });
  };

  const downloadRowVideo = async (row: VideoRow, index: number) => {
    if (!row.url) return;
    const mediaSlug = row.mediaId
      ? row.mediaId.slice(0, 8)
      : `row_${index + 1}`;
    const fileName = safeFileName(`manual-video-${index + 1}-${mediaSlug}.mp4`);
    await downloadFromUrl(row.url, fileName);
  };

  const downloadAllVideos = async () => {
    const downloadable = rows
      .map((row, index) => ({ row, index }))
      .filter((entry) => entry.row.status === "COMPLETED" && !!entry.row.url);
    if (downloadable.length === 0) return;
    for (const entry of downloadable) {
      // eslint-disable-next-line no-await-in-loop
      await downloadRowVideo(entry.row, entry.index);
      // eslint-disable-next-line no-await-in-loop
      await sleep(120);
    }
  };

  const singleStartProvided = Boolean(
    singleGenerationMode === "reference_frame_2_video"
      ? singleReferenceMediaId1.trim() || singleReferenceFilePath1.trim()
      : singleStartMediaId.trim() || singleStartFilePath.trim(),
  );
  const singleEndProvided = Boolean(
    singleGenerationMode === "reference_frame_2_video"
      ? singleReferenceMediaId2.trim() || singleReferenceFilePath2.trim()
      : singleEndMediaId.trim() || singleEndFilePath.trim(),
  );
  const singleDraftError = getModeValidationError(
    singleGenerationMode,
    singleStartProvided,
    singleEndProvided,
  );
  const singlePrimaryMediaId =
    singleGenerationMode === "reference_frame_2_video"
      ? singleReferenceMediaId1
      : singleStartMediaId;
  const singlePrimaryFilePath =
    singleGenerationMode === "reference_frame_2_video"
      ? singleReferenceFilePath1
      : singleStartFilePath;
  const singleSecondaryMediaId =
    singleGenerationMode === "reference_frame_2_video"
      ? singleReferenceMediaId2
      : singleEndMediaId;
  const singleSecondaryFilePath =
    singleGenerationMode === "reference_frame_2_video"
      ? singleReferenceFilePath2
      : singleEndFilePath;

  return (
    <div className="flex flex-col gap-4 h-full">
      <Card>
        <CardHeader className="pb-1">
          <CardTitle className="flex items-center gap-2">
            <Clapperboard size={14} />
            Tạo Video
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 pt-0 pb-2">
          <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_220px]">
            <div className="flex flex-col gap-1">
              <Label>Flow Project ID</Label>
              <Input
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="Để trống để app tự lấy hoặc tạo project thủ công"
              />
            </div>
            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={() => {
                  refreshContext(true).catch(() => {});
                }}
                disabled={resolvingContext}
                className="w-full"
              >
                <RefreshCw size={12} />
                {resolvingContext ? "Đang lấy context..." : "Lấy context"}
              </Button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Flow sẵn sàng</Badge>
            <Badge variant="secondary">
              {selectedVideoModel || "Model tự động"}
            </Badge>
            <Badge variant="secondary">{tier}</Badge>
            <Badge variant="secondary">Số dòng: {rows.length}</Badge>
          </div>
          {error && (
            <div className="text-xs rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-600">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cấu hình Phong cách & Model</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">
              Chất liệu: {material === MATERIAL_NONE ? "không" : material}
            </Badge>
            <Badge variant="secondary">
              Model: {selectedVideoModel || "tự động"}
            </Badge>
            <Badge variant="secondary">
              Mode:{" "}
              {GENERATION_MODE_OPTIONS.find(
                (m) => m.value === defaultGenerationMode,
              )?.label ?? defaultGenerationMode}
            </Badge>
            <Badge variant="secondary">
              Endpoint: {endpointByMode(defaultGenerationMode)}
            </Badge>
            <Badge variant="secondary">
              Tỉ lệ mặc định:{" "}
              {VIDEO_ASPECT_OPTIONS.find(
                (item) => item.value === defaultAspectRatio,
              )?.label ?? defaultAspectRatio}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdvanced((prev) => !prev)}
              className="ml-auto gap-1.5"
            >
              {showAdvanced ? (
                <ChevronUp size={12} />
              ) : (
                <ChevronDown size={12} />
              )}
              {showAdvanced ? "Ẩn cài đặt nâng cao" : "Hiện cài đặt nâng cao"}
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            {QUICK_PRESETS.map((preset) => (
              <Button
                key={preset.id}
                variant="outline"
                size="sm"
                onClick={() => applyPreset(preset.id)}
              >
                Preset: {preset.label}
              </Button>
            ))}
          </div>

          {showAdvanced && (
            <div className="grid gap-3 md:grid-cols-3 border border-[hsl(var(--border))] rounded-md p-3">
              <div className="flex flex-col gap-1.5">
                <Label>Chất liệu</Label>
                <Select value={material} onValueChange={setMaterial}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={MATERIAL_NONE}>
                      Không áp style material
                    </SelectItem>
                    {materials.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.name} ({item.id})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Model video</Label>
                <Select
                  value={selectedVideoModel}
                  onValueChange={setSelectedVideoModel}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Chọn model video..." />
                  </SelectTrigger>
                  <SelectContent>
                    {videoModelOptions.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Mode tạo video mặc định</Label>
                <Select
                  value={defaultGenerationMode}
                  onValueChange={(v) =>
                    setDefaultGenerationMode(v as GenerationMode)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {GENERATION_MODE_OPTIONS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="text-xs text-[hsl(var(--muted-foreground))]">
                  {
                    GENERATION_MODE_OPTIONS.find(
                      (m) => m.value === defaultGenerationMode,
                    )?.description
                  }
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Aspect mặc định</Label>
                <Select
                  value={defaultAspectRatio}
                  onValueChange={setDefaultAspectRatio}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VIDEO_ASPECT_OPTIONS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5 md:col-span-3">
                <Label>Phong cách tùy chỉnh (tùy chọn)</Label>
                <Textarea
                  value={customStyle}
                  onChange={(e) => setCustomStyle(e.target.value)}
                  rows={2}
                  placeholder="Ví dụ: cinematic documentary tone, smooth camera movement, realistic film grain..."
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nhập Prompt</CardTitle>
          <CardDescription>
            Tách riêng chế độ Đơn và Hàng loạt để nhập nhanh.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Tabs
            value={inputMode}
            onValueChange={(v) => setInputMode(v as "single" | "multiple")}
          >
            <TabsList>
              <TabsTrigger value="single" className="text-sm font-medium">
                Đơn (Single)
              </TabsTrigger>
              <TabsTrigger value="multiple" className="text-sm font-medium">
                Hàng loạt (Multiple)
              </TabsTrigger>
            </TabsList>

            <TabsContent value="single" className="mt-3">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="flex flex-col gap-1.5 md:col-span-2">
                  <Label>Prompt video đơn</Label>
                  <Textarea
                    rows={4}
                    value={singlePrompt}
                    onChange={(e) => setSinglePrompt(e.target.value)}
                    placeholder="0-3s: ... 3-6s: ... 6-8s: ..."
                  />
                </div>
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1.5">
                    <Label>Mode</Label>
                    <Select
                      value={singleGenerationMode}
                      onValueChange={(v) => {
                        const next = v as GenerationMode;
                        setSingleGenerationMode(next);
                        if (next === "frame_2_video") {
                          setSingleEndMediaId("");
                          setSingleEndFilePath("");
                          setSingleReferenceMediaId1("");
                          setSingleReferenceFilePath1("");
                          setSingleReferenceMediaId2("");
                          setSingleReferenceFilePath2("");
                          return;
                        }
                        if (next === "start_end_frame_2_video") {
                          setSingleReferenceMediaId1("");
                          setSingleReferenceFilePath1("");
                          setSingleReferenceMediaId2("");
                          setSingleReferenceFilePath2("");
                          return;
                        }
                        setSingleStartMediaId("");
                        setSingleStartFilePath("");
                        setSingleEndMediaId("");
                        setSingleEndFilePath("");
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {GENERATION_MODE_OPTIONS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>
                            {item.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="text-xs text-[hsl(var(--muted-foreground))]">
                      {
                        GENERATION_MODE_OPTIONS.find(
                          (m) => m.value === singleGenerationMode,
                        )?.description
                      }
                    </div>
                    <div className="text-xs text-[hsl(var(--muted-foreground))]">
                      Endpoint:{" "}
                      <span className="font-mono">
                        {endpointByMode(singleGenerationMode)}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label>Aspect</Label>
                    <Select
                      value={singleAspectRatio}
                      onValueChange={setSingleAspectRatio}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {VIDEO_ASPECT_OPTIONS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>
                            {item.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label>Ghi đè phong cách</Label>
                    <Input
                      value={singleStyle}
                      onChange={(e) => setSingleStyle(e.target.value)}
                      placeholder="tùy chọn"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label>
                    {singleGenerationMode === "reference_frame_2_video"
                      ? "Reference media_id 1 (bắt buộc)"
                      : "Start media_id"}
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      value={singlePrimaryMediaId}
                      onChange={(e) => {
                        if (singleGenerationMode === "reference_frame_2_video") {
                          setSingleReferenceMediaId1(e.target.value);
                          return;
                        }
                        setSingleStartMediaId(e.target.value);
                      }}
                      placeholder={
                        singleGenerationMode === "reference_frame_2_video"
                          ? "UUID media_id ảnh tham chiếu 1"
                          : "UUID media_id ảnh đầu"
                      }
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        void pickSingleImageFile(
                          singleGenerationMode === "reference_frame_2_video"
                            ? "ref1"
                            : "start",
                        );
                      }}
                    >
                      <Upload size={12} />
                      {singleGenerationMode === "reference_frame_2_video"
                        ? "Ref 1"
                        : "Ảnh đầu"}
                    </Button>
                  </div>
                  {singlePrimaryFilePath && (
                    <div className="text-xs text-[hsl(var(--muted-foreground))] break-all">
                      File: {singlePrimaryFilePath}
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label>
                    {singleGenerationMode === "start_end_frame_2_video"
                      ? "End media_id (bắt buộc)"
                      : singleGenerationMode === "reference_frame_2_video"
                        ? "Reference media_id 2 (tùy chọn)"
                        : "End media_id (tùy chọn)"}
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      value={singleSecondaryMediaId}
                      onChange={(e) => {
                        if (singleGenerationMode === "reference_frame_2_video") {
                          setSingleReferenceMediaId2(e.target.value);
                          return;
                        }
                        setSingleEndMediaId(e.target.value);
                      }}
                      disabled={singleGenerationMode === "frame_2_video"}
                      placeholder={
                        singleGenerationMode === "start_end_frame_2_video"
                          ? "UUID media_id ảnh cuối (bắt buộc)"
                          : singleGenerationMode === "reference_frame_2_video"
                            ? "UUID media_id ảnh tham chiếu 2 (tùy chọn)"
                            : "Không dùng ở mode Ảnh sang video"
                      }
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={singleGenerationMode === "frame_2_video"}
                      onClick={() => {
                        void pickSingleImageFile(
                          singleGenerationMode === "reference_frame_2_video"
                            ? "ref2"
                            : "end",
                        );
                      }}
                    >
                      <Upload size={12} />
                      {singleGenerationMode === "reference_frame_2_video"
                        ? "Ref 2"
                        : "Ảnh cuối"}
                    </Button>
                  </div>
                  {singleSecondaryFilePath && (
                    <div className="text-xs text-[hsl(var(--muted-foreground))] break-all">
                      File: {singleSecondaryFilePath}
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-3 flex flex-col gap-2">
                <div className="text-xs text-[hsl(var(--muted-foreground))]">
                  Quy tắc mode:{" "}
                  <span className="font-medium">
                    {singleGenerationMode === "frame_2_video"
                      ? "Cần start image."
                      : singleGenerationMode === "start_end_frame_2_video"
                        ? "Cần start + end image."
                        : "Cần tối thiểu 1 ảnh tham chiếu."}
                  </span>
                </div>

                {singleDraftError && (
                  <div className="text-xs rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700">
                    {singleDraftError}
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={appendSingleRow}
                    disabled={!singlePrompt.trim() || !!singleDraftError}
                  >
                    + Thêm single vào danh sách
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSinglePrompt("");
                      setSingleStyle("");
                      setSingleStartMediaId("");
                      setSingleStartFilePath("");
                      setSingleEndMediaId("");
                      setSingleEndFilePath("");
                      setSingleReferenceMediaId1("");
                      setSingleReferenceFilePath1("");
                      setSingleReferenceMediaId2("");
                      setSingleReferenceFilePath2("");
                    }}
                    disabled={
                      !singlePrompt &&
                      !singleStyle &&
                      !singleStartMediaId &&
                      !singleStartFilePath &&
                      !singleEndMediaId &&
                      !singleEndFilePath &&
                      !singleReferenceMediaId1 &&
                      !singleReferenceFilePath1 &&
                      !singleReferenceMediaId2 &&
                      !singleReferenceFilePath2
                    }
                  >
                    Xóa nội dung single
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="multiple" className="mt-3">
              <Textarea
                rows={5}
                value={bulkPrompts}
                onChange={(e) => setBulkPrompts(e.target.value)}
                placeholder={
                  "Prompt video 1...\nPrompt video 2...\nPrompt video 3..."
                }
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <Button variant="outline" onClick={appendBulkRows}>
                  + Thêm prompt vào danh sách
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    setRows((prev) => [
                      ...prev,
                      createRow("", defaultAspectRatio),
                    ])
                  }
                >
                  + Thêm 1 dòng trống
                </Button>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={submitAll}
              disabled={runningAll || rows.length === 0}
            >
              <Play size={12} />
              {runningAll ? "Đang gửi tất cả..." : "Gửi + Theo dõi tất cả"}
            </Button>
            <Button
              variant="outline"
              onClick={pollPending}
              disabled={rows.length === 0}
            >
              <RefreshCw size={12} />
              Cập nhật trạng thái
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                void downloadAllVideos();
              }}
              disabled={rows.every((row) => !row.url)}
            >
              <Download size={12} />
              Tải tất cả video
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3 overflow-y-auto pr-1">
        {rows.length === 0 && (
          <div className="text-xs text-[hsl(var(--muted-foreground))]">
            Chưa có item nào. Thêm prompt trước, rồi nhập media theo mode
            (start/end hoặc ref1/ref2).
          </div>
        )}

        {rows.map((row, idx) => {
          const usesReferenceInputs =
            row.generationMode === "reference_frame_2_video";
          const rowPrimaryMediaId = usesReferenceInputs
            ? row.referenceMediaId1
            : row.startMediaId;
          const rowPrimaryFilePath = usesReferenceInputs
            ? row.referenceFilePath1
            : row.startFilePath;
          const rowSecondaryMediaId = usesReferenceInputs
            ? row.referenceMediaId2
            : row.endMediaId;
          const rowSecondaryFilePath = usesReferenceInputs
            ? row.referenceFilePath2
            : row.endFilePath;
          const rowValidationError = getModeValidationError(
            row.generationMode,
            Boolean(rowPrimaryMediaId.trim() || rowPrimaryFilePath.trim()),
            Boolean(rowSecondaryMediaId.trim() || rowSecondaryFilePath.trim()),
          );

          return (
            <Card key={row.id}>
            <CardContent className="p-4 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold">#{idx + 1}</span>
                <StatusBadge status={row.status} />
                <span className="text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[50ch]">
                  {row.prompt.trim() || "Chưa có prompt"}
                </span>
                <div className="flex-1" />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleRowExpanded(row.id)}
                  className="gap-1.5"
                >
                  {expandedRows[row.id] ? (
                    <ChevronUp size={12} />
                  ) : (
                    <ChevronDown size={12} />
                  )}
                  {expandedRows[row.id] ? "Thu gọn" : "Chi tiết"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => submitRow(row.id)}
                  disabled={
                    row.status === "UPLOADING" ||
                    !row.prompt.trim() ||
                    !!rowValidationError
                  }
                >
                  <Video size={12} />
                  Tạo video
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    void pollRow(row.id);
                  }}
                  disabled={row.operations.length === 0}
                >
                  Theo dõi
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() =>
                    setRows((prev) => prev.filter((item) => item.id !== row.id))
                  }
                >
                  <Trash2 size={12} />
                </Button>
              </div>

              {expandedRows[row.id] && (
                <>
                  <div className="grid gap-3 md:grid-cols-3 border border-[hsl(var(--border))] rounded-md p-3">
                    <div className="flex flex-col gap-1.5 md:col-span-2">
                      <Label>Prompt</Label>
                      <Textarea
                        value={row.prompt}
                        onChange={(e) =>
                          updateRow(row.id, {
                            prompt: e.target.value,
                            status: "IDLE",
                          })
                        }
                        rows={3}
                        placeholder="0-3s: ... 3-6s: ... 6-8s: ..."
                      />
                    </div>
                    <div className="flex flex-col gap-3">
                      <div className="flex flex-col gap-1.5">
                        <Label>Mode</Label>
                        <Select
                          value={row.generationMode}
                          onValueChange={(value) => {
                            const next = value as GenerationMode;
                            if (next === "frame_2_video") {
                              updateRow(row.id, {
                                generationMode: next,
                                endMediaId: "",
                                endFilePath: "",
                                referenceMediaId1: "",
                                referenceFilePath1: "",
                                referenceMediaId2: "",
                                referenceFilePath2: "",
                                status: "IDLE",
                              });
                              return;
                            }
                            if (next === "start_end_frame_2_video") {
                              updateRow(row.id, {
                                generationMode: next,
                                referenceMediaId1: "",
                                referenceFilePath1: "",
                                referenceMediaId2: "",
                                referenceFilePath2: "",
                                status: "IDLE",
                              });
                              return;
                            }
                            updateRow(row.id, {
                              generationMode: next,
                              startMediaId: "",
                              startFilePath: "",
                              endMediaId: "",
                              endFilePath: "",
                              status: "IDLE",
                            });
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {GENERATION_MODE_OPTIONS.map((item) => (
                              <SelectItem key={item.value} value={item.value}>
                                {item.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <div className="text-xs text-[hsl(var(--muted-foreground))]">
                          {
                            GENERATION_MODE_OPTIONS.find(
                              (m) => m.value === row.generationMode,
                            )?.description
                          }
                        </div>
                        <div className="text-xs text-[hsl(var(--muted-foreground))]">
                          Endpoint:{" "}
                          <span className="font-mono">
                            {endpointByMode(row.generationMode)}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-col gap-1.5">
                        <Label>Aspect</Label>
                        <Select
                          value={row.aspectRatio}
                          onValueChange={(value) =>
                            updateRow(row.id, {
                              aspectRatio: value,
                              status: "IDLE",
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {VIDEO_ASPECT_OPTIONS.map((item) => (
                              <SelectItem key={item.value} value={item.value}>
                                {item.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex flex-col gap-1.5">
                        <Label>Ghi đè phong cách</Label>
                        <Input
                          value={row.style}
                          onChange={(e) =>
                            updateRow(row.id, {
                              style: e.target.value,
                              status: "IDLE",
                            })
                          }
                          placeholder="tùy chọn"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2 border border-[hsl(var(--border))] rounded-md p-3">
                    <div className="flex flex-col gap-1.5">
                      <Label>
                        {row.generationMode === "reference_frame_2_video"
                          ? "Reference media_id 1 (bắt buộc)"
                          : "Start media_id"}
                      </Label>
                      <div className="flex gap-2">
                        <Input
                          value={rowPrimaryMediaId}
                          onChange={(e) =>
                            updateRow(row.id, {
                              ...(usesReferenceInputs
                                ? { referenceMediaId1: e.target.value }
                                : { startMediaId: e.target.value }),
                              status: "IDLE",
                            })
                          }
                          placeholder={
                            row.generationMode === "reference_frame_2_video"
                              ? "UUID media_id ảnh tham chiếu 1"
                              : "UUID media_id ảnh đầu"
                          }
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            void pickImageFile(
                              row.id,
                              usesReferenceInputs ? "ref1" : "start",
                            );
                          }}
                        >
                          <Upload size={12} />
                          {row.generationMode === "reference_frame_2_video"
                            ? "Ref 1"
                            : "Ảnh đầu"}
                        </Button>
                      </div>
                      {rowPrimaryFilePath && (
                        <div className="text-xs text-[hsl(var(--muted-foreground))] break-all">
                          File: {rowPrimaryFilePath}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <Label>
                        {row.generationMode === "start_end_frame_2_video"
                          ? "End media_id (bắt buộc)"
                          : row.generationMode === "reference_frame_2_video"
                            ? "Reference media_id 2 (tùy chọn)"
                            : "End media_id (tùy chọn)"}
                      </Label>
                      <div className="flex gap-2">
                        <Input
                          value={rowSecondaryMediaId}
                          disabled={row.generationMode === "frame_2_video"}
                          onChange={(e) =>
                            updateRow(row.id, {
                              ...(usesReferenceInputs
                                ? { referenceMediaId2: e.target.value }
                                : { endMediaId: e.target.value }),
                              status: "IDLE",
                            })
                          }
                          placeholder={
                            row.generationMode === "start_end_frame_2_video"
                              ? "UUID media_id ảnh cuối (bắt buộc)"
                              : row.generationMode === "reference_frame_2_video"
                                ? "UUID media_id ảnh tham chiếu 2 (tùy chọn)"
                                : "Không dùng ở mode Ảnh sang video"
                          }
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={row.generationMode === "frame_2_video"}
                          onClick={() => {
                            void pickImageFile(
                              row.id,
                              usesReferenceInputs ? "ref2" : "end",
                            );
                          }}
                        >
                          <Upload size={12} />
                          {row.generationMode === "reference_frame_2_video"
                            ? "Ref 2"
                            : "Ảnh cuối"}
                        </Button>
                      </div>
                      {rowSecondaryFilePath && (
                        <div className="text-xs text-[hsl(var(--muted-foreground))] break-all">
                          File: {rowSecondaryFilePath}
                        </div>
                      )}
                    </div>
                  </div>

                  {rowValidationError && (
                    <div className="text-xs rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-700">
                      {rowValidationError}
                    </div>
                  )}
                </>
              )}

              {row.error && (
                <div className="text-xs rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-600">
                  {row.error}
                </div>
              )}

              {row.mediaId && (
                <div className="text-xs">
                  <strong>media_id:</strong> {row.mediaId}
                </div>
              )}

              {row.url && (
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap gap-2">
                    <a
                      className="text-xs underline"
                      href={row.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Mở video gốc
                    </a>
                    <button
                      type="button"
                      className="text-xs underline"
                      onClick={() => {
                        void downloadRowVideo(row, idx);
                      }}
                    >
                      Tải video
                    </button>
                  </div>
                  <div
                    className="rounded-md border border-[hsl(var(--border))] overflow-hidden bg-[hsl(var(--muted))]"
                    style={{
                      aspectRatio: aspectCss(row.aspectRatio),
                      maxHeight: "380px",
                    }}
                  >
                    <video
                      src={row.url}
                      controls
                      className="h-full w-full object-contain"
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          );
        })}
      </div>
    </div>
  );
}
