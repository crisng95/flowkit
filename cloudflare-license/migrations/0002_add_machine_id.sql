ALTER TABLE devices ADD COLUMN machine_id TEXT;

CREATE INDEX IF NOT EXISTS idx_devices_machine_id ON devices(machine_id);
