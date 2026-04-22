"""Tiny dashboard page and overview serializer for the control plane."""

from __future__ import annotations

from collections import Counter


QUEUE_METRIC_SUFFIXES = (":pending", ":lag", ":stream_depth")


def _queue_kind(key: str) -> str:
    if key == "chapters:pending":
        return "global"
    if key.endswith(":jobs"):
        return "lane"
    if key.endswith(":dead"):
        return "dead"
    return "metric"


def build_queue_sections(queue_depths: dict[str, int]) -> dict[str, list[dict]]:
    default_rows: list[dict] = []
    debug_rows: list[dict] = []

    for key, depth in queue_depths.items():
        row = {"key": key, "depth": depth, "kind": _queue_kind(key)}
        if key == "chapters:pending":
            default_rows.append(row)
            continue
        if key.endswith(QUEUE_METRIC_SUFFIXES):
            debug_rows.append(row)
            continue
        if depth > 0:
            default_rows.append(row)
        else:
            debug_rows.append(row)

    kind_order = {"global": 0, "lane": 1, "dead": 2, "metric": 3}
    default_rows.sort(key=lambda row: (kind_order[row["kind"]], row["key"]))
    debug_rows.sort(key=lambda row: (kind_order[row["kind"]], row["key"]))
    return {"default": default_rows, "debug": debug_rows}


