import { ChildProcess, execSync, spawn } from 'child_process'
import { delimiter, join } from 'path'
import { existsSync } from 'fs'
import { app } from 'electron'
import { EventEmitter } from 'events'

const AGENT_PORT = 8100
const HEALTH_URL = `http://127.0.0.1:${AGENT_PORT}/health`
const MANUAL_CONTEXT_URL = `http://127.0.0.1:${AGENT_PORT}/api/flow/manual/context`
const DOWNLOAD_ASSETS_PROBE_URL = `http://127.0.0.1:${AGENT_PORT}/api/videos/__feature_probe__/download-assets`
const SCRIPT_EXPORT_PROBE_URL = `http://127.0.0.1:${AGENT_PORT}/api/videos/__feature_probe__/script-export`
const SCRIPT_IMPORT_PROBE_URL = `http://127.0.0.1:${AGENT_PORT}/api/videos/__feature_probe__/script-import`
const MAX_RETRIES = 5
const RESTART_DELAY_MS = 3000
const HEALTH_POLL_MS = 600
const HEALTH_TIMEOUT_MS = 20000

class Sidecar extends EventEmitter {
    private process: ChildProcess | null = null
    private stopping = false
    private restartCount = 0
    /** Set to true when the process exits, so _waitForReady know to bail out */
    private abortReady = false
    private resolvingPortConflict = false

    async start() {
        this.stopping = false
        // If port is already occupied by an external instance, adopt only if compatible.
        const alreadyUp = await this._checkHealth()
        if (alreadyUp) {
            const compatible = await this._checkCompatibility()
            if (compatible) {
                const preferred = this._isPreferredAgentOnPort(AGENT_PORT)
                if (preferred) {
                    console.log('[sidecar] External compatible agent already running — adopting.')
                    this.emit('status', 'Ready')
                    return
                }

                console.warn('[sidecar] Compatible agent detected on :8100 but not preferred runtime — replacing it.')
                const replaced = await this._replaceIncompatibleProcess()
                if (!replaced) {
                    this.emit('status', 'Error — port 8100 occupied by external compatible process')
                    return
                }
                this._spawn()
                return
            }

            console.warn('[sidecar] External agent on :8100 is incompatible — trying to replace it.')
            const replaced = await this._replaceIncompatibleProcess()
            if (!replaced) {
                this.emit('status', 'Error — port 8100 occupied by incompatible process')
                return
            }
        }
        this._spawn()
    }

    stop() {
        this.stopping = true
        if (this.process) {
            console.log('[sidecar] Stopping Python agent...')
            this.process.kill('SIGTERM')
            setTimeout(() => this.process?.kill('SIGKILL'), 3000)
            this.process = null
        }
    }

    private _spawn() {
        const { bin, args, cwd } = this._resolveCommand()
        if (!existsSync(bin)) {
            const missingName = process.platform === 'win32' ? 'flowkit-agent.exe' : 'flowkit-agent'
            console.error('[sidecar] Agent binary missing:', { bin, cwd })
            this.emit('status', `Error — missing ${missingName}`)
            return
        }
        console.log('[sidecar] Spawning:', bin, args.join(' '), 'cwd:', cwd)

        this.abortReady = false
        this.emit('status', 'Starting...')

        const sidecarEnv: NodeJS.ProcessEnv = { ...process.env, PYTHONDONTWRITEBYTECODE: '1' }
        this._injectLocalUpscaleRuntimeEnv(sidecarEnv)

        this.process = spawn(bin, args, {
            cwd,
            env: sidecarEnv,
            stdio: ['ignore', 'pipe', 'pipe']
        })

        this.process.on('error', async (err: NodeJS.ErrnoException) => {
            console.error('[sidecar] Spawn failed:', err)
            this.abortReady = true

            // If another agent is already healthy, adopt it instead of failing hard.
            const alreadyUp = await this._checkHealth()
            if (alreadyUp) {
                const compatible = await this._checkCompatibility()
                if (compatible) {
                    console.log('[sidecar] Spawn failed but external compatible agent is healthy — adopting.')
                    this.emit('status', 'Ready')
                    return
                }

                console.warn('[sidecar] Spawn failed and external agent is incompatible — trying to replace.')
                const replaced = await this._replaceIncompatibleProcess()
                if (replaced) {
                    this.stopping = false
                    this.abortReady = false
                    this._spawn()
                    return
                }
            }

            const hint = err.code === 'ENOENT'
                ? 'agent binary/python not found'
                : (String(err?.message || '').toLowerCase().includes('not a valid win32 application')
                    ? 'invalid windows agent binary'
                    : (err.code || 'spawn error'))
            this.emit('status', `Error — ${hint}`)
        })

        this.process.stdout?.on('data', (d: Buffer) => {
            process.stdout.write(`[agent] ${d}`)
        })
        this.process.stderr?.on('data', (d: Buffer) => {
            process.stderr.write(`[agent] ${d}`)
            // Detect port-already-in-use and try to replace incompatible stale agent.
            const msg = d.toString()
            if (/address already in use|eaddrinuse/i.test(msg) && !this.resolvingPortConflict) {
                this.resolvingPortConflict = true
                this.abortReady = true // cancel _waitForReady loop while resolving conflict
                void this._handlePortConflict()
            }
        })

        this.process.on('exit', (code) => {
            console.log(`[sidecar] Process exited with code ${code}`)
            this.abortReady = true           // stop _waitForReady polling
            this.process = null

            if (!this.stopping) {
                this.emit('status', `Stopped (exit ${code})`)
                if (this.restartCount < MAX_RETRIES) {
                    this.restartCount++
                    console.log(`[sidecar] Restarting in ${RESTART_DELAY_MS}ms (attempt ${this.restartCount}/${MAX_RETRIES})`)
                    setTimeout(() => {
                        if (!this.stopping) {
                            this.abortReady = false
                            this._spawn()
                        }
                    }, RESTART_DELAY_MS)
                } else {
                    this.emit('status', 'Error — max restarts reached')
                }
            }
        })

        // Poll health until ready (or process exits)
        this._waitForReady()
    }

    private async _handlePortConflict() {
        try {
            console.warn('[sidecar] Port 8100 already in use — checking compatibility.')
            this.stopping = true // suppress auto-restart while we resolve conflict

            // Give current process a moment to exit after bind failure.
            await this._sleep(500)

            const healthy = await this._checkHealth()
            if (healthy) {
                const compatible = await this._checkCompatibility()
                if (compatible) {
                    console.log('[sidecar] External compatible agent detected — adopting.')
                    this.emit('status', 'Ready')
                    return
                }
            }

            const replaced = await this._replaceIncompatibleProcess()
            if (!replaced) {
                this.emit('status', 'Error — port 8100 occupied by incompatible process')
                return
            }

            console.log('[sidecar] Incompatible process removed — restarting sidecar.')
            this.stopping = false
            this.abortReady = false
            this._spawn()
        } finally {
            this.resolvingPortConflict = false
        }
    }

    private async _waitForReady() {
        const deadline = Date.now() + HEALTH_TIMEOUT_MS
        while (Date.now() < deadline) {
            if (this.abortReady) {
                console.log('[sidecar] _waitForReady aborted (process exited or port adopted)')
                return
            }
            const ok = await this._checkHealth()
            if (ok) {
                if (!this.abortReady) {
                    console.log('[sidecar] Agent is ready')
                    this.restartCount = 0
                    this.emit('status', 'Ready')
                }
                return
            }
            await new Promise(r => setTimeout(r, HEALTH_POLL_MS))
        }
        if (!this.abortReady) {
            console.error('[sidecar] Agent failed to start within timeout')
            this.emit('status', 'Error — timeout')
        }
    }

