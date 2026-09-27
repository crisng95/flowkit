# Temporary account-safety warning

> **Use Flow Kit generation only with a test or disposable Google account.**
> CAPTCHA-bearing generation is disabled by default. Explicit opt-in requires
> `FLOW_ENABLE_CAPTCHA_GENERATION=1` and should be limited to test accounts.
> Unusual-activity or extension-hijack signals create a persistent local
> generation safety hold; do not retry generation after such a signal.

After updating the extension, reload any already-open Flow tabs. Existing tabs
may still have previously injected scripts until reloaded.

For the hold behavior, manual-UI distinction, and recovery limits, see the
[main account-safety guide](../docs/ACCOUNT_SAFETY.md).
