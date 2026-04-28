begin;

insert into lanes (
  lane_id,
  vm_name,
  worker_hostname,
  status,
  account_alias,
  queue_key,
  dead_letter_key,
  chrome_profile_dir,
  runtime_dir,
  output_dir
)
values
  ('lane-01', 'fk-w01', 'fk-w01', 'idle', 'flow-account-01', 'lane:01:jobs', 'lane:01:dead', '/srv/flowkit/lane-01/chrome-profile', '/srv/flowkit/lane-01/runtime', '/srv/flowkit/lane-01/runtime/output'),
  ('lane-02', 'fk-w02', 'fk-w02', 'idle', 'flow-account-02', 'lane:02:jobs', 'lane:02:dead', '/srv/flowkit/lane-02/chrome-profile', '/srv/flowkit/lane-02/runtime', '/srv/flowkit/lane-02/runtime/output'),
  ('lane-03', 'fk-w03', 'fk-w03', 'idle', 'flow-account-03', 'lane:03:jobs', 'lane:03:dead', '/srv/flowkit/lane-03/chrome-profile', '/srv/flowkit/lane-03/runtime', '/srv/flowkit/lane-03/runtime/output'),
  ('lane-04', 'fk-w04', 'fk-w04', 'idle', 'flow-account-04', 'lane:04:jobs', 'lane:04:dead', '/srv/flowkit/lane-04/chrome-profile', '/srv/flowkit/lane-04/runtime', '/srv/flowkit/lane-04/runtime/output'),
  ('lane-05', 'fk-w05', 'fk-w05', 'idle', 'flow-account-05', 'lane:05:jobs', 'lane:05:dead', '/srv/flowkit/lane-05/chrome-profile', '/srv/flowkit/lane-05/runtime', '/srv/flowkit/lane-05/runtime/output'),
  ('lane-06', 'fk-w06', 'fk-w06', 'idle', 'flow-account-06', 'lane:06:jobs', 'lane:06:dead', '/srv/flowkit/lane-06/chrome-profile', '/srv/flowkit/lane-06/runtime', '/srv/flowkit/lane-06/runtime/output'),
  ('lane-07', 'fk-w07', 'fk-w07', 'idle', 'flow-account-07', 'lane:07:jobs', 'lane:07:dead', '/srv/flowkit/lane-07/chrome-profile', '/srv/flowkit/lane-07/runtime', '/srv/flowkit/lane-07/runtime/output'),
  ('lane-08', 'fk-w08', 'fk-w08', 'idle', 'flow-account-08', 'lane:08:jobs', 'lane:08:dead', '/srv/flowkit/lane-08/chrome-profile', '/srv/flowkit/lane-08/runtime', '/srv/flowkit/lane-08/runtime/output'),
  ('lane-09', 'fk-w09', 'fk-w09', 'idle', 'flow-account-09', 'lane:09:jobs', 'lane:09:dead', '/srv/flowkit/lane-09/chrome-profile', '/srv/flowkit/lane-09/runtime', '/srv/flowkit/lane-09/runtime/output'),
  ('lane-10', 'fk-w10', 'fk-w10', 'idle', 'flow-account-10', 'lane:10:jobs', 'lane:10:dead', '/srv/flowkit/lane-10/chrome-profile', '/srv/flowkit/lane-10/runtime', '/srv/flowkit/lane-10/runtime/output')
on conflict (lane_id) do update
set vm_name = excluded.vm_name,
    worker_hostname = excluded.worker_hostname,
    account_alias = excluded.account_alias,
    queue_key = excluded.queue_key,
    dead_letter_key = excluded.dead_letter_key,
    chrome_profile_dir = excluded.chrome_profile_dir,
    runtime_dir = excluded.runtime_dir,
    output_dir = excluded.output_dir;

commit;
