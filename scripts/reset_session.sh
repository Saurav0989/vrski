#!/bin/bash
# Kill the running emulator, wipe user data, and restart from a clean state.
# Use this when automation has left the emulator in a broken or dirty state.

set -e

AVD_NAME="${1:-vrski_dev}"
SERIAL="${2:-emulator-5554}"
API_PORT=7070

echo "[1/4] Stopping Vrski Control API (if running)..."
pkill -f "uvicorn vrski.api" 2>/dev/null || true
sleep 1

echo "[2/4] Killing emulator: $SERIAL..."
adb -s "$SERIAL" emu kill 2>/dev/null || true
sleep 3

echo "[3/4] Restarting emulator with wiped data..."
EMULATOR_BIN=$(which emulator 2>/dev/null || echo "$HOME/Library/Android/sdk/emulator/emulator")
"$EMULATOR_BIN" -avd "$AVD_NAME" -wipe-data -no-audio -no-boot-anim -gpu swiftshader_indirect &
EMULATOR_PID=$!
echo "  Emulator PID: $EMULATOR_PID"

echo "  Waiting for device to boot..."
adb wait-for-device
while [ "$(adb shell getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
    echo "  Still booting..."
    sleep 3
done
echo "  Device ready."

echo "[4/4] Re-initialising uiautomator2 server..."
python -m uiautomator2 init

echo ""
echo "✓ Session reset complete. Start the API with:"
echo "  uvicorn vrski.api.main:app --host 0.0.0.0 --port $API_PORT"
