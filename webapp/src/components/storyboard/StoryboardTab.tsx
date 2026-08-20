import { useEffect, useRef, useState } from "react";
import {
  api,
  storyboard,
  storyboardExportUrl,
  shotImageDownloadUrl,
  type Entity,
  type Project,
  type Scene,
  type Shot,
} from "../../api/client";
import type { EditorTarget } from "../nodeeditor/NodeEditor";
import MediaCard from "../common/MediaCard";
import Lightbox from "../common/Lightbox";
import CandidatePicker from "../common/CandidatePicker";
import MediaHistory from "../common/MediaHistory";
import BulkAddShots from "../common/BulkAddShots";
import SceneHeading from "../common/SceneHeading";
import { announceScene, announceShotRenamed, useSceneEvents } from "../../lib/scenebus";
import { useConfirm } from "../common/Confirm";
import { downloadFile, slugName, pad3 } from "../../lib/download";
import { useJobs, useJobWatcher } from "../../jobs/JobsContext";

const slug = (s: string) => slugName(s);

const parseRefs = (s: string | null): string[] => {
  try {
    return JSON.parse(s || "[]");
  } catch {
    return [];
  }
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export default function StoryboardTab({
  project,
  onEdit,
  onCoverSet,
}: {
  project: Project;
  onEdit?: (t: EditorTarget) => void;
  onCoverSet?: (mediaId: string) => void;
}) {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [shotsByScene, setShotsByScene] = useState<Record<string, Shot[]>>({});
  const [sel, setSel] = useState<Shot | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [gening, setGening] = useState<Set<string>>(new Set());
  const [lightbox, setLightbox] = useState<Shot | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [candidate, setCandidate] = useState<Shot | null>(null);
  const [history, setHistory] = useState<Shot | null>(null);
  // Scene đang mở hộp "thêm hàng loạt" (dán nhiều dòng prompt → nhiều shot).
  const [bulk, setBulk] = useState<Scene | null>(null);
  const confirm = useConfirm();
  const { jobFor } = useJobs();
  // Scenes currently being rebuilt by a per-scene "Lời đọc" job (shots cleared optimistically).
  const [rebuilding, setRebuilding] = useState<Set<string>>(new Set());
  // Scenes currently having their camera angles re-varied (per-scene 🎬).
  const [revarying, setRevarying] = useState<Set<string>>(new Set());
  // Scenes whose audio is being re-synthesized (per-scene 🔊) — keeps images, re-times shots.
  const [rebuildingAudio, setRebuildingAudio] = useState<Set<string>>(new Set());
  // Narration preview playback (one scene at a time).
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Trần độ phân giải ảnh của tài khoản (ONE → 2K, Ultra → 4K) — chỉ để ghi vào tooltip nút
  // ⬇ cho biết bấm xuống sẽ ra file cỡ nào. Hỏi server chứ không đoán ở client.
  const [hiresInfo, setHiresInfo] = useState<{ label: string } | null>(null);

  const setAsCover = async (shot: Shot) => {
    if (!shot.image_media_id) return;
    setErr(null);
    try {
      await api.setCover(project.id, shot.image_media_id);
      onCoverSet?.(shot.image_media_id);
      setNotice(`Đã đặt "${shot.title}" làm ảnh đại diện dự án`);
      setTimeout(() => setNotice(null), 2500);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const loadShots = async (sid: string) => {
    const r = await storyboard.sceneShots(sid);
    setShotsByScene((m) => ({ ...m, [sid]: r.shots }));
  };

  // Tab Shots hiển thị CÙNG danh sách scene này và cũng đang sống trong DOM (workspace giữ
  // mọi tab đã mở). Đổi tên/thêm/xoá scene bên đó phải thấy được ở đây mà không cần bấm ⟳.
  useSceneEvents(project.id, (e) => {
    if (e.type === "renamed") {
      setScenes((list) =>
        list.map((x) => (x.id === e.id ? { ...x, heading: e.heading } : x)));
      return;
    }
    if (e.type === "shot-renamed") {
      setShotsByScene((m) => m[e.sceneId]
        ? { ...m, [e.sceneId]: m[e.sceneId].map(
              (x) => (x.id === e.id ? { ...x, title: e.title } : x)) }
        : m);
      return;
    }
    api.listScenes(project.id)
      .then(async ({ scenes: list }) => {
        setScenes(list);
        for (const sc of list) if (!shotsByScene[sc.id]) await loadShots(sc.id);
      })
      .catch(() => {});
  });

  useEffect(() => {
    storyboard.hiresStatus(project.id).then(setHiresInfo).catch(() => {});
    (async () => {
      const sc = (await api.listScenes(project.id)).scenes;
      setScenes(sc);
      setEntities((await api.listEntities(project.id)).entities);
      for (const s of sc) await loadShots(s.id);
    })().catch((e) => setErr(e.message));
  }, [project.id]);

  const setShot = (updated: Shot) => {
    setShotsByScene((m) => ({
      ...m,
      [updated.scene_id]: (m[updated.scene_id] || []).map((x) =>
        x.id === updated.id ? updated : x
      ),
    }));
    if (sel?.id === updated.id) setSel(updated);
    // Thẻ shot ở tab Shots cũng hiện `title` — báo sang để hai tab không gọi cùng một shot
    // bằng hai cái tên. (Phát cả khi title không đổi: bên nhận đặt lại đúng giá trị cũ.)
    announceShotRenamed(project.id, updated);
  };

  const genImage = async (shot: Shot): Promise<boolean> => {
    setGening((s) => new Set(s).add(shot.id));
    setErr(null);
    try {
      setShot(await storyboard.genImage(shot.id));
      return true;
    } catch (e: any) {
      setErr(e.message);
      return false;
    } finally {
      setGening((s) => {
        const n = new Set(s);
        n.delete(shot.id);
        return n;
      });
    }
  };

  const autofill = async (sid: string) => {
    setBusy("autofill:" + sid);
    setErr(null);
    try {
      const r = await storyboard.autofill(sid);
      setShotsByScene((m) => ({ ...m, [sid]: r.shots }));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  const sceneAll = async (sid: string) => {
    const todo = (shotsByScene[sid] || []).filter((s) => !s.image_path);
    if (!todo.length) {
      setErr("Mọi frame trong scene đã có ảnh.");
      return;
    }
    // Không hỏi credit: tạo ảnh trên Flow KHÔNG trừ credit (chỉ video mới trừ).
    setErr(null);
    try {
      await storyboard.genSceneAll(sid);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Rebuild ONE scene by its narration (TTS) — the escape hatch when the project-wide
  // "Dựng theo lời đọc" misses a scene (so you don't fall back to a silent Autofill).
  const buildSceneBeats = async (sid: string) => {
    const ok = await confirm({
      title: "Dựng lại scene này theo lời đọc?",
      message:
        "Đọc (TTS) phần nội dung gốc của RIÊNG scene này, đo thời lượng và cắt beat bám " +
        "đúng audio. Thao tác này XOÁ các shot hiện tại của scene.",
      confirmText: "Dựng shots",
      danger: true,
    });
    if (!ok) return;
    setErr(null);
    // Optimistic: clear this scene's shots right away so the delete is visible, and mark
    // it "đang dựng" — the background job streams state to the banner; the "beats" watcher
    // reloads shots + scene meta when it finishes.
    setShotsByScene((m) => ({ ...m, [sid]: [] }));
    setRebuilding((s) => new Set(s).add(sid));
    try {
      await storyboard.buildSceneBeats(sid);
    } catch (e: any) {
      setErr(e.message);
      setRebuilding((s) => {
        const n = new Set(s);
        n.delete(sid);
        return n;
      });
      await loadShots(sid); // restore on failure to start
    }
  };

  // Play / stop a scene's narration WAV (nghe thử).
  const toggleAudio = (sc: Scene) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (playing === sc.id || !sc.narration_path) {
      setPlaying(null);
      return;
    }
    const a = new Audio(sc.narration_path);
    a.onended = () => setPlaying(null);
    a.onerror = () => {
      setPlaying(null);
      setErr("Không phát được audio scene.");
    };
    void a.play();
    audioRef.current = a;
    setPlaying(sc.id);
  };

  // Play / stop ONE shot's slice of the scene WAV (nghe thử lời đọc của shot này).
  // The scene WAV concatenates all beats; this shot starts at sh.start_time and runs
  // for sh.narration_duration (read + trailing gap), so we seek + stop at the boundary.
  const toggleShotAudio = (sc: Scene, sh: Shot) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (playing === sh.id || !sc.narration_path) {
      setPlaying(null);
      return;
    }
    const start = sh.start_time || 0;
    const end = start + (sh.narration_duration || 0);
    const a = new Audio(sc.narration_path);
    const stop = () => {
      a.pause();
      if (audioRef.current === a) audioRef.current = null;
      setPlaying(null);
    };
    a.onloadedmetadata = () => {
      a.currentTime = start;
    };
    a.ontimeupdate = () => {
      if (end > start && a.currentTime >= end) stop();
    };
    a.onended = stop;
    a.onerror = () => {
      stop();
      setErr("Không phát được audio shot.");
    };
    void a.play();
    audioRef.current = a;
    setPlaying(sh.id);
  };

  // Audio status of a scene: measured = real TTS WAV exists; else estimate from beats.
  const sceneAudio = (sc: Scene) => {
    const list = shotsByScene[sc.id] || [];
    const measured = !!sc.narration_path;
    const dur = sc.narration_duration ?? list.reduce((a, s) => a + (s.narration_duration || 0), 0);
    const hasNarr = measured || list.some((s) => s.narrator_text || s.narration_duration);
    return { measured, dur, hasNarr };
  };

  // ── Reorder (kéo-thả / mũi tên) ──
  const dragShot = useRef<{ sceneId: string; id: string } | null>(null);

  const moveScene = async (pos: number, dir: -1 | 1) => {
    const j = pos + dir;
    if (j < 0 || j >= scenes.length) return;
    const next = [...scenes];
    [next[pos], next[j]] = [next[j], next[pos]];
    const reindexed = next.map((s, i) => ({ ...s, idx: i }));
    setScenes(reindexed);
    try {
      await storyboard.reorderScenes(project.id, reindexed.map((s) => s.id));
      announceScene({ type: "list-changed", projectId: project.id });
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const dropShot = async (sceneId: string, targetId: string) => {
    const d = dragShot.current;
    dragShot.current = null;
    if (!d || d.sceneId !== sceneId || d.id === targetId) return;
    const list = shotsByScene[sceneId] || [];
    const from = list.findIndex((s) => s.id === d.id);
    const to = list.findIndex((s) => s.id === targetId);
    if (from < 0 || to < 0) return;
    const next = [...list];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    const reindexed = next.map((s, i) => ({ ...s, idx: i }));
    setShotsByScene((m) => ({ ...m, [sceneId]: reindexed }));
    try {
      await storyboard.reorderShots(sceneId, reindexed.map((s) => s.id));
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const reloadAll = async () => {
    for (const s of scenes) await loadShots(s.id);
  };

  // Stop any narration playback when leaving the tab / switching project.
  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, [project.id]);

  // Refetch frames as the server storyboard batch advances (§9) — images fill in live
  // and survive tab close / reload.
  const imgJob = jobFor("storyboard");
  useJobWatcher("storyboard", {
    onAdvance: reloadAll,
    onDone: (j) => {
      reloadAll();
      if (j.errors.length) setErr(`Auto gen ảnh: ${j.done}/${j.total} xong, ${j.errors.length} lỗi.`);
    },
  });

  // Thêm scene bằng tay (đường không qua kịch bản). `shots` > 0 → scene mới có sẵn khung
  // trống để bắt tay vào làm ngay.
  const addScene = async (shots = 0) => {
    setErr(null);
    try {
      const sc = await api.addScene(project.id, { shots });
      setScenes((list) => [...list, sc]);
      await loadShots(sc.id);
      announceScene({ type: "list-changed", projectId: project.id });
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Xoá scene + mọi shot trong nó. Hỏi lại khi scene còn shot: shot đã render là công sức
  // (và credit) thật, xoá nhầm không lấy lại được.
  const delScene = async (sc: Scene) => {
    const n = (shotsByScene[sc.id] || []).length;
    if (
      n &&
      !(await confirm({
        title: "Xoá scene?",
        message: `"${sc.heading}" còn ${n} shot — xoá scene là xoá luôn cả ${n} shot đó.`,
        confirmText: "Xoá",
        danger: true,
      }))
    )
      return;
    setErr(null);
    try {
      await api.deleteScene(sc.id);
      announceScene({ type: "list-changed", projectId: project.id });
      setScenes((list) => list.filter((x) => x.id !== sc.id).map((x, i) => ({ ...x, idx: i })));
      setShotsByScene((m) => {
        const n2 = { ...m };
        delete n2[sc.id];
        return n2;
      });
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Storytelling "Dựng theo lời đọc" runs as a job too (TTS is slow). Reload shots scene
  // by scene as each is rebuilt, and announce the result.
  const beatsJob = jobFor("beats");
  // Refetch scenes too so narration badges (🎙 / ⏱) update after a beats run.
  const refreshScenes = async () => {
    try {
      setScenes((await api.listScenes(project.id)).scenes);
    } catch {
      /* keep current */
    }
  };
  useJobWatcher("beats", {
    onAdvance: reloadAll,
    onDone: (j) => {
      reloadAll();
      refreshScenes();
      setRebuilding(new Set());
      if (j.errors.length) {
        setErr(`Dựng lời đọc: ${j.done}/${j.total} scene xong, ${j.errors.length} lỗi.`);
      } else {
        setNotice(`Đã dựng lời đọc + beats cho ${j.done}/${j.total} scene.`);
        setTimeout(() => setNotice(null), 6000);
      }
    },
  });

  // Bulk "🔊 Tạo lại audio (tất cả)" — re-TTS + re-time every scene, KEEPS images. Same watcher
  // shape as beats, but it never clears shots, so just refresh timing/badges as it advances.
  const audioJob = jobFor("audio");
  useJobWatcher("audio", {
    onAdvance: () => {
      reloadAll();
      refreshScenes();
    },
    onDone: (j) => {
      reloadAll();
      refreshScenes();
      if (j.errors.length) {
        setErr(`Tạo lại audio: ${j.done}/${j.total} scene xong, ${j.errors.length} lỗi.`);
      } else {
        setNotice(`Đã tạo lại audio cho ${j.done}/${j.total} scene (giữ nguyên ảnh).`);
        setTimeout(() => setNotice(null), 6000);
      }
    },
  });

  // "Đa dạng góc máy": rewrites shot descriptions only (keeps audio) → regen images after.
  const revaryJob = jobFor("revary");
  useJobWatcher("revary", {
    onAdvance: reloadAll,
    onDone: (j) => {
      reloadAll();
      setRevarying(new Set());
      if (j.errors.length) {
        setErr(`Đa dạng góc máy: ${j.done}/${j.total} scene xong, ${j.errors.length} lỗi.`);
      } else {
        setNotice(`Đã đổi góc máy cho ${j.done}/${j.total} scene — bấm “Auto gen all” để vẽ lại ảnh.`);
        setTimeout(() => setNotice(null), 8000);
      }
    },
  });

  const revaryAll = async () => {
    setErr(null);
    try {
      await storyboard.revaryProject(project.id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const revaryScene = async (sid: string) => {
    setErr(null);
    setRevarying((s) => new Set(s).add(sid));
    try {
      await storyboard.revaryScene(sid);
    } catch (e: any) {
      setErr(e.message);
      setRevarying((s) => {
        const n = new Set(s);
        n.delete(sid);
        return n;
      });
    }
  };

  // Re-synthesize ONLY this scene's audio from its existing shots' narration, then re-time the
  // shots + captions — keeps the (slow-to-make) images. Synchronous; no image re-gen.
  const rebuildAudio = async (sid: string) => {
    setErr(null);
    setRebuildingAudio((s) => new Set(s).add(sid));
    try {
      const r = await storyboard.rebuildSceneAudio(sid);
      setShotsByScene((m) => ({ ...m, [sid]: r.shots }));
      setScenes((list) =>
        list.map((s) =>
          s.id === sid
            ? { ...s, narration_path: r.narration_path, narration_duration: r.scene_duration }
            : s
        )
      );
      setNotice(`Đã tạo lại audio (${Math.round(r.scene_duration)}s) — đã căn lại thời gian & caption`);
      setTimeout(() => setNotice(null), 3500);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setRebuildingAudio((s) => {
        const n = new Set(s);
        n.delete(sid);
        return n;
      });
    }
  };

  const autofillAll = async () => {
    setBusy("autofill-all");
    setErr(null);
    try {
      await storyboard.autofillAll(project.id);
      await reloadAll();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  // Storytelling (§2.6): TTS each scene as ONE continuous read first, then map beats.
  const buildBeats = async () => {
    const ok = await confirm({
      title: "Dựng shots theo lời đọc?",
      message:
        "Mỗi scene được đọc (TTS) liền mạch MỘT lần để giữ cảm xúc, rồi cắt thành beat " +
        "(1 cảnh) bám đúng thời điểm audio; từ khoá quan trọng được canh giờ để hiện chữ " +
        "lên video. Cần BẬT OmniVoice (TTS); nếu tắt sẽ ước lượng theo số từ.\n\n" +
        "Thao tác này XOÁ các shot + ẢNH hiện có của mọi scene.",
      confirmText: "Dựng shots (tất cả)",
      danger: true,
    });
    if (!ok) return;
    setErr(null);
    try {
      // Background job (§9): TTS is slow, so we kick it off and watch progress in the
      // banner instead of blocking. Shots rebuild scene-by-scene as it advances.
      await storyboard.buildBeats(project.id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Bulk "🔊 Tạo lại audio (tất cả)": re-TTS + re-time EVERY scene, KEEPING images — the safe,
  // non-destructive counterpart of "🎙 Dựng shots (tất cả)". Runs as a background job.
  const rebuildAudioAll = async () => {
    const ok = await confirm({
      title: "Tạo lại audio cho TẤT CẢ scene?",
      message:
        "Đọc (TTS) lại liền mạch từng scene rồi căn lại thời gian + phụ đề cho các shot HIỆN CÓ. " +
        "GIỮ NGUYÊN ảnh/prompt/ref — không vẽ lại ảnh. Dùng khi đổi giọng/tốc độ/khoảng nghỉ. " +
        "Cần BẬT OmniVoice; chạy nền và hơi lâu (mỗi scene phải đọc + căn giờ).",
      confirmText: "Tạo lại audio (tất cả)",
    });
    if (!ok) return;
    setErr(null);
    try {
      await storyboard.rebuildProjectAudio(project.id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  // Re-align the source prose to scenes by CONTENT (fixes narration landing in the wrong
  // scene). Doesn't touch shots/audio — you rebuild "Dựng theo lời đọc" after.
  const alignSource = async () => {
    const ok = await confirm({
      title: "Căn lại nội dung vào đúng scene?",
      message:
        "Dùng AI gán lại từng đoạn của nội dung gốc vào scene khớp bối cảnh của nó (theo " +
        "heading/địa điểm), thay cho cách chia đều theo độ dài. Sau đó hãy '🎙 Dựng shots (tất cả)' lại.",
      confirmText: "Căn lại nội dung",
    });
    if (!ok) return;
    setBusy("align");
    setErr(null);
    try {
      await storyboard.alignSource(project.id);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  // Split ONE over-long scene into ~90s sub-scenes (same location) so each gets its own
  // coherent shot plan. Clears the scene's shots — rebuild after with "Dựng theo lời đọc".
  const splitScene = async (sc: Scene) => {
    const ok = await confirm({
      title: "Tách scene dài này?",
      message:
        "Chia scene thành nhiều scene ngắn (~90s) THEO THỜI LƯỢNG, GIỮ NGUYÊN địa điểm. " +
        "Các shot hiện tại của scene sẽ bị xoá — sau đó bấm '🎙 Dựng shots' để dựng lại. " +
        "Dùng khi cả chương bị gộp thành 1 scene / shot quá dài.",
      confirmText: "Tách scene",
      danger: true,
    });
    if (!ok) return;
    setBusy("split:" + sc.id);
    setErr(null);
    try {
      const r = await storyboard.splitScene(sc.id);
      setScenes(r.scenes);
      for (const x of r.scenes) await loadShots(x.id);
      announceScene({ type: "list-changed", projectId: project.id });
      setNotice(`Đã tách thành ${r.split_into} scene (cùng địa điểm) — hãy '🎙 Dựng shots' lại.`);
      setTimeout(() => setNotice(null), 4000);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  // Rebuild the shot list for EVERY scene from the script (force) — deletes existing
  // shots (incl. manual edits) and re-splits via AI. Confirm because it's destructive.
  const rebuildAll = async () => {
    const ok = await confirm({
      title: "Dựng lại tất cả shots từ kịch bản?",
      message:
        "Thao tác này XOÁ các shot hiện tại (kể cả prompt/ảnh đã chỉnh tay) và để AI tách lại từ script.",
      confirmText: "Dựng lại tất cả",
      danger: true,
    });
    if (!ok) return;
    setBusy("rebuild-all");
    setErr(null);
    try {
      const r = await storyboard.autofillAll(project.id, undefined, true);
      await reloadAll();
      setNotice(`Đã dựng lại shots cho ${r.done}/${r.requested} scene`);
      setTimeout(() => setNotice(null), 3000);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  };

  // Server-side background job (§9): generate every frame without an image.
  const projectAll = async () => {
    const todo = scenes.flatMap((sc) => (shotsByScene[sc.id] || []).filter((s) => !s.image_path));
    if (!todo.length) {
      setErr("Mọi frame đã có ảnh.");
      return;
    }
    // Không hỏi credit: tạo ảnh trên Flow KHÔNG trừ credit (chỉ video mới trừ).
    setErr(null);
    try {
      await storyboard.genProjectAll(project.id);
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="flex h-full">
      <div className="min-w-0 flex-1 overflow-auto px-6 py-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Storyboard</h2>
            <p className="text-sm text-neutral-500">Ảnh từng frame theo scene</p>
          </div>
          <div className="flex gap-2">
            {!project.storytelling && (
              <>
                <button
                  disabled={!!busy || !scenes.length}
                  onClick={autofillAll}
                  title="Autofill các scene CHƯA có shot (bỏ qua scene đã có)"
                  className="rounded-lg border border-neutral-700 px-3 py-2 text-sm hover:bg-neutral-800 disabled:opacity-40"
                >
                  {busy === "autofill-all" ? "Đang autofill…" : "✨ Autofill all"}
                </button>
                <button
                  disabled={!!busy || !scenes.length}
                  onClick={rebuildAll}
                  title="Dựng lại shots từ kịch bản cho MỌI scene (xóa shot cũ)"
                  className="rounded-lg border border-amber-700/60 px-3 py-2 text-sm text-amber-300 hover:bg-amber-950/40 disabled:opacity-40"
                >
                  {busy === "rebuild-all" ? "Đang dựng lại…" : "↻ Dựng lại tất cả"}
                </button>
              </>
            )}
            {!!project.storytelling && (
              <>
                <button
                  disabled={!!busy || !!beatsJob || !!audioJob || !scenes.length}
                  onClick={alignSource}
                  title="Căn nội dung gốc vào đúng scene theo bối cảnh (sửa lệch nội dung giữa các scene). Sau đó bấm '🎙 Dựng shots (tất cả)'."
                  className="rounded-lg border border-sky-700/60 px-3 py-2 text-sm text-sky-300 hover:bg-sky-950/40 disabled:opacity-40"
                >
                  {busy === "align" ? "Đang căn nội dung…" : "🧭 Căn nội dung scene"}
                </button>
                <button
                  disabled={!!busy || !!beatsJob || !!audioJob || !scenes.length}
                  onClick={buildBeats}
                  title="Đọc (TTS) liền mạch mỗi scene rồi cắt shots bám đúng audio, cho MỌI scene. ⚠ Xoá shots + ảnh hiện có. Chỉ muốn làm lại tiếng (GIỮ ảnh) thì dùng '🔊 Tạo lại audio (tất cả)'."
                  className="rounded-lg border border-violet-700/60 px-3 py-2 text-sm text-violet-300 hover:bg-violet-950/40 disabled:opacity-40"
                >
                  {beatsJob ? `Đang dựng ${beatsJob.done}/${beatsJob.total}…` : "🎙 Dựng shots (tất cả)"}
                </button>
                <button
                  disabled={!!busy || !!beatsJob || !!audioJob || !scenes.length}
                  onClick={rebuildAudioAll}
                  title="Tạo LẠI audio cho MỌI scene từ lời đọc hiện có (GIỮ ảnh) rồi căn lại thời gian + phụ đề. Dùng khi đổi giọng/tốc độ/khoảng nghỉ mà không vẽ lại ảnh."
                  className="rounded-lg border border-sky-700/60 px-3 py-2 text-sm text-sky-300 hover:bg-sky-950/40 disabled:opacity-40"
                >
                  {audioJob ? `Đang tạo audio ${audioJob.done}/${audioJob.total}…` : "🔊 Tạo lại audio (tất cả)"}
                </button>
              </>
            )}
            <button
              disabled={!!busy || !!revaryJob || !scenes.length}
              onClick={revaryAll}
              title="Đổi/đa dạng góc máy cho mọi shot (giữ nguyên lời đọc & thời lượng — KHÔNG chạy lại TTS). Xong rồi bấm Auto gen all để vẽ lại ảnh."
              className="rounded-lg border border-teal-700/60 px-3 py-2 text-sm text-teal-300 hover:bg-teal-950/40 disabled:opacity-40"
            >
              {revaryJob ? `Đổi góc ${revaryJob.done}/${revaryJob.total}…` : "🎬 Đa dạng góc máy"}
            </button>
            <button
              onClick={() => downloadFile(storyboardExportUrl(project.id), "storyboard.zip")}
              title="Tải toàn bộ ảnh storyboard (.zip, scXXX-sXXX-mô-tả.png)"
              className="rounded-lg border border-neutral-700 px-3 py-2 text-sm hover:bg-neutral-800"
            >
              ⬇ Export ảnh
            </button>
            <button
              disabled={!!busy || !!imgJob || !scenes.length}
              onClick={projectAll}
              title="Tạo ảnh cho mọi frame chưa có ảnh trong dự án"
              className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
            >
              {imgJob ? `Đang tạo ${imgJob.done}/${imgJob.total}…` : "✦ Auto gen all"}
            </button>
          </div>
        </div>
        {progress && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-indigo-800 bg-indigo-950/40 px-3 py-2 text-sm text-indigo-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
            {progress}
          </div>
        )}
        {notice && (
          <div className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">
            ★ {notice}
          </div>
        )}
        {err && (
          <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
            {err}
          </div>
        )}
        {!scenes.length && (
          // Dự án trắng vẫn phải làm được: mọi shot treo dưới `shot.scene_id`, nên "thêm shot"
          // khi chưa có scene nào = tạo scene rồi thêm shot vào đó, làm gọn trong một nút.
          <div className="rounded-xl border border-dashed border-neutral-800 py-12 text-center text-sm text-neutral-500">
            <p>Chưa có scene — tạo kịch bản ở tab Script, hoặc tự thêm shot ở đây.</p>
            <button
              disabled={!!busy}
              onClick={() => addScene(1)}
              className="mt-3 rounded-lg border border-neutral-700 px-3 py-2 text-sm text-neutral-200 hover:bg-neutral-800 disabled:opacity-40"
            >
              + Thêm scene (kèm 1 shot)
            </button>
          </div>
        )}
        {scenes.map((sc, scenePos) => {
          const shots = shotsByScene[sc.id] || [];
          return (
            <section key={sc.id} className="mb-8">
              <div className="mb-3 flex items-center gap-3">
                <SceneHeading
                  scene={sc}
                  index={scenePos}
                  projectId={project.id}
                  onRenamed={(u) =>
                    setScenes((list) => list.map((x) => (x.id === u.id ? u : x)))
                  }
                />
                {(() => {
                  const a = sceneAudio(sc);
                  if (!a.hasNarr) return null;
                  return a.measured ? (
                    <span
                      title="Scene có audio lời đọc (TTS) thật — thời lượng đo từ giọng đọc"
                      className="rounded bg-emerald-900/50 px-1.5 py-0.5 text-[11px] text-emerald-300"
                    >
                      🎙 {Math.round(a.dur)}s
                    </span>
                  ) : (
                    <span
                      title="Chưa có audio TTS — thời lượng đang ƯỚC LƯỢNG theo số từ. Bấm 🎙 Lời đọc để tạo audio thật."
                      className="rounded bg-amber-900/40 px-1.5 py-0.5 text-[11px] text-amber-300"
                    >
                      ⏱ ~{Math.round(a.dur)}s
                    </span>
                  );
                })()}
                {sc.narration_path && (
                  <button
                    onClick={() => toggleAudio(sc)}
                    title="Nghe thử lời đọc của scene"
                    className="grid h-6 w-6 place-items-center rounded text-emerald-300 hover:bg-emerald-950/40"
                  >
                    {playing === sc.id ? "⏸" : "▶"}
                  </button>
                )}
                <div className="flex items-center">
                  <button
                    disabled={scenePos === 0 || !!busy}
                    onClick={() => moveScene(scenePos, -1)}
                    title="Đưa scene lên"
                    className="grid h-6 w-6 place-items-center rounded text-neutral-500 hover:bg-neutral-800 hover:text-neutral-200 disabled:opacity-30"
                  >
                    ▲
                  </button>
                  <button
                    disabled={scenePos === scenes.length - 1 || !!busy}
                    onClick={() => moveScene(scenePos, 1)}
                    title="Đưa scene xuống"
                    className="grid h-6 w-6 place-items-center rounded text-neutral-500 hover:bg-neutral-800 hover:text-neutral-200 disabled:opacity-30"
                  >
                    ▼
                  </button>
                </div>
                <div className="ml-auto flex gap-2">
                  <button
                    disabled={!!busy}
                    onClick={() => splitScene(sc)}
                    title="Tách scene dài này thành nhiều scene ~90s (GIỮ địa điểm) — khi cả chương bị gộp 1 scene / shot quá dài. Xoá shot hiện tại, dựng lại sau."
                    className="rounded-md border border-amber-700/60 px-2.5 py-1 text-xs text-amber-300 hover:bg-amber-950/40 disabled:opacity-40"
                  >
                    {busy === "split:" + sc.id ? "Đang tách…" : "✂ Tách scene"}
                  </button>
                  {!project.storytelling && (
                    <button
                      disabled={!!busy}
                      onClick={() => autofill(sc.id)}
                      className="rounded-md border border-neutral-700 px-2.5 py-1 text-xs hover:bg-neutral-800 disabled:opacity-40"
                    >
                      {busy === "autofill:" + sc.id ? "…" : "✨ Autofill"}
                    </button>
                  )}
                  {!!project.storytelling && (
                    <button
                      disabled={!!busy || !!beatsJob || !!audioJob}
                      onClick={() => buildSceneBeats(sc.id)}
                      title="Dựng lại toàn bộ shots của scene này từ lời đọc (TTS). ⚠ XOÁ shots + ẢNH hiện có rồi cắt lại từ đầu — chỉ dùng khi scene chưa có shot hoặc muốn chia lại. Nếu chỉ muốn làm lại tiếng mà GIỮ ảnh, dùng '🔊 Tạo lại audio'."
                      className="rounded-md border border-violet-700/60 px-2.5 py-1 text-xs text-violet-300 hover:bg-violet-950/40 disabled:opacity-40"
                    >
                      {rebuilding.has(sc.id) ? "Đang dựng…" : "🎙 Dựng shots"}
                    </button>
                  )}
                  {!!project.storytelling && !!shots.length && (
                    <button
                      disabled={!!busy || !!beatsJob || !!audioJob || rebuildingAudio.has(sc.id)}
                      onClick={() => rebuildAudio(sc.id)}
                      title="Tạo LẠI audio cho scene này từ lời đọc hiện có của các shot (GIỮ ảnh đã tạo), rồi căn lại thời gian & caption. Dùng khi đổi tốc độ/khoảng nghỉ/đệm 2 đầu mà không muốn vẽ lại ảnh."
                      className="rounded-md border border-sky-700/60 px-2.5 py-1 text-xs text-sky-300 hover:bg-sky-950/40 disabled:opacity-40"
                    >
                      {rebuildingAudio.has(sc.id) ? "Đang tạo audio…" : "🔊 Tạo lại audio"}
                    </button>
                  )}
                  <button
                    disabled={!!busy || !!revaryJob || !shots.length}
                    onClick={() => revaryScene(sc.id)}
                    title="Đổi/đa dạng góc máy cho các shot của scene này (giữ lời đọc — không chạy lại TTS). Xong bấm Auto gen để vẽ lại ảnh."
                    className="rounded-md border border-teal-700/60 px-2.5 py-1 text-xs text-teal-300 hover:bg-teal-950/40 disabled:opacity-40"
                  >
                    {revarying.has(sc.id) ? "Đổi góc…" : "🎬 Góc máy"}
                  </button>
                  <button
                    disabled={!!busy || !!imgJob || !shots.length}
                    onClick={() => sceneAll(sc.id)}
                    className="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
                  >
                    {imgJob ? "…" : "✦ Auto gen"}
                  </button>
                  <button
                    disabled={!!busy}
                    onClick={() => delScene(sc)}
                    title="Xoá scene này và mọi shot trong nó"
                    className="rounded-md border border-neutral-700 px-2 py-1 text-xs text-neutral-400 hover:bg-rose-950/40 hover:text-rose-300 disabled:opacity-40"
                  >
                    🗑
                  </button>
                </div>
              </div>
              {rebuilding.has(sc.id) && (
                <div className="mb-3 flex items-center gap-2 rounded-lg border border-violet-800/60 bg-violet-950/30 px-3 py-2 text-sm text-violet-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-violet-400" />
                  🎙 Đang đọc (TTS) & dựng beat cho scene này… (xem tiến độ ở góc phải)
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {shots.map((sh) => (
                  <div
                    key={sh.id}
                    className="relative"
                    draggable
                    onDragStart={() => (dragShot.current = { sceneId: sc.id, id: sh.id })}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      dropShot(sc.id, sh.id);
                    }}
                    title="Kéo để đổi thứ tự shot"
                  >
                  {(sh.narrator_text || sh.narration_duration != null) &&
                    (sc.narration_path ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleShotAudio(sc, sh);
                        }}
                        title={
                          (sh.narrator_text ? `Lời đọc: "${sh.narrator_text}"\n` : "") +
                          `Nghe thử shot này (${(sh.narration_duration || 0).toFixed(1)}s)`
                        }
                        className={`absolute left-1.5 top-1.5 z-10 flex items-center gap-1 rounded px-1 py-0.5 text-[10px] transition-colors ${
                          playing === sh.id
                            ? "bg-rose-600/90 text-white"
                            : "bg-emerald-600/85 text-white hover:bg-emerald-500"
                        }`}
                      >
                        {playing === sh.id ? "⏸" : "▶"} {(sh.narration_duration || 0).toFixed(1)}s
                      </button>
                    ) : (
                      <span
                        title={
                          (sh.narrator_text ? `Lời đọc: "${sh.narrator_text}"\n` : "") +
                          `Ước lượng ${(sh.narration_duration || 0).toFixed(1)}s — chưa có audio thật`
                        }
                        className="absolute left-1.5 top-1.5 z-10 rounded bg-amber-600/80 px-1 py-0.5 text-[10px] text-white"
                      >
                        ⏱ {(sh.narration_duration || 0).toFixed(1)}s
                      </span>
                    ))}
                  <MediaCard
                    imageSrc={sh.image_path}
                    title={sh.title}
                    index={sh.idx}
                    subtitle={sh.description}
                    selected={sel?.id === sh.id}
                    busy={gening.has(sh.id)}
                    busyLabel="Đang tạo ảnh…"
                    onClick={() => setSel(sh)}
                    onPreview={sh.image_path ? () => setLightbox(sh) : undefined}
                    onEdit={
                      onEdit
                        ? () =>
                            onEdit({
                              kind: "shot",
                              goal: "image",
                              id: sh.id,
                              title: sh.title,
                              prompt: sh.description || sh.visual_prompt || sh.title,
                              refEntityIds: parseRefs(sh.ref_entity_ids),
                              imageMediaId: sh.image_media_id,
                              imageSrc: sh.image_path,
                              videoSrc: sh.video_path,
                            })
                        : undefined
                    }
                    actions={
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            genImage(sh);
                          }}
                          title="Gen nhanh"
                          className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-indigo-600"
                        >
                          ⚡
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setCandidate(sh);
                          }}
                          title="Tạo nhiều mẫu rồi chọn ảnh đẹp nhất"
                          className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-indigo-600"
                        >
                          🎲
                        </button>
                        {sh.image_path && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setHistory(sh);
                            }}
                            title="Lịch sử phiên bản — khôi phục bản cũ"
                            className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-neutral-700"
                          >
                            🕘
                          </button>
                        )}
                        {sh.image_path && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Server tự kéo bản 2K/4K rồi mới trả file, và tự đặt tên
                              // scXXX-sXXX-mô-tả-4k.png — đừng tải thẳng image_path (bản HD).
                              downloadFile(shotImageDownloadUrl(sh.id));
                            }}
                            title={
                              hiresInfo
                                ? `Tải ảnh ở ${hiresInfo.label} (tự kéo bản nét nếu chưa có — không tốn credit)`
                                : "Tải ảnh ở độ phân giải cao nhất (tự kéo bản nét nếu chưa có)"
                            }
                            className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-emerald-600"
                          >
                            ⬇
                          </button>
                        )}
                        {sh.image_media_id && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setAsCover(sh);
                            }}
                            title="Đặt làm ảnh đại diện dự án"
                            className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-amber-600"
                          >
                            ★
                          </button>
                        )}
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            await storyboard.deleteShot(sh.id);
                            loadShots(sc.id);
                          }}
                          title="Xóa"
                          className="grid h-7 w-7 place-items-center rounded-md bg-neutral-900/80 text-sm hover:bg-rose-600"
                        >
                          🗑
                        </button>
                      </>
                    }
                  />
                  </div>
                ))}
                <div className="flex aspect-video flex-col gap-2">
                  <button
                    onClick={async () => {
                      await storyboard.addShot(sc.id);
                      loadShots(sc.id);
                    }}
                    title="Thêm một shot rỗng vào cuối scene"
                    className="flex-1 rounded-xl border border-dashed border-neutral-700 text-2xl text-neutral-600 hover:border-neutral-500 hover:text-neutral-400"
                  >
                    +
                  </button>
                  <button
                    onClick={() => setBulk(sc)}
                    title="Thêm nhiều shot cùng lúc — dán văn bản, mỗi dòng một prompt ảnh"
                    className="shrink-0 rounded-xl border border-dashed border-neutral-700 py-1.5 text-xs text-neutral-600 hover:border-neutral-500 hover:text-neutral-400"
                  >
                    ＋ hàng loạt
                  </button>
                </div>
              </div>
            </section>
          );
        })}
        {!!scenes.length && (
          <button
            disabled={!!busy}
            onClick={() => addScene(1)}
            title="Thêm một scene rỗng vào cuối (kèm 1 shot để làm ngay)"
            className="mb-8 w-full rounded-xl border border-dashed border-neutral-800 py-3 text-sm text-neutral-600 hover:border-neutral-600 hover:text-neutral-400 disabled:opacity-40"
          >
            + Thêm scene
          </button>
        )}
      </div>

      {sel && (
        <FramePanel
          shot={sel}
          entities={entities}
          onClose={() => setSel(null)}
          onChange={setShot}
          onGenerate={() => genImage(sel)}
          onCover={() => setAsCover(sel)}
          generating={gening.has(sel.id)}
        />
      )}

      {bulk && (
        <BulkAddShots
          sceneId={bulk.id}
          sceneTitle={bulk.heading}
          field="description"
          onDone={(r) => setShotsByScene((m) => ({ ...m, [bulk.id]: r.shots }))}
          onClose={() => setBulk(null)}
        />
      )}

      {lightbox && (
        // Xem thì dùng bản HD cho nhẹ, nhưng ⬇ trong lightbox phải ra bản 2K/4K như nút ⬇
        // trên thẻ — hai nút cùng một chỗ mà cho ra hai file khác cỡ là bẫy.
        <Lightbox
          imageSrc={lightbox.image_path}
          title={lightbox.title}
          downloadUrl={shotImageDownloadUrl(lightbox.id)}
          onClose={() => setLightbox(null)}
        />
      )}

      {candidate && (
        <CandidatePicker
          kind="shot"
          id={candidate.id}
          title={candidate.title}
          onApplied={(updated) =>
            setShotsByScene((m) => ({
              ...m,
              [updated.scene_id]: (m[updated.scene_id] || []).map((x) =>
                x.id === updated.id ? updated : x
              ),
            }))
          }
          onClose={() => setCandidate(null)}
        />
      )}

      {history && (
        <MediaHistory
          kind="shot"
          id={history.id}
          slot="image"
          title={history.title}
          onRestored={(updated) =>
            setShotsByScene((m) => ({
              ...m,
              [updated.scene_id]: (m[updated.scene_id] || []).map((x) =>
                x.id === updated.id ? updated : x
              ),
            }))
          }
          onClose={() => setHistory(null)}
        />
      )}
    </div>
  );
}

function FramePanel({
  shot,
  entities,
  onClose,
  onChange,
  onGenerate,
  onCover,
  generating,
}: {
  shot: Shot;
  entities: Entity[];
  onClose: () => void;
  onChange: (s: Shot) => void;
  onGenerate: () => void;
  onCover: () => void;
  generating: boolean;
}) {
  const [title, setTitle] = useState(shot.title);
  const [desc, setDesc] = useState(shot.description ?? "");
  const refIds: string[] = (() => {
    try {
      return JSON.parse(shot.ref_entity_ids || "[]");
    } catch {
      return [];
    }
  })();
  const [refs, setRefs] = useState<string[]>(refIds);

  useEffect(() => {
    setTitle(shot.title);
    setDesc(shot.description ?? "");
    try {
      setRefs(JSON.parse(shot.ref_entity_ids || "[]"));
    } catch {
      setRefs([]);
    }
  }, [shot.id]);

  const save = async () => {
    onChange(
      await storyboard.updateShot(shot.id, { title, description: desc, ref_entity_ids: refs })
    );
  };

  const toggleRef = (id: string) =>
    setRefs((r) => (r.includes(id) ? r.filter((x) => x !== id) : [...r, id]));

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-neutral-800 bg-neutral-950/50">
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2.5">
        <span className="text-sm font-medium">Frame</span>
        <button onClick={onClose} className="text-neutral-500 hover:text-neutral-300">✕</button>
      </div>
      <div className="flex-1 space-y-4 overflow-auto p-4">
        <div>
          <label className="mb-1 block text-xs text-neutral-400">Tiêu đề</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={save}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-neutral-400">Mô tả (dùng {"{Tên}"} để gắn ref)</label>
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            onBlur={save}
            className="h-28 w-full resize-none rounded-lg border border-neutral-700 bg-neutral-950 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-neutral-400">Reference Assets (≤10)</label>
          <div className="space-y-1">
            {entities.map((e) => (
              <label
                key={e.id}
                className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-neutral-800"
              >
                <input
                  type="checkbox"
                  checked={refs.includes(e.id)}
                  onChange={() => toggleRef(e.id)}
                  onBlur={save}
                  className="h-3.5 w-3.5 accent-indigo-500"
                />
                <span className={`h-1.5 w-1.5 rounded-full ${e.media_id ? "bg-emerald-400" : "bg-neutral-600"}`} />
                <span className="truncate text-neutral-300">{e.name}</span>
                <span className="ml-auto text-xs text-neutral-600">{e.type}</span>
              </label>
            ))}
            {!entities.length && <p className="text-xs text-neutral-600">Chưa có asset.</p>}
          </div>
        </div>
      </div>
      <div className="space-y-2 border-t border-neutral-800 p-3">
        <button
          onClick={async () => {
            await save();
            onGenerate();
          }}
          disabled={generating}
          className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
        >
          {generating ? "Đang tạo ảnh…" : "Create image"}
        </button>
        <button
          onClick={onCover}
          disabled={!shot.image_media_id}
          title={shot.image_media_id ? "" : "Tạo ảnh cho frame này trước"}
          className="w-full rounded-lg border border-amber-700/60 py-2 text-sm text-amber-300 hover:bg-amber-950/40 disabled:opacity-40"
        >
          ★ Đặt làm ảnh đại diện dự án
        </button>
      </div>
    </aside>
  );
}
