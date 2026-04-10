#!/usr/bin/env bash
set -euo pipefail

# install-skill-governance.sh
#
# Installs the skill-governance hook for Claude Code.
# Creates the hook, default config, and patches settings.json.
#
# Usage:
#   bash install-skill-governance.sh          # install
#   bash install-skill-governance.sh --check  # verify installation
#
# What it does:
#   1. Copies skill-governance.py to ~/.claude/hooks/
#   2. Creates ~/.claude/skill-governance.json (default config, won't overwrite)
#   3. Adds wildcard permission for ~/.claude/skills/** to settings.json
#   4. Registers the PreToolUse hook in settings.json
#   5. Runs the test suite to verify

CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS="$CLAUDE_DIR/settings.json"
CONFIG="$CLAUDE_DIR/skill-governance.json"
HOOK="$HOOKS_DIR/skill-governance.py"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

info()  { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$1"; }
die()   { error "$1"; exit 1; }

# --- Check mode ---
if [[ "${1:-}" == "--check" ]]; then
    echo "Checking skill-governance installation..."
    exit_code=0

    if [[ -f "$HOOK" ]]; then
        info "Hook exists: $HOOK"
    else
        error "Hook missing: $HOOK"
        exit_code=1
    fi

    if [[ -f "$CONFIG" ]]; then
        if python3 - "$CONFIG" <<'PYCHECK'
import json, sys
json.load(open(sys.argv[1]))
PYCHECK
        then
            info "Config valid: $CONFIG"
        else
            error "Config has invalid JSON: $CONFIG"
            exit_code=1
        fi
    else
        error "Config missing: $CONFIG"
        exit_code=1
    fi

    if [[ -f "$SETTINGS" ]]; then
        if grep -q "skill-governance.py" "$SETTINGS"; then
            info "Hook registered in settings.json"
        else
            error "Hook not registered in settings.json"
            exit_code=1
        fi

        if grep -q '\.claude/skills/\*\*' "$SETTINGS"; then
            info "Wildcard permission present in settings.json"
        else
            warn "No wildcard skill permission in settings.json — skills may still prompt"
            exit_code=1
        fi
    else
        error "Settings file missing: $SETTINGS"
        exit_code=1
    fi

    exit "$exit_code"
fi

# --- Prerequisites ---
echo "Installing skill-governance hook for Claude Code..."
echo ""

command -v python3 >/dev/null 2>&1 || die "python3 is required but not found"

[[ -d "$CLAUDE_DIR" ]] || die "$CLAUDE_DIR does not exist. Is Claude Code installed?"

mkdir -p "$HOOKS_DIR"

# Restore backup on failure
restore_on_error() {
    if [[ -f "$SETTINGS.bak" ]]; then
        cp "$SETTINGS.bak" "$SETTINGS"
        error "Restored settings.json from backup after failure"
    fi
}
trap restore_on_error ERR

# --- Step 1: Install hook ---
if [[ -f "$SCRIPT_DIR/skill-governance.py" ]]; then
    cp "$SCRIPT_DIR/skill-governance.py" "$HOOK"
    info "Installed hook: $HOOK"
else
    die "skill-governance.py not found in $SCRIPT_DIR"
fi

# --- Step 2: Create default config (don't overwrite) ---
if [[ -f "$CONFIG" ]]; then
    info "Config already exists: $CONFIG (not overwriting)"
else
    cat > "$CONFIG" <<'CONF'
{
  "blocked": [],
  "audit": false,
  "dangerous_patterns": []
}
CONF
    info "Created default config: $CONFIG"
fi

# --- Step 3: Patch settings.json ---
if [[ ! -f "$SETTINGS" ]]; then
    cat > "$SETTINGS" <<'SETTINGS_JSON'
{
  "permissions": {
    "allow": []
  },
  "hooks": {
    "PreToolUse": []
  }
}
SETTINGS_JSON
    info "Created settings.json"
fi

# Validate JSON before modifying
python3 - "$SETTINGS" <<'PYVALIDATE' \
    || die "settings.json has invalid JSON — fix it manually before running this installer"
import json, sys
json.load(open(sys.argv[1]))
PYVALIDATE

# Backup
cp "$SETTINGS" "$SETTINGS.bak"
info "Backed up settings.json to settings.json.bak"

# Add wildcard permission if not present
if grep -q '\.claude/skills/\*\*' "$SETTINGS"; then
    info "Wildcard skill permission already present"
else
    python3 - "$SETTINGS" "$HOME" <<'PYPERM'
import json, os, sys
settings_path, home = sys.argv[1], sys.argv[2]
with open(settings_path) as f:
    s = json.load(f)
perms = s.setdefault('permissions', {}).setdefault('allow', [])
perm = f'Bash({home}/.claude/skills/**)'
if not any('.claude/skills/**' in p for p in perms):
    perms.insert(0, perm)
tmp = settings_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(s, f, indent=2)
    f.write('\n')
os.replace(tmp, settings_path)
PYPERM
    info "Added wildcard permission: Bash($HOME/.claude/skills/**)"
fi

# Register hook if not present
if grep -q "skill-governance.py" "$SETTINGS"; then
    info "Hook already registered in settings.json"
else
    python3 - "$SETTINGS" <<'PYHOOK'
import json, os, sys
settings_path = sys.argv[1]
with open(settings_path) as f:
    s = json.load(f)
hooks = s.setdefault('hooks', {}).setdefault('PreToolUse', [])
bash_entry = None
for entry in hooks:
    if entry.get('matcher') == 'Bash':
        bash_entry = entry
        break
if bash_entry is None:
    bash_entry = {'matcher': 'Bash', 'hooks': []}
    hooks.append(bash_entry)
hook_list = bash_entry.setdefault('hooks', [])
gov_hook = {
    'type': 'command',
    'command': 'python3 ~/.claude/hooks/skill-governance.py',
    'statusMessage': 'Checking skill governance...'
}
if not any('skill-governance.py' in h.get('command', '') for h in hook_list):
    hook_list.insert(0, gov_hook)
tmp = settings_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(s, f, indent=2)
    f.write('\n')
os.replace(tmp, settings_path)
PYHOOK
    info "Registered hook in settings.json PreToolUse"
fi

# --- Step 4: Run tests if available ---
echo ""
TEST_FILE="$HOOKS_DIR/test_skill_governance.py"
if [[ -f "$TEST_FILE" ]]; then
    echo "Running tests..."
    if command -v pytest >/dev/null 2>&1; then
        if pytest "$TEST_FILE" -q; then
            info "All tests passed"
        else
            warn "Some tests failed — check output above"
        fi
    else
        if python3 -m pytest "$TEST_FILE" -q; then
            info "All tests passed"
        else
            warn "Some tests failed (or pytest not installed) — check output above"
        fi
    fi
else
    warn "Test file not found at $TEST_FILE — skipping verification"
fi

echo ""
echo "=========================================="
echo "  Skill governance installed successfully"
echo "=========================================="
echo ""
echo "Skills in ~/.claude/skills/ will now run without prompting."
echo "The governance hook enforces blocklist and injection detection."
echo ""
echo "Config:  $CONFIG"
echo "Hook:    $HOOK"
echo "Verify:  bash $(cd "$SCRIPT_DIR" && pwd)/$(basename "${BASH_SOURCE[0]}") --check"
echo ""
