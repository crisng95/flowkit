# Temporary Flow account-safety guidance

This notice is temporary and should remain visible while the cause and recovery
status of the reported access problems are unresolved.

## Implemented FlowKit safeguards

- CAPTCHA-bearing generation requests are **disabled by default**. The opt-in
  is `FLOW_ENABLE_CAPTCHA_GENERATION=1`; use it only with a test/disposable
  account. Without opt-in, FlowKit rejects the request before sending it.
- An unusual-activity or extension-hijack signal latches
  `flow_generation_safety_hold.json` (or the configured
  `FLOW_GENERATION_SAFETY_FILE`). The hold blocks later CAPTCHA-bearing
  generation and survives agent restarts. FlowKit writes an in-flight marker
  **before** requesting a token; an interrupted request or failed hold write
  leaves that marker behind and the next process treats it as a hold. If the
  file cannot be read, FlowKit also treats the hold as active.
- `/api/flow/clear-hijack` **cannot clear an active safety hold**; it returns
  HTTP 409. It only clears a legacy in-memory timer when no persistent hold is
  active. Do not describe it as a hold reset.
- A generic CAPTCHA/reCAPTCHA or transport error marks that request failed,
  latches the persistent hold, and is not automatically retried. A successful
  request clears only its own in-flight marker.
- The safety gate applies to CAPTCHA-bearing generation. Non-generation
  metadata and polling RPCs are outside that generation gate; this does not
  establish whether the manual Flow UI works for the account.

`FLOW_MANUAL_UI_STATUS` is operator-reported metadata (`unknown` by default,
or `works` / `blocked`); FlowKit does not infer manual UI status from an
extension error. FlowKit's internal timers and holds are safety controls, not
Google account recovery cooldowns.

## Before testing

- Use a test or disposable Google account. Do not experiment with an account
  whose access you cannot risk losing.
- Stop all automated Flow generation at the first unusual-activity response,
  suspected account/session hijack, unexpected sign-in or security prompt, or
  other unexpected account-security signal. Do not continue by retrying through
  FlowKit or another automation path.

## Describe the affected layer accurately

- **Extension/agent-only failure:** the extension, local agent, or an automated
  request reports an error. This does not by itself show that Flow's manual
  website is blocked for the account.
- **Manual Flow UI blocked:** the account cannot use the Flow website manually,
  independently of an extension request. Record this as a separate observation
  only when it has actually been reported or observed. Do not repeatedly retry
  generation to establish the distinction.
- **Unknown:** if the available report does not say whether manual Flow access
  is blocked, preserve that uncertainty. Do not label an extension error as an
  account block.

Reports that two Google accounts became unable to use the **manual Flow UI**
after FlowKit testing are temporally associated reports. That correlation does
not prove FlowKit caused the blocks. The related upstream report is public in
[FlowKit issue #67](https://github.com/crisng95/flowkit/issues/67).

## Recovery status

No Google account recovery method or recovery cooldown has been verified for
these reports. The FlowKit safety hold is persistent application state, not a
Google recovery measure. Do not say that clearing cookies, changing IP address
or network, or waiting a fixed time will restore account access. Do not suggest
that a CAPTCHA retry, slower cadence, or switching accounts repairs an affected
account.

### Local hold reset

There is deliberately **no API reset** for the persistent safety hold.
`/api/flow/clear-hijack` cannot clear it. Only after an operator has completed a
manual review, is using a disposable/test account, and has independently
verified that the manual Flow UI works may the operator explicitly remove or
rename the local hold file (`flow_generation_safety_hold.json`, or the path set
by `FLOW_GENERATION_SAFETY_FILE`). The operator must then restart FlowKit with
`FLOW_ENABLE_CAPTCHA_GENERATION=1` to opt in to CAPTCHA-bearing generation.

This procedure clears only FlowKit's local hold. It does not clear Google's
account state and cannot restore Google access. If any prerequisite is unknown
or unmet, leave the hold in place.

Stop automated requests and preserve the observed error, approximate time,
FlowKit/extension version, and whether manual Flow access was reported blocked.
Never include passwords, cookies, access tokens, or other account secrets in a
bug report. For account access, follow Google's official account/help process;
FlowKit documentation cannot restore or verify account access.

## Reporting language

Prefer: “Two accounts were reported unable to use the manual Flow UI after
FlowKit testing; timing is correlated, and causation and recovery are
unverified.” Avoid stating or implying that FlowKit caused a Google account
block, that the extension alone proves a manual UI block, or that a particular
remedy or wait period restores access.
