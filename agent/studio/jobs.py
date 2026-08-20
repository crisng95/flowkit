"""Background job manager for Flow Studio batch generation (video-app.md §9).

In-process asyncio jobs that outlive the HTTP request that started them, so closing
the browser tab no longer aborts a batch. Each job loops over a list of items,
calling an async worker per item with throttle between items. Progress is mirrored
to the `job` table and broadcast to WebSocket subscribers on /api/studio/ws.

The manager holds no Flow state of its own — workers are closures from studio.py
that call the existing per-item generate helpers.
"""
import asyncio
import json
import logging
import random
import time
from typing import Awaitable, Callable, Optional

from agent.studio import db

logger = logging.getLogger(__name__)

# Finished jobs linger this long so a tab that reconnects can still see the result.
_REAP_DELAY = 180.0


class Job:
    def __init__(self, jid: str, project_id: str, type_: str, total: int, label: str = ""):
        self.id = jid
        self.project_id = project_id
        self.type = type_
        self.total = total
        self.label = label
        self.done = 0
        self.errors: list[dict] = []
        self.status = "running"   # running | done | error | cancelled
        self.message = ""
        self.current = ""         # human label of the item in progress
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.cancel = asyncio.Event()
        self.task: Optional[asyncio.Task] = None

    @property
    def progress(self) -> float:
        if not self.total:
            return 1.0
        return (self.done + len(self.errors)) / self.total

    def to_dict(self) -> dict:
        return {
            "id": self.id, "project_id": self.project_id, "type": self.type,
            "label": self.label, "total": self.total, "done": self.done,
            "errors": self.errors, "status": self.status, "message": self.message,
            "current": self.current, "progress": round(self.progress, 4),
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._subs: set = set()

    # ── WebSocket subscribers ───────────────────────────────
    def subscribe(self, ws) -> None:
        self._subs.add(ws)

    def unsubscribe(self, ws) -> None:
        self._subs.discard(ws)

    async def _broadcast(self, job: Job) -> None:
        job.updated_at = time.time()
        payload = {"type": "job", "job": job.to_dict()}
        dead = []
        for ws in list(self._subs):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._subs.discard(ws)

    # ── Query / control ─────────────────────────────────────
    def active(self, project_id: Optional[str] = None) -> list[dict]:
        return [j.to_dict() for j in self._jobs.values()
                if project_id is None or j.project_id == project_id]

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        j = self._jobs.get(job_id)
        if j and j.status == "running":
            j.cancel.set()
            return True
        return False

    # ── Persistence (best-effort mirror to the job table) ───
    async def _persist(self, job: Job) -> None:
        try:
            row = {
                "project_id": job.project_id, "type": job.type, "status": job.status,
                "progress": job.progress, "message": job.message,
                "error": json.dumps(job.errors) if job.errors else None,
                "updated_at": time.time(),
            }
            existing = await db.query_one("SELECT id FROM job WHERE id=?", (job.id,))
            if existing:
                await db.update("job", job.id, row)
            else:
                await db.insert("job", {"id": job.id, "created_at": job.created_at, **row})
        except Exception:
            logger.exception("job persist failed")

    # ── Run a batch ─────────────────────────────────────────
    def start(
        self,
        *,
        project_id: str,
        type_: str,
        items: list,
        worker: Callable[[object], Awaitable[None]],
        label: str = "",
        throttle: tuple[float, float] = (2.0, 6.0),
        item_label: Optional[Callable[[object], str]] = None,
        finalize: Optional[Callable[[], Awaitable[None]]] = None,
        batch_size: int = 1,
        stagger: tuple[float, float] = (0.0, 0.0),
        unit: str = "ảnh",
    ) -> Job:
        """Run `worker` over `items`. batch_size=1 → one at a time with `throttle` between
        items. batch_size>1 → process items in groups of that many CONCURRENTLY, each group
        sharing a fresh batch id; `throttle` is then the COOLDOWN between groups. In batch mode
        the worker is called as worker(item, batch_id).

        `stagger` (batch mode): spread each group's submits by up to index*random(stagger)
        seconds so they don't hit Flow at the exact same instant — enough to dodge the
        anti-abuse 'unusual activity' heuristic while keeping most of the concurrency."""
        job = Job(db.new_id(), project_id, type_, len(items), label)
        self._jobs[job.id] = job
        runner = self._run_batched if batch_size > 1 else self._run
        job.task = asyncio.create_task(
            runner(job, items, worker, throttle, item_label, finalize, batch_size, stagger, unit))
        return job

    async def _cooldown(self, job, throttle) -> None:
        """Interruptible wait (wakes early if cancelled)."""
        try:
            await asyncio.wait_for(job.cancel.wait(), timeout=random.uniform(*throttle))
        except asyncio.TimeoutError:
            pass

    async def _run_batched(self, job, items, worker, throttle, item_label,
                           finalize=None, batch_size: int = 4,
                           stagger: tuple[float, float] = (0.0, 0.0),
                           unit: str = "ảnh") -> None:
        """Fire items in concurrent groups of `batch_size`, each group sharing one Flow batch
        id, with a cooldown between groups — like the web UI's 4-image batch. Cuts wall-clock
        time for large storyboards (400+ frames) roughly by the batch size."""
        import uuid
        await self._broadcast(job)
        await self._persist(job)
        groups = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        for gi, group in enumerate(groups):
            if job.cancel.is_set():
                job.status = "cancelled"
                break
            batch_id = str(uuid.uuid4())
            labels = [item_label(it) if item_label else str(k) for k, it in enumerate(group)]
            job.current = (f"Lô {gi + 1}/{len(groups)} · {len(group)} {unit}: "
                           + ", ".join(labels)[:80])
            await self._broadcast(job)

            async def _one(idx, it, lbl):
                if job.cancel.is_set():
                    return
                # spread the group's submits so they don't hit Flow at the same instant
                if stagger[1] > 0 and idx:
                    await asyncio.sleep(idx * random.uniform(*stagger))
                try:
                    await worker(it, batch_id)        # batch worker takes (item, batch_id)
                    job.done += 1
                except asyncio.CancelledError:
                    raise                             # cancel → stop this frame at once
                except Exception as ex:               # noqa: BLE001
                    logger.exception("job %s batch item failed: %s", job.id, lbl)
                    job.errors.append({"item": lbl, "error": str(ex)[:200]})
                # reflect THIS item's completion immediately (done/errors is polled by the UI),
                # so images appear as each finishes instead of only when the whole group does —
                # a slow retry on one frame no longer freezes the others' updates.
                await self._broadcast(job)
                await self._persist(job)

            # Run the group concurrently, but abort PROMPTLY on cancel: cancel the still-running
            # frames (which interrupts their long retry/backoff sleeps) instead of waiting the
            # whole group out — otherwise "Dừng" appears to do nothing mid-batch.
            tasks = [asyncio.create_task(_one(k, it, lbl))
                     for k, (it, lbl) in enumerate(zip(group, labels))]
            while tasks:
                _, pending = await asyncio.wait(tasks, timeout=0.4,
                                                return_when=asyncio.FIRST_COMPLETED)
                tasks = list(pending)
                if job.cancel.is_set() and tasks:
                    for t in tasks:
                        t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    break
            if gi < len(groups) - 1 and not job.cancel.is_set():
                await self._cooldown(job, throttle)   # 10s cooldown between batches
        if finalize is not None and job.status != "cancelled":
            job.current = "Hoàn tất…"
            await self._broadcast(job)
            try:
                await finalize()
            except Exception as ex:
                logger.exception("job %s finalize failed", job.id)
                job.errors.append({"item": "finalize", "error": str(ex)[:200]})
        if job.status != "cancelled":
            job.status = "error" if job.errors and not job.done else "done"
        job.current = ""
        job.message = f"{job.done}/{job.total} xong" + (
            f", {len(job.errors)} lỗi" if job.errors else "")
        await self._broadcast(job)
        await self._persist(job)
        asyncio.create_task(self._reap(job.id))

    async def _run(self, job, items, worker, throttle, item_label,
                   finalize=None, batch_size: int = 1,
                   stagger: tuple[float, float] = (0.0, 0.0),
                   unit: str = "ảnh") -> None:   # `unit` chỉ có nghĩa ở chế độ lô
        await self._broadcast(job)
        await self._persist(job)
        for i, item in enumerate(items):
            if job.cancel.is_set():
                job.status = "cancelled"
                break
            job.current = item_label(item) if item_label else ""
            await self._broadcast(job)
            try:
                await worker(item)
                job.done += 1
            except Exception as ex:
                logger.exception("job %s item %d failed", job.id, i)
                job.errors.append(
                    {"item": (item_label(item) if item_label else str(i)), "error": str(ex)[:200]})
            await self._broadcast(job)
            await self._persist(job)
            if i < len(items) - 1 and not job.cancel.is_set():
                # Interruptible throttle: wakes early if the job is cancelled.
                try:
                    await asyncio.wait_for(job.cancel.wait(), timeout=random.uniform(*throttle))
                except asyncio.TimeoutError:
                    pass
        if finalize is not None and job.status != "cancelled":
            job.current = "Hoàn tất…"
            await self._broadcast(job)
            try:
                await finalize()
            except Exception as ex:
                logger.exception("job %s finalize failed", job.id)
                job.errors.append({"item": "finalize", "error": str(ex)[:200]})
        if job.status != "cancelled":
            job.status = "error" if job.errors and not job.done else "done"
        job.current = ""
        job.message = f"{job.done}/{job.total} xong" + (
            f", {len(job.errors)} lỗi" if job.errors else "")
        await self._broadcast(job)
        await self._persist(job)
        asyncio.create_task(self._reap(job.id))

    async def _reap(self, job_id: str, delay: float = _REAP_DELAY) -> None:
        await asyncio.sleep(delay)
        self._jobs.pop(job_id, None)


_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager
