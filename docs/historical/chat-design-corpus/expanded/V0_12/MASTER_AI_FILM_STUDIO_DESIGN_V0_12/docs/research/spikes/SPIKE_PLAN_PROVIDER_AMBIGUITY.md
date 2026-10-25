# SPIKE_PLAN_PROVIDER_AMBIGUITY.md
# Design Spike Plan — Provider Ambiguous Timeout / Reconciliation

**Status:** REQUIRED BEFORE L6  
**Code classification:** DESIGN SPIKE ONLY

## Question

Can a provider adapter prevent duplicate paid jobs when the network fails after remote acceptance but before local confirmation?

## Required adapter capabilities

```text
submit(request, idempotency_key?)
reconcile(local_request_identity, provider_job_id?, provider_request_id?)
poll(remote_job)
```

## Injection points

1. fail before bytes sent;
2. fail after request body sent;
3. fail after provider accepted but before response read;
4. fail after remote ID returned but before DB commit;
5. restart during reconciliation.

## Expected behavior

```text
1 → safe retry
2/3 → UNKNOWN_REMOTE_STATE → reconcile first
4 → reconciliation recovers remote identity where provider supports
5 → persistent recovery resumes
```

## Evidence

For each real V1 provider:
- API supports idempotency? yes/no;
- search/list jobs available? yes/no;
- client request ID echoed? yes/no;
- duplicate side-effect risk;
- exact fallback policy.

Do not claim generic duplicate prevention until each provider path is verified.
