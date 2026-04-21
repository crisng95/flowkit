# FlowKit Deployment Kit

This folder contains a practical deployment starter kit for the 10-lane blueprint.

Use it to stand up:

- 1 control VM
- 10 worker VMs
- 1 isolated FlowKit lane per worker

Contents:

- `control/`
  - control-plane docker-compose
  - env template
  - Postgres schema
  - Redis job contract
  - service descriptions
- `worker/`
  - lane directory layout
  - systemd units
  - lane env template
  - Chrome startup scripts
  - artifact upload script skeleton
- `lane-env/`
  - ready-to-copy env files for lane-01 to lane-10
- `two-lane-same-vm-hth2-box-handoff.md`
  - current same-VM lab state for `lane-01` + `lane-02` on `hth2-box`

Recommended order:

1. Read [10-lane-production-blueprint.md](/F:/vm201 Coolify/flowkit/docs/10-lane-production-blueprint.md)
2. Bring up `control/`
3. Bring up `worker/` on one test worker
4. Validate one lane end to end
5. Replicate for lanes 02-10

## Same-VM Lab Path

The deployment kit now also documents a non-production lab path for running a second isolated lane on the same VM.

Current lab shape on `hth2-box`:

- `lane-01` stays on `8100/9222`
- `lane-02` uses `8110/9232`
- lane-02 worker health uses `18182`
- lane-02 uses its own runtime root, Chrome profile, and unpacked extension bundle

Supporting pieces:

- worker bootstrap now supports custom deploy root and per-lane port overrides
- extension bundles can be rendered with lane-specific endpoints using:
  - `worker/scripts/render-extension-bundle.py`

Use these docs for the lab path:

1. [worker/BOOTSTRAP-RUNBOOK.md](/F:/vm201 Coolify/flowkit/docs/deployment-kit/worker/BOOTSTRAP-RUNBOOK.md)
2. [two-lane-same-vm-hth2-box-handoff.md](/F:/vm201 Coolify/flowkit/docs/deployment-kit/two-lane-same-vm-hth2-box-handoff.md)

Important:

- production recommendation is still `1 lane per worker VM`
- same-VM dual-lane is only for lab validation and debugging
