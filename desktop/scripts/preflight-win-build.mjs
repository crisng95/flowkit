#!/usr/bin/env node

const allowCross = process.env.FLOWKIT_ALLOW_CROSS_WIN === "1";

if (process.platform !== "win32" && !allowCross) {
  console.error(
    "[dist:win] Build Windows trên non-Windows bị chặn để tránh package lỗi (agent binary sai định dạng).",
  );
  console.error(
    "[dist:win] Hãy build trên Windows runner (GitHub Actions build-windows) hoặc máy Windows local.",
  );
  process.exit(1);
}

