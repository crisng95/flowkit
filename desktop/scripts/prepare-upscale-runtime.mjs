#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { createWriteStream, existsSync } from "node:fs";
import { access, chmod, copyFile, cp, mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const desktopRoot = resolve(__dirname, "..");
const runtimeBaseRoot = join(desktopRoot, "resources", "agent", "third_party");
const projectRuntimeBaseRoot = resolve(desktopRoot, "..", "third_party");
const runtimeIndexManifestPath = join(runtimeBaseRoot, "runtime-manifest.json");

const args = process.argv.slice(2);
const force = args.includes("--force") || process.env.FLOWKIT_UPSCALE_FORCE === "1";
const downloadTimeoutMs = Math.max(
  60_000,
  Number.parseInt(process.env.FLOWKIT_DOWNLOAD_TIMEOUT_MS || "", 10) || 20 * 60 * 1000,
);
const explicitPlatformArg = args.find((arg) => arg.startsWith("--platform="));
const explicitPlatform = explicitPlatformArg ? explicitPlatformArg.slice("--platform=".length).trim() : "";

const RUNTIME_SPECS = {
  win32: {
    ffmpegZipUrls: [
      "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
      "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    ],
    realesrganZipUrls: [
      "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.3.0/realesrgan-ncnn-windows.zip",
      "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",
    ],
    ffmpegBin: "ffmpeg.exe",
    ffprobeBin: "ffprobe.exe",
    realesrganBin: "realesrgan-ncnn-vulkan.exe",
  },
  darwin: {
    ffmpegZipUrls: ["https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"],
    ffprobeZipUrls: ["https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"],
    realesrganZipUrls: [
      "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.3.0/realesrgan-ncnn-macos.zip",
      "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip",
    ],
    ffmpegBin: "ffmpeg",
    ffprobeBin: "ffprobe",
    realesrganBin: "realesrgan-ncnn-vulkan",
  },
};

function normalizePlatform(raw) {
  const value = String(raw || "").trim().toLowerCase();
  if (!value) return "";
  if (["win", "win32", "windows", "win64"].includes(value)) return "win32";
  if (["darwin", "mac", "macos", "osx", "os-x"].includes(value)) return "darwin";
  return value;
}

function resolveTargetPlatforms(raw) {
  const supported = Object.keys(RUNTIME_SPECS);
  const fallback = normalizePlatform(process.platform);
  const text = String(raw || "").trim().toLowerCase();
  if (!text) return [fallback];
  if (text === "all") return supported;
  const tokens = text
    .split(",")
    .map((item) => normalizePlatform(item))
    .filter(Boolean);
  const deduped = Array.from(new Set(tokens));
  if (!deduped.length) return [fallback];
  const unsupported = deduped.filter((platform) => !supported.includes(platform));
  if (unsupported.length) {
    throw new Error(
      `Unsupported platform(s): ${unsupported.join(", ")}. Supported: ${supported.join(", ")} or "all".`,
    );
  }
  return deduped;
}

const targetPlatforms = resolveTargetPlatforms(
  explicitPlatform || process.env.FLOWKIT_UPSCALE_PLATFORM || process.platform,
);

function log(message) {
  process.stdout.write(`[prepare-upscale-runtime] ${message}\n`);
}

async function ensureDir(path) {
  await mkdir(path, { recursive: true });
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function hasRuntimeAtRoot(root, spec) {
  const ffmpegTarget = join(root, "ffmpeg", spec.ffmpegBin);
  const ffprobeTarget = join(root, "ffmpeg", spec.ffprobeBin);
  const realesrganTarget = join(root, "realesrgan", spec.realesrganBin);
  const modelParamTarget = join(root, "realesrgan", "models", "realesrgan-x4plus.param");
  const modelBinTarget = join(root, "realesrgan", "models", "realesrgan-x4plus.bin");
  return (
    (await pathExists(ffmpegTarget)) &&
    (await pathExists(ffprobeTarget)) &&
    (await pathExists(realesrganTarget)) &&
    (await pathExists(modelParamTarget)) &&
    (await pathExists(modelBinTarget))
  );
}

async function downloadFile(url, destPath) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), downloadTimeoutMs);
  try {
    const response = await fetch(url, { redirect: "follow", signal: controller.signal });
    if (!response.ok || !response.body) {
      throw new Error(`Download failed (${response.status}) from ${url}`);
    }
    const out = createWriteStream(destPath);
    await pipeline(response.body, out);
  } finally {
    clearTimeout(timer);
  }
}

