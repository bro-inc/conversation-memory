#!/usr/bin/env bash
# Install a macOS LaunchAgent so daemon.py starts automatically at login and
# restarts itself if it crashes -- so putting the machine to sleep, closing
# the lid, or logging back in never requires manually re-running it.
#
# Usage: ./scripts/install_launchagent.sh [--with-ui]
#   --with-ui   also auto-launch the desktop window at login
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
LOG_DIR="$HOME/Library/Logs/conversation-memory"
AGENTS_DIR="$HOME/Library/LaunchAgents"
DAEMON_LABEL="com.broinc.conversation-memory.daemon"
UI_LABEL="com.broinc.conversation-memory.ui"

mkdir -p "$LOG_DIR" "$AGENTS_DIR"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "error: $VENV_PYTHON not found." >&2
  echo "run first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

write_plist() {
  local label="$1"
  local script="$2"
  local plist="$AGENTS_DIR/$label.plist"
  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$label</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PYTHON</string>
        <string>$script</string>
    </array>
    <key>WorkingDirectory</key><string>$PROJECT_DIR</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>$LOG_DIR/$label.log</string>
    <key>StandardErrorPath</key><string>$LOG_DIR/$label.log</string>
    <key>ProcessType</key><string>Interactive</string>
</dict>
</plist>
PLIST
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load -w "$plist"
  echo "installed + loaded: $plist"
}

write_plist "$DAEMON_LABEL" "$PROJECT_DIR/daemon.py"

if [[ "${1:-}" == "--with-ui" ]]; then
  write_plist "$UI_LABEL" "$PROJECT_DIR/desktop_app.py"
fi

cat <<EOF

daemon will now start automatically at login and restart itself if it crashes.
logs:        $LOG_DIR
status:      launchctl list | grep broinc.conversation-memory
restart now: launchctl kickstart -k gui/\$(id -u)/$DAEMON_LABEL
uninstall:   ./scripts/uninstall_launchagent.sh

IMPORTANT (macOS mic permission): the first time this venv's python binary
tries to open the microphone with no Terminal window attached (i.e. run by
launchd, not by you), macOS may silently deny it instead of prompting. If
the log shows no transcript activity, open System Settings > Privacy &
Security > Microphone and make sure the python3 binary at:
  $VENV_PYTHON
is listed and enabled. Then: launchctl kickstart -k gui/\$(id -u)/$DAEMON_LABEL
EOF