def build_overview(*, lanes: list[dict], projects: list[dict], chapters: list[dict], jobs: list[dict], queue_depths: dict[str, int]) -> dict:
    return {
        "summary": {
            "lane_count": len(lanes),
            "project_count": len(projects),
            "chapter_count": len(chapters),
            "job_count": len(jobs),
            "lane_status_counts": dict(Counter(lane.get("status") for lane in lanes)),
            "chapter_status_counts": dict(Counter(chapter.get("status") for chapter in chapters)),
            "job_status_counts": dict(Counter(job.get("status") for job in jobs)),
        },
        "queues": queue_depths,
        "queue_sections": build_queue_sections(queue_depths),
        "lanes": lanes,
        "projects": projects,
        "chapters": chapters,
        "jobs": jobs,
    }


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FlowKit Control Dashboard</title>
  <style>
    :root { color-scheme: dark; --bg:#0b1020; --panel:#121932; --line:#26304f; --text:#e7ecff; --muted:#93a0c6; --acc:#64b5ff; --ok:#22c55e; --bad:#ef4444; --warn:#f59e0b; }
    * { box-sizing:border-box; }
    body { margin:0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:linear-gradient(180deg,#0a0f1d,#10172e); color:var(--text); }
    header { padding:18px 22px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; }
    h1 { margin:0; font-size:18px; }
    main { padding:18px; display:grid; gap:18px; }
    section { background:rgba(18,25,50,.92); border:1px solid var(--line); border-radius:14px; padding:14px; overflow:auto; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }
    .card { padding:12px; border:1px solid var(--line); border-radius:12px; background:#0f1630; }
    .label { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
    .value { font-size:28px; margin-top:6px; }
    .grid-two { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
    .section-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
    .section-head h2 { margin:0; }
    .subhead { margin:14px 0 8px; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
    table { width:100%; border-collapse:collapse; font-size:12px; }
    th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }
    th { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; position:sticky; top:0; background:#121932; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid var(--line); }
    .ok { color:var(--ok); }
    .bad { color:var(--bad); }
    .warn { color:var(--warn); }
    .muted { color:var(--muted); }
    pre { margin:0; white-space:pre-wrap; color:var(--muted); }
  </style>
</head>
<body>
  <header>
    <h1>FlowKit Control Dashboard</h1>
    <div id="last-update" class="muted">Loading...</div>
  </header>
  <main>
    <section>
      <div class="cards" id="summary-cards"></div>
    </section>
    <div class="grid-two">
      <section>
        <h2>Lanes</h2>
        <table id="lanes-table"></table>
      </section>
      <section>
        <div class="section-head">
          <h2>Queues</h2>
          <span class="muted">Default view hides zero-depth noise</span>
        </div>
        <table id="queues-table"></table>
        <details id="raw-queues-panel">
          <summary class="subhead">Raw Queue Metrics</summary>
          <table id="raw-queues-table"></table>
        </details>
      </section>
    </div>
    <section>
      <h2>Chapters</h2>
      <table id="chapters-table"></table>
    </section>
    <section>
      <h2>Recent Jobs</h2>
      <table id="jobs-table"></table>
    </section>
  </main>
  <script>
    const fmt = (v) => v === null || v === undefined || v === '' ? '—' : String(v);
    const esc = (v) => fmt(v).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
    const statusClass = (v) => ({completed:'ok', idle:'ok', running:'warn', assigned:'warn', queued:'muted', planned:'muted', failed:'bad', dead:'bad', degraded:'bad', offline:'bad'})[(v || '').toLowerCase()] || 'muted';
    function renderTable(el, columns, rows) {
      const head = '<thead><tr>' + columns.map(c => `<th>${esc(c.label)}</th>`).join('') + '</tr></thead>';
      const body = '<tbody>' + rows.map(row => '<tr>' + columns.map(c => {
        const value = c.render ? c.render(row) : row[c.key];
        return `<td>${value}</td>`;
      }).join('') + '</tr>').join('') + '</tbody>';
      el.innerHTML = head + body;
    }
    async function refresh() {
      const res = await fetch('/overview');
      const data = await res.json();
      document.getElementById('last-update').textContent = 'Updated ' + new Date().toLocaleTimeString();
      const summary = data.summary;
      document.getElementById('summary-cards').innerHTML = [
        ['Lanes', summary.lane_count],
        ['Projects', summary.project_count],
        ['Chapters', summary.chapter_count],
        ['Jobs', summary.job_count]
      ].map(([label, value]) => `<div class="card"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`).join('');
      renderTable(document.getElementById('lanes-table'), [
        { label:'Lane', key:'lane_id' },
        { label:'VM', key:'vm_name' },
        { label:'Status', render:(row) => `<span class="pill ${statusClass(row.status)}">${esc(row.status)}</span>` },
        { label:'Credits', key:'credits_last_seen' },
        { label:'Token Age', key:'token_age_seconds' },
        { label:'Current Chapter', key:'current_chapter_id' }
      ], data.lanes);
      const queueSections = data.queue_sections || { default: Object.entries(data.queues).map(([key, depth]) => ({ key, depth, kind: 'metric' })), debug: [] };
      renderTable(document.getElementById('queues-table'), [
        { label:'Queue', key:'key' },
        { label:'Kind', render:(row) => `<span class="pill ${row.kind === 'dead' ? 'bad' : row.kind === 'lane' ? 'warn' : 'muted'}">${esc(row.kind)}</span>` },
        { label:'Depth', key:'depth' }
      ], queueSections.default);
      renderTable(document.getElementById('raw-queues-table'), [
        { label:'Queue', key:'key' },
        { label:'Kind', render:(row) => `<span class="pill muted">${esc(row.kind)}</span>` },
        { label:'Depth', key:'depth' }
      ], queueSections.debug);
      renderTable(document.getElementById('chapters-table'), [
        { label:'Project', key:'project_slug' },
        { label:'#', key:'chapter_index' },
        { label:'Chapter', key:'chapter_slug' },
        { label:'Lane', key:'lane_id' },
        { label:'Status', render:(row) => `<span class="pill ${statusClass(row.status)}">${esc(row.status)}</span>` },
        { label:'Flow Project', key:'local_flow_project_id' },
        { label:'Output', key:'chapter_output_uri' }
      ], data.chapters);
      renderTable(document.getElementById('jobs-table'), [
        { label:'Job', key:'job_type' },
        { label:'Lane', key:'lane_id' },
        { label:'Chapter', key:'chapter_slug' },
        { label:'Status', render:(row) => `<span class="pill ${statusClass(row.status)}">${esc(row.status)}</span>` },
        { label:'Attempt', key:'attempt_count' },
        { label:'Priority', key:'priority' },
        { label:'Error', key:'error_text' }
      ], data.jobs);
    }
    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""
