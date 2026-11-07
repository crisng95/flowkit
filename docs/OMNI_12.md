# Optional Omni 1.2 trusted-UI transport (complements PR #85)

This adds an opt-in, signed-in Chrome UI path for Omni Flash 1.2
text-to-video requests. It is complementary to the captured
macaron_cookie wire-key integration in [PR #85](https://github.com/crisng95/flowkit/pull/85).
Once PR #85 is merged, clients continue to use the same
/api/flow/generate-video-omni-text API with omni_version = "1.2".

## Why offer a browser UI path?

The Flow frontend owns the model menu, duration slider and reCAPTCHA
evaluation. A direct extension batch request can be rejected by Google's
account risk controls even when the normal signed-in UI works.
This optional backend navigates the *existing dedicated Flow Chrome session*
and clicks Generate once. It captures the response before Flow navigates.

The model aliases and durations are adapted from
[GTAI-1/flow-mcp #29](https://github.com/GTAI-1/flow-mcp/pull/29) and
[#30](https://github.com/GTAI-1/flow-mcp/pull/30).
The optional transport is for the classic Flow composer. Agent-first Flow
support from #29 is not included and fails explicitly without charging.

## Setup

1. Install the optional Python Playwright package. This uses an existing
   Chrome browser, so it does not download Playwright Chromium.
2. Connect a **dedicated** local Chrome with a signed-in Flow profile and CDP
   on a free localhost port. Do not reuse another app's Chrome.
3. Configure FLOW_OMNI12_CDP_URL=http://127.0.0.1:9224 (change the port as
   appropriate) and FLOW_OMNI12_MAX_CREDITS=20 (default).

If FLOW_OMNI12_CDP_URL is unset, **nothing changes**: PR #85 continues to
submit through the existing extension batch RPC. The FlowKit extension must
remain connected for account and project bookkeeping.

The optional UI path recognizes Omni 1.2 text-to-video model keys
macaron_cookie_t2v_<N>s[_360p] for 3–15 integer seconds. Other Omni
modes continue through the regular extension transport.

The UI checks the 360p/720p resolution, 3–15-second slider and x1 variants,
then reads Flow's *live* credit quote before clicking Generate. A quote
over FLOW_OMNI12_MAX_CREDITS or over the official 1.2 rate is refused, as
is an unrecognized quote locale. Official posted rates are 1 credit/sec
at 360p or 3 credits/sec at 720p through 10s; additional seconds 11–15
are twice as expensive.

There are **no automatic retries** of ambiguous requests. This code does
not bypass CAPTCHA, quotas or account risk controls. If Flow flags unusual
activity, stop submitting until the account is permitted to generate again.

### Validation

- Unit tests cover model matching, price tiers, duration parsing and
  exactly-once response forwarding.
- The classic Flow model picker, 3s duration slider and 3-credit 360p
  quote were checked against a signed-in session without submitting.
- A real Omni 1.2 generation was attempted on 2026-11-07, but Flow's
  unusual-activity warning prevented successful end-to-end validation.
  Do not mark this experimental transport as live-verified.

Google references: https://support.google.com/flow/answer/16352836
and https://support.google.com/flow/answer/16526234
