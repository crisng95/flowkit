# LIVE_PROVIDER_ADAPTER_CONTRACT.md

A live-provider fault harness must wrap a **test account/project** and implement:

```python
class LiveProviderAdapter:
    def prepare(self, local_submission_key: str) -> dict: ...
    def submit(self, prepared: dict, fault_mode: str) -> dict: ...
    def reconcile(self, prepared: dict, known_remote_handle: str | None) -> dict: ...
    def poll(self, remote_handle: str) -> dict: ...
    def list_recent(self, since_iso: str) -> list[dict]: ...
    def billing_observation(self, prepared: dict) -> dict: ...
```

`fault_mode` minimum:
- `NONE`
- `FAIL_BEFORE_TRANSPORT`
- `DROP_RESPONSE_AFTER_DISPATCH`
- `CRASH_AFTER_HANDLE_BEFORE_LOCAL_COMMIT`

The adapter must document how `DROP_RESPONSE_AFTER_DISPATCH` is implemented.
A generic timeout exception is not enough unless the request was actually dispatched.

Return shapes:

```text
submit:
  ACCEPTED(handle)
  PROVEN_NOT_SUBMITTED
  AMBIGUOUS
  FINAL_FAILURE

reconcile:
  RECOVERED(handle)
  PROVEN_ABSENT
  STILL_AMBIGUOUS
  EXPIRED_UNKNOWN
```

Do not test with production customer data.
