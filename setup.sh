#!/usr/bin/env bash
set -e

echo "========================================="
echo "  Flow Kit — Setup"
echo "========================================="
echo ""

# ─── Windows check ──────────────────────────────────────────
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$(uname -s)" == CYGWIN* ]]; then
    echo "Detected Windows (Git Bash / MSYS2)."
    echo "  Tip: For best results, use WSL (Windows Subsystem for Linux)."
    echo "  Install WSL: wsl --install"
    echo "  Then re-run: bash setup.sh"
    echo ""
fi

ERRORS=0

# ─── Python ──────────────────────────────────────────────────
echo "Checking Python..."
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        echo "  OK: Python $PY_VERSION"
    else
        echo "  WARNING: Python $PY_VERSION found, 3.10+ recommended"
    fi
else
    echo "  MISSING: Python 3 not found"
    echo "  Install: https://www.python.org/downloads/"
    echo "  macOS:   brew install python@3.12"
    echo "  Ubuntu:  sudo apt install python3 python3-pip python3-venv"
    echo "  WSL:     sudo apt install python3 python3-pip python3-venv"
    ERRORS=$((ERRORS + 1))
fi

# ─── pip ─────────────────────────────────────────────────────
echo "Checking pip..."
if python3 -m pip --version &>/dev/null; then
    echo "  OK: $(python3 -m pip --version | head -1)"
else
    echo "  MISSING: pip not found"
    echo "  Install: python3 -m ensurepip --upgrade"
    ERRORS=$((ERRORS + 1))
fi

# ─── ffmpeg ──────────────────────────────────────────────────
echo "Checking ffmpeg..."
if command -v ffmpeg &>/dev/null; then
    FF_VERSION=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    echo "  OK: ffmpeg $FF_VERSION"
else
    echo "  MISSING: ffmpeg not found (needed for video concat/trim/music)"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt install ffmpeg"
    echo "  Windows: https://ffmpeg.org/download.html"
    ERRORS=$((ERRORS + 1))
fi

# ─── ffprobe ─────────────────────────────────────────────────
echo "Checking ffprobe..."
if command -v ffprobe &>/dev/null; then
    echo "  OK: ffprobe available"
else
    echo "  MISSING: ffprobe not found (usually bundled with ffmpeg)"
    ERRORS=$((ERRORS + 1))
fi

# ─── Chrome ──────────────────────────────────────────────────
echo "Checking Chrome..."
if [ -d "/Applications/Google Chrome.app" ] || command -v google-chrome &>/dev/null || command -v google-chrome-stable &>/dev/null; then
    echo "  OK: Chrome found"
else
    echo "  WARNING: Chrome not detected (needed for extension)"
    echo "  Download: https://www.google.com/chrome/"
fi

echo ""

# ─── Abort if critical missing ───────────────────────────────
if [ "$ERRORS" -gt 0 ]; then
    echo "Found $ERRORS missing dependency(ies). Install them and re-run."
    exit 1
fi

# ─── Virtual environment ────────────────────────────────────
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created: venv/"
else
    echo "  Exists: venv/"
fi

# ─── Activate & install ─────────────────────────────────────
echo "Installing Python dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "  Installed: $(pip list --format=columns | grep -cE 'fastapi|uvicorn|aiosqlite|websockets|pydantic|aiohttp|httpx') packages"

# ─── Verify import ──────────────────────────────────────────
echo "Verifying agent can import..."
python3 -c "from agent.main import app; print('  OK: agent.main imports successfully')" 2>&1 || {
    echo "  FAILED: agent cannot import — check error above"
    exit 1
}

# ─── jq (for statusline) ───────────────────────────────────
echo "Checking jq..."
if command -v jq &>/dev/null; then
    echo "  OK: jq $(jq --version 2>&1)"
else
    echo "  WARNING: jq not found (needed for statusline)"
    echo "  macOS:   brew install jq"
    echo "  Ubuntu:  sudo apt install jq"
    echo "  WSL:     sudo apt install jq"
fi

# ─── Claude Code statusline ────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATUSLINE_SCRIPT="$SCRIPT_DIR/scripts/statusline.sh"
CLAUDE_SETTINGS="$SCRIPT_DIR/.claude/settings.local.json"

echo "Setting up Claude Code statusline..."
chmod +x "$STATUSLINE_SCRIPT" 2>/dev/null

if ! command -v jq &>/dev/null; then
    echo "  SKIPPED: jq not installed (needed for statusline setup)"
elif [ -f "$CLAUDE_SETTINGS" ]; then
    # Check if statusLine already configured
    if jq -e '.statusLine' "$CLAUDE_SETTINGS" &>/dev/null; then
        echo "  OK: statusLine already configured"
    else
        # Add statusLine to existing settings
        TMP=$(mktemp)
        jq --arg cmd "$STATUSLINE_SCRIPT" '. + {"statusLine": {"type": "command", "command": $cmd}}' "$CLAUDE_SETTINGS" > "$TMP" && mv "$TMP" "$CLAUDE_SETTINGS"
        echo "  Added: statusLine to .claude/settings.local.json"
    fi
else
    # Create settings file with statusLine
    mkdir -p "$SCRIPT_DIR/.claude"
    cat > "$CLAUDE_SETTINGS" <<EOJSON
{
  "statusLine": {
    "type": "command",
    "command": "$STATUSLINE_SCRIPT"
  }
}
EOJSON
    echo "  Created: .claude/settings.local.json with statusLine"
fi

echo ""
echo "========================================="
echo "  Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Load Chrome extension:"
echo "     chrome://extensions → Developer mode → Load unpacked → extension/"
echo ""
echo "  2. Open Google Flow:"
echo "     https://labs.google/fx/tools/flow (sign in)"
echo ""
echo "  3. Start the agent:"
echo "     source venv/bin/activate"
echo "     python -m agent.main"
echo ""
echo "  4. Verify:"
echo "     curl http://127.0.0.1:8100/health"
echo ""
echo "  5. Claude Code statusline:"
echo "     GLA status shows at the bottom of Claude Code automatically."
echo ""
