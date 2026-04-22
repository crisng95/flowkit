"""FastAPI control-plane stub for project/chapter orchestration."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .assembler import assemble_project
from .config import settings
from .dashboard import build_overview, dashboard_html
from .planning import build_chapter_rows, slugify
from .storage import (
    create_chapters,
    create_project,
    enqueue_pending_chapter,
    get_project,
    list_chapters,
    list_jobs,
    list_lanes,
    list_projects,
    ping_all,
    queue_depths,
)


class ProjectCreate(BaseModel):
    source_title: str
    source_brief: str | None = None
    target_duration_seconds: int = Field(gt=0)
    material_id: str = "realistic"
    chapter_count: int = Field(default=10, ge=1, le=20)


app = FastAPI(title="FlowKit Control API", version="0.1.0")


@app.get("/health")
def health():
    deps = ping_all()
    return {"status": "ok" if all(deps.values()) else "degraded", **deps}


@app.get("/lanes")
def lanes():
    return list_lanes()


@app.get("/projects")
def projects():
    return list_projects()


@app.get("/chapters")
def chapters():
    return list_chapters()


@app.get("/jobs")
def jobs():
    return list_jobs()


@app.get("/overview")
def overview():
    return build_overview(
        lanes=list_lanes(),
        projects=list_projects(),
        chapters=list_chapters(),
        jobs=list_jobs(),
        queue_depths=queue_depths(),
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return dashboard_html()


@app.post("/projects")
def projects_create(body: ProjectCreate):
    project = create_project(
        source_title=body.source_title,
        source_brief=body.source_brief,
        target_duration_seconds=body.target_duration_seconds,
        material_id=body.material_id,
        chapter_count=body.chapter_count,
    )
    slug = slugify(body.source_title)
    chapter_rows = build_chapter_rows(slug, body.target_duration_seconds, body.chapter_count)
    chapters = create_chapters(project["id"], chapter_rows)
    enqueued = [
        enqueue_pending_chapter(
            chapter_id=chapter["id"],
            project_id=project["id"],
            chapter_index=chapter["chapter_index"],
            target_duration_seconds=chapter["target_duration_seconds"],
            target_scene_count=chapter["target_scene_count"],
            material_id=body.material_id,
        )
        for chapter in chapters
    ]
    return {"project": project, "chapters": chapters, "stream_ids": enqueued}


@app.post("/projects/{project_id}/chapters/split")
def split_existing_project(project_id: str):
    for project in list_projects():
        if project["id"] == project_id:
            chapter_count = project.get("target_chapter_count") or 10
            slug = project["project_slug"]
            rows = build_chapter_rows(slug, project["target_duration_seconds"], chapter_count)
            chapters = create_chapters(project_id, rows)
            return {"project_id": project_id, "chapters": chapters}
    raise HTTPException(404, "Project not found")


@app.post("/projects/{project_id}/assemble-master")
def assemble_master(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return assemble_project(project_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.control_api_bind, port=settings.control_api_port)
