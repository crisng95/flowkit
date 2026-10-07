# ADR-0002 — Desktop Process Topology

**Status:** PROPOSED  
**Decision:** prefer Electron Renderer + Preload + Main Security Broker + `utilityProcess` Production Backend.

## Why

It preserves desktop simplicity while separating:
- untrusted renderer;
- privileged OS/security APIs;
- heavy/long-running production backend.

It avoids a localhost service and its port/auth/firewall exposure for V1.

## Rejected
- Main-only backend: too much privileged/heavy work in Electron main failure domain.
- localhost service: useful later, but higher ops/security burden now.

## Revisit
If headless/background-with-UI-closed, non-Node backend, or multi-client access becomes MUST.
