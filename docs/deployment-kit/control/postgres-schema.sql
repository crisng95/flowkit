-- FlowKit control-plane schema
-- PostgreSQL 16+

begin;

create extension if not exists pgcrypto;

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'lane_status_enum') then
    create type lane_status_enum as enum (
      'provisioning',
      'idle',
      'busy',
      'paused',
      'degraded',
      'offline'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'project_status_enum') then
    create type project_status_enum as enum (
      'draft',
      'queued',
      'in_progress',
      'blocked',
      'failed',
      'completed',
      'archived'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'chapter_status_enum') then
    create type chapter_status_enum as enum (
      'planned',
      'queued',
      'assigned',
      'running',
      'review_required',
      'failed',
      'completed'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'job_type_enum') then
    create type job_type_enum as enum (
      'CREATE_PROJECT',
      'CREATE_ENTITIES',
      'CREATE_VIDEO',
      'CREATE_SCENES',
      'GEN_REFS',
      'GEN_IMAGES',
      'GEN_VIDEOS',
      'UPSCALE',
      'CONCAT_CHAPTER',
      'UPLOAD_ARTIFACTS',
      'ASSEMBLE_MASTER'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'job_status_enum') then
    create type job_status_enum as enum (
      'queued',
      'claimed',
      'running',
      'retryable',
      'dead',
      'failed',
      'completed',
      'cancelled'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'artifact_type_enum') then
    create type artifact_type_enum as enum (
      'ref_image',
      'scene_image',
      'scene_video',
      'upscale_video',
      'chapter_final',
      'master_final',
      'thumbnail',
      'manifest',
      'log_bundle'
    );
  end if;
end $$;

create table if not exists lanes (
  id uuid primary key default gen_random_uuid(),
  lane_id text not null unique,
  vm_name text not null unique,
  worker_hostname text not null,
  status lane_status_enum not null default 'provisioning',
  account_alias text not null unique,
  queue_key text not null unique,
  dead_letter_key text not null unique,
  chrome_profile_dir text not null,
  runtime_dir text not null,
  output_dir text not null,
  current_chapter_id uuid null,
  credits_last_seen integer null,
  tier_last_seen text null,
  token_age_seconds integer null,
  last_heartbeat_at timestamptz null,
  last_error_text text null,
  lane_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  project_slug text not null unique,
  source_title text not null,
  source_brief text null,
  target_duration_seconds integer not null check (target_duration_seconds > 0),
  status project_status_enum not null default 'draft',
  material_id text not null default 'realistic',
  target_scene_count integer null,
  target_chapter_count integer null,
  master_output_uri text null,
  project_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists chapters (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  chapter_index integer not null check (chapter_index >= 1),
  chapter_slug text not null,
  title text not null,
  synopsis text null,
  target_duration_seconds integer not null check (target_duration_seconds > 0),
  target_scene_count integer null,
  assigned_lane_id uuid null references lanes(id) on delete set null,
  status chapter_status_enum not null default 'planned',
  local_flow_project_id text null,
  chapter_output_uri text null,
  chapter_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, chapter_index),
  unique (project_id, chapter_slug)
);

create table if not exists jobs (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references chapters(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  lane_id uuid null references lanes(id) on delete set null,
  job_type job_type_enum not null,
  status job_status_enum not null default 'queued',
  attempt_count integer not null default 0 check (attempt_count >= 0),
  max_attempts integer not null default 3 check (max_attempts >= 1),
  priority integer not null default 100,
  idempotency_key text not null,
  queue_message_id text null,
  trace_id text null,
  payload_json jsonb not null,
  result_json jsonb null,
  error_text text null,
  created_at timestamptz not null default now(),
  claimed_at timestamptz null,
  started_at timestamptz null,
  finished_at timestamptz null,
  updated_at timestamptz not null default now(),
  unique (idempotency_key)
);

create table if not exists artifacts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  chapter_id uuid null references chapters(id) on delete cascade,
  lane_id uuid null references lanes(id) on delete set null,
  artifact_type artifact_type_enum not null,
  local_path text null,
  storage_uri text not null,
  checksum_sha256 text null,
  size_bytes bigint null check (size_bytes is null or size_bytes >= 0),
  duration_seconds numeric(12,3) null,
  width integer null,
  height integer null,
  artifact_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists lane_heartbeats (
  lane_id uuid primary key references lanes(id) on delete cascade,
  heartbeat_at timestamptz not null,
  active_job_id uuid null references jobs(id) on delete set null,
  active_chapter_id uuid null references chapters(id) on delete set null,
  stats_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists scheduler_leases (
  lease_name text primary key,
  holder_id text not null,
  acquired_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create index if not exists idx_lanes_status on lanes(status);
create index if not exists idx_lanes_heartbeat on lanes(last_heartbeat_at desc nulls last);

create index if not exists idx_projects_status on projects(status);
create index if not exists idx_projects_created_at on projects(created_at desc);

create index if not exists idx_chapters_project on chapters(project_id, chapter_index);
create index if not exists idx_chapters_lane_status on chapters(assigned_lane_id, status);
create index if not exists idx_chapters_status on chapters(status);

create index if not exists idx_jobs_lane_status_priority on jobs(lane_id, status, priority desc, created_at asc);
create index if not exists idx_jobs_chapter_type on jobs(chapter_id, job_type, status);
create index if not exists idx_jobs_project_status on jobs(project_id, status);
create index if not exists idx_jobs_created_at on jobs(created_at desc);

create index if not exists idx_artifacts_project_type on artifacts(project_id, artifact_type, created_at desc);
create index if not exists idx_artifacts_chapter_type on artifacts(chapter_id, artifact_type, created_at desc);
create index if not exists idx_artifacts_storage_uri on artifacts(storage_uri);

drop trigger if exists trg_lanes_updated_at on lanes;
create trigger trg_lanes_updated_at
before update on lanes
for each row execute function set_updated_at();

drop trigger if exists trg_projects_updated_at on projects;
create trigger trg_projects_updated_at
before update on projects
for each row execute function set_updated_at();

drop trigger if exists trg_chapters_updated_at on chapters;
create trigger trg_chapters_updated_at
before update on chapters
for each row execute function set_updated_at();

drop trigger if exists trg_jobs_updated_at on jobs;
create trigger trg_jobs_updated_at
before update on jobs
for each row execute function set_updated_at();

drop trigger if exists trg_lane_heartbeats_updated_at on lane_heartbeats;
create trigger trg_lane_heartbeats_updated_at
before update on lane_heartbeats
for each row execute function set_updated_at();

commit;