    private async _checkHealth(): Promise<boolean> {
        try {
            const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(1500) })
            return res.ok
        } catch {
            return false
        }
    }

    private async _checkCompatibility(): Promise<boolean> {
        try {
            const manualContextRes = await fetch(MANUAL_CONTEXT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ create_if_missing: false }),
                signal: AbortSignal.timeout(2000),
            })
            // Endpoint exists => 200/4xx/5xx except 404.
            if (manualContextRes.status === 404) return false

            // Route shape probe for new local-download feature.
            // Existing route should return 405 on GET (method not allowed),
            // but never 404 when endpoint is present.
            const downloadProbeRes = await fetch(DOWNLOAD_ASSETS_PROBE_URL, {
                method: 'GET',
                signal: AbortSignal.timeout(2000),
            })
            if (downloadProbeRes.status === 404) return false

            // Script export route probe.
            // Expected behavior with dummy vid: 404 + {"detail":"Video not found"}.
            const scriptExportRes = await fetch(SCRIPT_EXPORT_PROBE_URL, {
                method: 'GET',
                signal: AbortSignal.timeout(2000),
            })
            if (scriptExportRes.status === 404) {
                const raw = await scriptExportRes.text().catch(() => '')
                const isVideoNotFound = raw.includes('Video not found')
                if (!isVideoNotFound) return false
            } else if (!scriptExportRes.ok && scriptExportRes.status !== 400 && scriptExportRes.status !== 422) {
                // Allow non-2xx but reject hard routing/transport incompatibilities.
                return false
            }

            // Script import route probe.
            // Existing route should return 405 on GET (method not allowed), never 404.
            const scriptImportRes = await fetch(SCRIPT_IMPORT_PROBE_URL, {
                method: 'GET',
                signal: AbortSignal.timeout(2000),
            })
            if (scriptImportRes.status === 404) return false

            return true
        } catch {
            return false
        }
    }

    private async _replaceIncompatibleProcess(): Promise<boolean> {
        const pids = this._listListeningPids(AGENT_PORT)
        if (pids.length === 0) return true

        for (const pid of pids) {
            const cmd = this._readPidCommand(pid)
            if (!this._isLikelyFlowKitAgentCommand(cmd)) {
                console.error(`[sidecar] Refusing to kill non-FlowKit process on :${AGENT_PORT} (pid=${pid}, cmd="${cmd}")`)
                return false
            }
        }

        for (const pid of pids) {
            try {
                console.warn(`[sidecar] Terminating stale FlowKit agent pid=${pid}`)
                process.kill(pid, 'SIGTERM')
            } catch (err) {
                console.error(`[sidecar] Failed to SIGTERM pid=${pid}:`, err)
            }
        }

        await this._sleep(1200)
        let remaining = this._listListeningPids(AGENT_PORT)
        if (remaining.length > 0) {
            for (const pid of remaining) {
                try {
                    console.warn(`[sidecar] Force killing stale FlowKit agent pid=${pid}`)
                    process.kill(pid, 'SIGKILL')
                } catch (err) {
                    console.error(`[sidecar] Failed to SIGKILL pid=${pid}:`, err)
                }
            }
        }

        // Some macOS processes linger briefly after SIGKILL. Wait a bit longer before
        // declaring failure, and only fail hard if a non-FlowKit process is still binding.
        for (let attempt = 0; attempt < 8; attempt += 1) {
            await this._sleep(400)
            remaining = this._listListeningPids(AGENT_PORT)
            if (remaining.length === 0) return true
            const nonFlowKit = remaining.find((pid) => !this._isLikelyFlowKitAgentCommand(this._readPidCommand(pid)))
            if (nonFlowKit) {
                console.error(`[sidecar] Port ${AGENT_PORT} still occupied by non-FlowKit process pid=${nonFlowKit}`)
                return false
            }
            if (attempt >= 3) {
                for (const pid of remaining) {
                    try { process.kill(pid, 'SIGKILL') } catch { /* noop */ }
                }
            }
        }

        return this._listListeningPids(AGENT_PORT).length === 0
    }

    private _listListeningPids(port: number): number[] {
        if (process.platform === 'win32') {
            try {
                const out = execSync(`netstat -ano -p tcp | findstr LISTENING | findstr :${port}`, { encoding: 'utf8' }).trim()
                if (!out) return []
                const pids = out
                    .split(/\r?\n/)
                    .map((line) => line.trim().split(/\s+/))
                    .filter((parts) => parts.length >= 5)
                    .map((parts) => Number.parseInt(parts[parts.length - 1], 10))
                    .filter((pid) => Number.isFinite(pid) && pid > 0)
                return Array.from(new Set(pids))
            } catch {
                return []
            }
        }
        try {
            const out = execSync(`lsof -n -P -ti tcp:${port} -sTCP:LISTEN`, { encoding: 'utf8' }).trim()
            if (!out) return []
            return out
                .split('\n')
                .map(v => Number.parseInt(v.trim(), 10))
                .filter(v => Number.isFinite(v) && v > 0)
        } catch {
            return []
        }
    }

    private _readPidCommand(pid: number): string {
        if (!Number.isFinite(pid) || pid <= 0) return ''
        if (process.platform === 'win32') {
            try {
                const cmd = execSync(
                    `powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \\"ProcessId=${pid}\\").CommandLine"`,
                    { encoding: 'utf8' },
                ).trim()
                if (cmd) return cmd
            } catch { /* noop */ }
            try {
                const out = execSync(`tasklist /FI "PID eq ${pid}" /FO LIST`, { encoding: 'utf8' }).trim()
                return out
            } catch {
                return ''
            }
        }
        try {
            return execSync(`ps -p ${pid} -o command=`, { encoding: 'utf8' }).trim()
        } catch {
            return ''
        }
    }

    private _isLikelyFlowKitAgentCommand(cmd: string): boolean {
        const lower = cmd.toLowerCase()
        return lower.includes('agent.main') || lower.includes('flowkit-agent')
    }

    private _isPreferredAgentOnPort(port: number): boolean {
        const pids = this._listListeningPids(port)
        if (pids.length === 0) return false
        return pids.some((pid) => this._isPreferredAgentCommand(this._readPidCommand(pid)))
    }

    private _isPreferredAgentCommand(cmd: string): boolean {
        const lower = cmd.toLowerCase()
        if (!lower) return false

        if (app.isPackaged) {
            return lower.includes('flowkit-agent')
        }

        const projectRoot = join(__dirname, '../../..')
        const expectedPython = process.platform === 'win32'
            ? join(projectRoot, 'venv', 'Scripts', 'python.exe')
            : join(projectRoot, 'venv', 'bin', 'python3')

        return lower.includes(expectedPython.toLowerCase()) && lower.includes('agent.main')
    }

    private _sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms))
    }

    private _resolveCommand(): { bin: string; args: string[]; cwd: string } {
        if (app.isPackaged) {
            const ext = process.platform === 'win32' ? '.exe' : ''
            const candidates = [
                join(process.resourcesPath, 'agent', `flowkit-agent${ext}`),
                join(process.resourcesPath, 'agent', 'flowkit-agent'),
                join(process.resourcesPath, `flowkit-agent${ext}`),
                join(process.resourcesPath, 'flowkit-agent'),
            ]
            const bin = candidates.find((p) => existsSync(p)) || candidates[0]
            return { bin, args: [], cwd: process.resourcesPath }
        } else {
            const projectRoot = join(__dirname, '../../..')
            const venvPython = process.platform === 'win32'
                ? join(projectRoot, 'venv', 'Scripts', 'python.exe')
                : join(projectRoot, 'venv', 'bin', 'python3')
            return {
                bin: venvPython,
                args: ['-m', 'agent.main'],
                cwd: projectRoot
            }
        }
    }

    private _injectLocalUpscaleRuntimeEnv(sidecarEnv: NodeJS.ProcessEnv) {
        const projectRoot = join(__dirname, '../../..')
        const platformFolder = process.platform === 'win32'
            ? 'win32'
            : (process.platform === 'darwin' ? 'darwin' : process.platform)
        const runtimeBaseRoots = app.isPackaged
            ? [
                join(process.resourcesPath, 'agent', 'third_party'),
                join(process.resourcesPath, 'third_party'),
            ]
            : [
                join(projectRoot, 'third_party'),
                join(projectRoot, 'desktop', 'resources', 'agent', 'third_party'),
            ]
        const runtimeRoots = runtimeBaseRoots.flatMap((baseRoot) => [
            join(baseRoot, platformFolder),
            baseRoot,
        ])

        const ffmpegName = process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg'
        const ffprobeName = process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe'
        const realesrganName = process.platform === 'win32' ? 'realesrgan-ncnn-vulkan.exe' : 'realesrgan-ncnn-vulkan'
        const modelParam = 'realesrgan-x4plus.param'
        const modelBin = 'realesrgan-x4plus.bin'

        let chosenRoot = ''
        for (const root of runtimeRoots) {
            const ffmpegBin = join(root, 'ffmpeg', ffmpegName)
            const ffprobeBin = join(root, 'ffmpeg', ffprobeName)
            const realesrganBin = join(root, 'realesrgan', realesrganName)
            const modelDir = join(root, 'realesrgan', 'models')
            const hasAll =
                existsSync(ffmpegBin) &&
                existsSync(ffprobeBin) &&
                existsSync(realesrganBin) &&
                existsSync(join(modelDir, modelParam)) &&
                existsSync(join(modelDir, modelBin))
            if (hasAll) {
                chosenRoot = root
                break
            }
        }

        if (!chosenRoot) {
            chosenRoot = runtimeRoots.find((root) => existsSync(root)) || ''
        }
        if (!chosenRoot) return

        const ffmpegDir = join(chosenRoot, 'ffmpeg')
        const realesrganDir = join(chosenRoot, 'realesrgan')
        const ffmpegBin = join(ffmpegDir, ffmpegName)
        const ffprobeBin = join(ffmpegDir, ffprobeName)
        const realesrganBin = join(realesrganDir, realesrganName)
        const modelDir = join(realesrganDir, 'models')

        if (existsSync(ffmpegBin)) sidecarEnv.LOCAL_UPSCALE_FFMPEG = ffmpegBin
        if (existsSync(ffprobeBin)) sidecarEnv.LOCAL_UPSCALE_FFPROBE = ffprobeBin
        if (existsSync(realesrganBin)) sidecarEnv.LOCAL_UPSCALE_BIN = realesrganBin
        if (existsSync(join(modelDir, modelParam)) && existsSync(join(modelDir, modelBin))) {
            sidecarEnv.LOCAL_UPSCALE_MODEL_DIR = modelDir
        }
        sidecarEnv.LOCAL_UPSCALE_RUNTIME_ROOT = chosenRoot

        const pathParts: string[] = []
        if (existsSync(ffmpegDir)) pathParts.push(ffmpegDir)
        if (existsSync(realesrganDir)) pathParts.push(realesrganDir)
        const currentPath = process.env.PATH ?? process.env.Path ?? ''
        if (currentPath) pathParts.push(currentPath)
        if (pathParts.length > 0) {
            const mergedPath = pathParts.join(delimiter)
            sidecarEnv.PATH = mergedPath
            sidecarEnv.Path = mergedPath
        }

        console.log('[sidecar] Local upscale runtime root:', chosenRoot)
    }
}

export const sidecar = new Sidecar()
