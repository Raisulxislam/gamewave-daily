#!/bin/sh
# GameWave automated publish: scan -> build -> push. Twice daily via cron.
export HOME=/data/data/com.termux/files/home
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
LOG="$HOME/.gwi/run.log"
cd "$HOME/gamewave-daily" || exit 1

: > "$LOG"

echo "=== scan $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"
python3 scripts/scan_news.py
SCAN_RC=$?
tail -40 "$LOG"
if [ "$SCAN_RC" -ne 0 ]; then
  echo "SCAN FAILED rc=$SCAN_RC"
  exit 1
fi

echo "=== build $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"
hugo --gc --minify >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "HUGO BUILD FAILED"
  tail -30 "$LOG"
  exit 1
fi

echo "=== push $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"
git add -A
if git diff --cached --quiet; then
  echo "nothing new to publish"
  exit 0
fi
git commit -m "gamewave: automated publish $(date -u +%Y-%m-%dT%H:%M)" >> "$LOG" 2>&1
git push origin HEAD >> "$LOG" 2>&1
echo "PUSH OK"
exit 0