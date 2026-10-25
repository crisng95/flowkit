# Windows Persistence / Update Design Spike V2

Run 1 exposed that direct 12-connection writes are not acceptable under the old harness.

V2 separates:

```text
A. RAW MULTI-WRITER
   adversarial characterization
   exact exception class/message captured

B. SINGLE-WRITER QUEUE
   intended V1 topology
   12 producers -> one DB write owner
   production acceptance lane
```

Recommended command:

```powershell
python .\windows_persistence_spike_v2.py --out .\spike-output-v2
```

If `python` is unavailable:

```powershell
py .\windows_persistence_spike_v2.py --out .\spike-output-v2
```

Or use:

```powershell
.\run-windows-spike-v2.ps1
```

Send back:

```text
spike-output-v2\windows_persistence_spike_results_v2.json
```

Production acceptance requires:
- 3000/3000 committed in `single_writer_queue`;
- 0 writer errors;
- 0 producer errors;
- integrity `ok`;
- crash/migration/backup/schema tests pass.

Raw multi-writer errors are diagnostic, not the production acceptance lane.
