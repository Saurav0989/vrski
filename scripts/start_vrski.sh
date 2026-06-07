#!/bin/bash
set -euo pipefail

AVD_NAME="vrski_dev"
API_PORT=7070
EMULATOR_PID=""
API_PID=""

if [ -z "${JAVA_HOME:-}" ] && [ -d "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
fi

# Define search paths for Android SDK on macOS
ANDROID_SDK_PATHS=(
    "${HOME:-}/Library/Android/sdk"
    "/Users/sauravkumar/Library/Android/sdk"
    "/Library/Android/sdk"
    "/opt/homebrew/share/android-commandlinetools"
)

# Define cleanup function
cleanup() {
    # Disable trap to avoid recursion/double calling
    trap - EXIT SIGINT SIGTERM
    
    echo ""
    echo "Stopping Vrski components..."
    
    # Terminate uvicorn API server
    if [ -n "$API_PID" ]; then
        echo "Killing API server (PID: $API_PID)..."
        kill "$API_PID" 2>/dev/null || true
    fi
    
    # Terminate Emulator
    if [ -n "$EMULATOR_PID" ]; then
        echo "Killing Emulator (PID: $EMULATOR_PID)..."
        kill "$EMULATOR_PID" 2>/dev/null || true
    fi
    
    # Wait for background processes to finish
    wait 2>/dev/null || true
    echo "Cleanup complete."
}

# Trap signals and exit
trap cleanup EXIT SIGINT SIGTERM

SDK_ROOT=""
for path in "${ANDROID_SDK_PATHS[@]}"; do
    if [ -d "$path" ]; then
        SDK_ROOT="$path"
        break
    fi
done

if [ -n "$SDK_ROOT" ]; then
    export PATH="$SDK_ROOT/platform-tools:$SDK_ROOT/emulator:$PATH"
fi

echo "[1/4] Starting Android emulator..."
emulator -avd $AVD_NAME -no-audio -no-boot-anim -gpu swiftshader_indirect &
EMULATOR_PID=$!

echo "[2/4] Waiting for device to boot..."
adb wait-for-device
# Wait for full boot (sys.boot_completed property)
while [ "$(adb shell getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
    echo "  Waiting for boot..."
    sleep 3
done
echo "  Device ready."

echo "[3/4] Initializing uiautomator2 server..."
python3 -m uiautomator2 init

echo "[4/4] Starting Vrski Control API on port $API_PORT..."
uvicorn vrski.api.main:app --host 0.0.0.0 --port $API_PORT &
API_PID=$!

echo ""
echo "✓ Vrski is running"
echo "  Emulator PID:  $EMULATOR_PID"
echo "  API PID:       $API_PID"
echo "  API URL:       http://localhost:$API_PORT"
echo ""
echo "To add the MCP server to Claude Code:"
echo "  claude mcp add vrski python -m vrski.mcp.server"
echo ""
echo "Press Ctrl+C to stop."
wait