async function downloadFirstAvailable(urls, destPath, label) {
  if (!urls?.length) throw new Error(`No download URLs configured for ${label}`);
  let lastError = "";
  for (const url of urls) {
    try {
      log(`Downloading ${label} from ${url}`);
      await downloadFile(url, destPath);
      return url;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
      log(`Download failed for ${label} (${url}): ${lastError}`);
    }
  }
  throw new Error(`All mirrors failed for ${label}: ${lastError}`);
}

function runCommand(command, commandArgs) {
  const result = spawnSync(command, commandArgs, { stdio: "inherit" });
  if (result.status !== 0) {
    throw new Error(`Command failed: ${command} ${commandArgs.join(" ")}`);
  }
}

function extractZip(zipPath, outputDir) {
  if (process.platform === "win32") {
    const escapedZip = zipPath.replace(/'/g, "''");
    const escapedOut = outputDir.replace(/'/g, "''");
    runCommand("powershell.exe", [
      "-NoLogo",
      "-NoProfile",
      "-Command",
      `Expand-Archive -Path '${escapedZip}' -DestinationPath '${escapedOut}' -Force`,
    ]);
    return;
  }
  runCommand("unzip", ["-o", zipPath, "-d", outputDir]);
}

async function findFile(rootDir, fileName) {
  const stack = [rootDir];
  while (stack.length) {
    const current = stack.pop();
    const entries = await readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
        continue;
      }
      if (entry.isFile() && entry.name.toLowerCase() === fileName.toLowerCase()) {
        return full;
      }
    }
  }
  return null;
}

async function findModels(rootDir) {
  const found = [];
  const stack = [rootDir];
  while (stack.length) {
    const current = stack.pop();
    const entries = await readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
        continue;
      }
      if (!entry.isFile()) continue;
      if (!entry.name.endsWith(".param") && !entry.name.endsWith(".bin")) continue;
      found.push(full);
    }
  }
  return found;
}

async function findDynamicLibs(rootDir) {
  const found = [];
  const stack = [rootDir];
  while (stack.length) {
    const current = stack.pop();
    const entries = await readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
        continue;
      }
      if (!entry.isFile()) continue;
      const lower = entry.name.toLowerCase();
      if (
        lower.endsWith(".dylib") ||
        lower.endsWith(".dll") ||
        lower.endsWith(".so") ||
        lower.includes(".so.")
      ) {
        found.push(full);
      }
    }
  }
  return found;
}

async function copyExecutable(src, dest, platform) {
  await copyFile(src, dest);
  if (platform !== "win32") {
    await chmod(dest, 0o755);
  }
}

function getRuntimePathsForPlatform(platform) {
  const runtimeRoot = join(runtimeBaseRoot, platform);
  const ffmpegRoot = join(runtimeRoot, "ffmpeg");
  const realesrganRoot = join(runtimeRoot, "realesrgan");
  const realesrganModelsRoot = join(realesrganRoot, "models");
  const manifestPath = join(runtimeRoot, "runtime-manifest.json");
  return {
    runtimeRoot,
    ffmpegRoot,
    realesrganRoot,
    realesrganModelsRoot,
    manifestPath,
  };
}

