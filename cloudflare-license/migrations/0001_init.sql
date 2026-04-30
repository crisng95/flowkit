CREATE TABLE IF NOT EXISTS devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  machine_hash TEXT NOT NULL UNIQUE,
  machine_hint TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  last_app_version TEXT,
  last_platform TEXT
);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);

CREATE TABLE IF NOT EXISTS licenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  machine_hash TEXT NOT NULL,
  plan_code TEXT NOT NULL,
  status TEXT NOT NULL,
  activated_at TEXT NOT NULL,
  expires_at TEXT,
  created_by TEXT NOT NULL DEFAULT 'admin',
  note TEXT,
  revoked_at TEXT,
  revoked_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_licenses_machine_hash ON licenses(machine_hash);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
CREATE INDEX IF NOT EXISTS idx_licenses_activated_at ON licenses(activated_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  machine_hash TEXT,
  detail_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
