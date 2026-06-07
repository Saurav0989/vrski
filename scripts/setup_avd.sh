#!/bin/bash
set -euo pipefail

echo "Setting up Vrski AVD..."

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

SDK_ROOT=""
for path in "${ANDROID_SDK_PATHS[@]}"; do
    if [ -d "$path" ]; then
        SDK_ROOT="$path"
        break
    fi
done

if [ -n "$SDK_ROOT" ]; then
    export PATH="$SDK_ROOT/platform-tools:$SDK_ROOT/emulator:$SDK_ROOT/cmdline-tools/latest/bin:$PATH"
fi

PACKAGE="system-images;android-34;google_apis_playstore;arm64-v8a"
AVD_NAME="vrski_dev"

# Install system image
echo "Installing system image..."
if command -v sdkmanager &> /dev/null; then
    sdkmanager "$PACKAGE"
    sdkmanager "platform-tools"
    sdkmanager "emulator"
else
    echo "⚠ sdkmanager not found in PATH. Make sure cmdline-tools is installed and added to PATH."
    exit 1
fi

# Create AVD
echo "Creating AVD: $AVD_NAME"
avdmanager create avd \
  --name "$AVD_NAME" \
  --package "$PACKAGE" \
  --device "pixel_6" \
  --force

# Configure AVD (more RAM, faster storage)
AVD_CONFIG="${HOME:-}/.android/avd/${AVD_NAME}.avd/config.ini"
if [ -f "$AVD_CONFIG" ]; then
    echo "hw.ramSize=4096" >> "$AVD_CONFIG"
    echo "disk.dataPartition.size=6G" >> "$AVD_CONFIG"
    echo "hw.keyboard=yes" >> "$AVD_CONFIG"
    echo "hw.mainKeys=no" >> "$AVD_CONFIG"
    echo "AVD $AVD_NAME created and configured successfully."
else
    echo "⚠ Config file not found at $AVD_CONFIG. AVD may not be configured properly."
fi

echo "Start it with: emulator -avd $AVD_NAME -no-audio -no-boot-anim"