async function readManifest(path) {
  try {
    const raw = await readFile(path, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function writeManifest(path, manifest) {
  await ensureDir(dirname(path));
  await writeFile(path, JSON.stringify(manifest, null, 2), "utf-8");
}

async function mirrorRuntimeToProjectRoot(runtimeRoot, targetPlatform) {
  const platformRoot = join(projectRuntimeBaseRoot, targetPlatform);
  await ensureDir(projectRuntimeBaseRoot);
  await rm(platformRoot, { recursive: true, force: true });
  await cp(runtimeRoot, platformRoot, { recursive: true, force: true });
  log(`Mirrored runtime (${targetPlatform}) to ${platformRoot}`);
}

async function cleanupLegacyFlatRuntime(baseRoot, targetPlatform, spec) {
  const platformRoot = join(baseRoot, targetPlatform);
  if (!(await hasRuntimeAtRoot(platformRoot, spec))) {
    return;
  }
  const legacyFfmpeg = join(baseRoot, "ffmpeg");
  const legacyRealesrgan = join(baseRoot, "realesrgan");
  if (await pathExists(legacyFfmpeg)) {
    await rm(legacyFfmpeg, { recursive: true, force: true });
  }
  if (await pathExists(legacyRealesrgan)) {
    await rm(legacyRealesrgan, { recursive: true, force: true });
  }
}

async function writeRuntimeIndexManifest(items) {
  const payload = {
    preparedAt: new Date().toISOString(),
    hostPlatform: normalizePlatform(process.platform),
    targets: items,
  };
  await writeManifest(runtimeIndexManifestPath, payload);
}

async function prepareRuntimeForPlatform(targetPlatform) {
  const spec = RUNTIME_SPECS[targetPlatform];
  if (!spec) {
    log(`Skip: unsupported platform "${targetPlatform}". Supported: ${Object.keys(RUNTIME_SPECS).join(", ")}`);
    return null;
  }

  const { runtimeRoot, ffmpegRoot, realesrganRoot, realesrganModelsRoot, manifestPath } =
    getRuntimePathsForPlatform(targetPlatform);

  await ensureDir(ffmpegRoot);
  await ensureDir(realesrganModelsRoot);

  const ffmpegTarget = join(ffmpegRoot, spec.ffmpegBin);
  const ffprobeTarget = join(ffmpegRoot, spec.ffprobeBin);
  const realesrganTarget = join(realesrganRoot, spec.realesrganBin);
  const modelParamTarget = join(realesrganModelsRoot, "realesrgan-x4plus.param");
  const modelBinTarget = join(realesrganModelsRoot, "realesrgan-x4plus.bin");

  let existingReady =
    (await pathExists(ffmpegTarget)) &&
    (await pathExists(ffprobeTarget)) &&
    (await pathExists(realesrganTarget)) &&
    (await pathExists(modelParamTarget)) &&
    (await pathExists(modelBinTarget));

  // One-time migration path: old runtime layout stored binaries directly at
  // third_party/{ffmpeg,realesrgan}. Migrate to third_party/<platform>/...
  if (!existingReady) {
    const legacyReady = await hasRuntimeAtRoot(runtimeBaseRoot, spec);
    if (legacyReady) {
      log(`Migrating legacy runtime layout to platform folder (${targetPlatform})...`);
      await cp(join(runtimeBaseRoot, "ffmpeg"), ffmpegRoot, { recursive: true, force: true });
      await cp(join(runtimeBaseRoot, "realesrgan"), realesrganRoot, { recursive: true, force: true });
      existingReady = await hasRuntimeAtRoot(runtimeRoot, spec);
      if (existingReady) {
        log(`Legacy runtime migrated to ${runtimeRoot}`);
      }
    }
  }

  const manifest = await readManifest(manifestPath);
  const specSignature = JSON.stringify({
      targetPlatform,
      ffmpegZipUrls: spec.ffmpegZipUrls,
      ffprobeZipUrls: spec.ffprobeZipUrls || null,
      realesrganZipUrls: spec.realesrganZipUrls,
    });
  const manifestMatches = manifest?.specSignature === specSignature;

  if (!force && existingReady && (manifestMatches || !manifest)) {
    if (!manifestMatches) {
      await writeManifest(manifestPath, {
        preparedAt: new Date().toISOString(),
        targetPlatform,
        specSignature,
        runtimeRoot,
        ffmpegBin: join("ffmpeg", spec.ffmpegBin),
        ffprobeBin: join("ffmpeg", spec.ffprobeBin),
        realesrganBin: join("realesrgan", spec.realesrganBin),
        modelDir: join("realesrgan", "models"),
      });
    }
    const mirroredProbe = join(projectRuntimeBaseRoot, targetPlatform, "realesrgan", "models", "realesrgan-x4plus.param");
    if (!(await pathExists(mirroredProbe))) {
      await mirrorRuntimeToProjectRoot(runtimeRoot, targetPlatform);
    }
    await cleanupLegacyFlatRuntime(runtimeBaseRoot, targetPlatform, spec);
    await cleanupLegacyFlatRuntime(projectRuntimeBaseRoot, targetPlatform, spec);
    log(`Runtime already prepared for ${targetPlatform}. Use --force to refresh.`);
    return {
      platform: targetPlatform,
      ffmpegBin: ffmpegTarget,
      ffprobeBin: ffprobeTarget,
      realesrganBin: realesrganTarget,
      modelDir: realesrganModelsRoot,
      status: manifestMatches ? "cached" : "migrated_cached",
    };
  }

  const scratchDir = join(tmpdir(), `flowkit-upscale-${randomUUID()}`);
  await ensureDir(scratchDir);

  try {
    log(`Preparing runtime for ${targetPlatform}...`);

    const ffmpegZip = join(scratchDir, "ffmpeg.zip");
    await downloadFirstAvailable(spec.ffmpegZipUrls, ffmpegZip, "ffmpeg bundle");

    const ffmpegExtractDir = join(scratchDir, "ffmpeg");
    await ensureDir(ffmpegExtractDir);
    extractZip(ffmpegZip, ffmpegExtractDir);

    const ffmpegSrc = await findFile(ffmpegExtractDir, spec.ffmpegBin);
    if (!ffmpegSrc) {
      throw new Error("Could not locate ffmpeg binary in downloaded archive.");
    }
    let ffprobeSrc = await findFile(ffmpegExtractDir, spec.ffprobeBin);
    await copyExecutable(ffmpegSrc, ffmpegTarget, targetPlatform);
    if (ffprobeSrc) {
      await copyExecutable(ffprobeSrc, ffprobeTarget, targetPlatform);
      log(`Bundled ${spec.ffmpegBin} + ${spec.ffprobeBin}`);
    } else {
      log(`${spec.ffprobeBin} not found in ffmpeg bundle, fallback to dedicated ffprobe package...`);
    }

    if (spec.ffprobeZipUrls?.length) {
      const ffprobeZip = join(scratchDir, "ffprobe.zip");
      await downloadFirstAvailable(spec.ffprobeZipUrls, ffprobeZip, "ffprobe bundle");
      const ffprobeExtractDir = join(scratchDir, "ffprobe");
      await ensureDir(ffprobeExtractDir);
      extractZip(ffprobeZip, ffprobeExtractDir);
      const standaloneProbe = await findFile(ffprobeExtractDir, spec.ffprobeBin);
      if (!standaloneProbe) {
        throw new Error(`Could not locate ${spec.ffprobeBin} in dedicated ffprobe package.`);
      }
      await copyExecutable(standaloneProbe, ffprobeTarget, targetPlatform);
      ffprobeSrc = standaloneProbe;
      log(`Bundled ${spec.ffprobeBin} from dedicated package`);
    }

    if (!(await pathExists(ffprobeTarget))) {
      throw new Error(`${spec.ffprobeBin} is missing after extraction.`);
    }

    const realesrganZip = join(scratchDir, "realesrgan.zip");
    await downloadFirstAvailable(spec.realesrganZipUrls, realesrganZip, "Real-ESRGAN bundle");

    const realesrganExtractDir = join(scratchDir, "realesrgan");
    await ensureDir(realesrganExtractDir);
    extractZip(realesrganZip, realesrganExtractDir);

    const realesrganSrc = await findFile(realesrganExtractDir, spec.realesrganBin);
    if (!realesrganSrc) {
      throw new Error("Could not locate realesrgan binary in downloaded archive.");
    }
    await copyExecutable(realesrganSrc, realesrganTarget, targetPlatform);

    const dynamicLibs = await findDynamicLibs(realesrganExtractDir);
    for (const libPath of dynamicLibs) {
      const libName = libPath.split(/[\\/]/).pop();
      if (!libName) continue;
      const libTarget = join(realesrganRoot, libName);
      await copyFile(libPath, libTarget);
      if (targetPlatform !== "win32") await chmod(libTarget, 0o755);
    }
    if (dynamicLibs.length > 0) {
      log(`Bundled ${dynamicLibs.length} runtime library file(s) for Real-ESRGAN`);
    }

    const models = await findModels(realesrganExtractDir);
    if (!models.length) {
      throw new Error("Could not locate Real-ESRGAN model files (.param/.bin).");
    }

    for (const modelPath of models) {
      const target = join(realesrganModelsRoot, modelPath.split(/[\\/]/).pop());
      await copyFile(modelPath, target);
    }

    if (!(await pathExists(modelParamTarget)) || !(await pathExists(modelBinTarget))) {
      throw new Error("Required model realesrgan-x4plus.[param|bin] not found after extraction.");
    }

    await writeManifest(manifestPath, {
      preparedAt: new Date().toISOString(),
      targetPlatform,
      specSignature,
      runtimeRoot,
      ffmpegBin: join("ffmpeg", spec.ffmpegBin),
      ffprobeBin: join("ffmpeg", spec.ffprobeBin),
      realesrganBin: join("realesrgan", spec.realesrganBin),
      modelDir: join("realesrgan", "models"),
    });

    await mirrorRuntimeToProjectRoot(runtimeRoot, targetPlatform);
    await cleanupLegacyFlatRuntime(runtimeBaseRoot, targetPlatform, spec);
    await cleanupLegacyFlatRuntime(projectRuntimeBaseRoot, targetPlatform, spec);

    log(`Runtime prepared successfully for ${targetPlatform}.`);
    return {
      platform: targetPlatform,
      ffmpegBin: ffmpegTarget,
      ffprobeBin: ffprobeTarget,
      realesrganBin: realesrganTarget,
      modelDir: realesrganModelsRoot,
      status: "prepared",
    };
  } finally {
    if (existsSync(scratchDir)) {
      await rm(scratchDir, { recursive: true, force: true });
    }
  }
}

async function main() {
  log(`Target runtime platform(s): ${targetPlatforms.join(", ")}`);
  const results = [];
  for (const platform of targetPlatforms) {
    const prepared = await prepareRuntimeForPlatform(platform);
    if (prepared) {
      results.push(prepared);
    }
  }
  await writeRuntimeIndexManifest(results);
}

main().catch((error) => {
  console.error(`[prepare-upscale-runtime] ERROR: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
});
