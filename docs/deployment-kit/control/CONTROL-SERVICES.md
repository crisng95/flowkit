# Control VM Services

## Purpose

The control VM owns orchestration state and assembly only.

It does not hold a Google Flow browser session.

## Services

### Postgres

Stores:

- projects
- chapters
- lane health
- jobs
- artifact records

### Redis

Stores:

- chapter backlog
- per-lane queues
- retry/dead-letter queues
- ephemeral scheduler state

### Control API

Recommended future endpoints:

- `POST /projects`
- `POST /projects/{id}/chapters/split`
- `POST /chapters/{id}/assign`
- `POST /chapters/{id}/retry`
- `GET /lanes`
- `GET /chapters/{id}`
- `GET /artifacts/{id}`

### Scheduler

Responsibilities:

- consume `chapters:pending`
- choose idle lane
- enqueue jobs into `lane:XX:jobs`
- requeue failed chapters by policy

### Assembler

Responsibilities:

- wait for all chapter finals
- fetch chapter finals from object storage
- normalize final chapter outputs
- concat master long-form video
