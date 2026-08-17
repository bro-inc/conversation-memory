#!/usr/bin/env bash
# Undo install_launchagent.sh: stop and remove the LaunchAgent(s).
set -euo pipefail

AGENTS_DIR="$HOME/Library/LaunchAgents"

for label in com.broinc.conversation-memory.daemon com.broinc.conversation-memory.ui; do
  plist="$AGENTS_DIR/$label.plist"
  if [ -f "$plist" ]; then
    launchctl unload "$plist" 2>/dev/null || true
    rm "$plist"
    echo "removed: $plist"
  fi
done
