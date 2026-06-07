#!/bin/bash
set -euo pipefail

# check_deps.sh - Verify system dependencies for Vrski

echo "Checking dependencies for Vrski..."

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

# Try to find android SDK root
SDK_ROOT=""
for path in "${ANDROID_SDK_PATHS[@]}"; do
    if [ -d "$path" ]; then
        SDK_ROOT="$path"
        break
    fi
done

if [ -n "$SDK_ROOT" ]; then
    echo "✓ Found Android SDK at: $SDK_ROOT"
    # Add to path for this check
    export PATH="$SDK_ROOT/platform-tools:$SDK_ROOT/emulator:$SDK_ROOT/cmdline-tools/latest/bin:$PATH"
else
    echo "⚠ Android SDK directory not found in common locations."
fi

# Check ADB
if command -v adb &> /dev/null; then
    echo "✓ ADB is installed: $(adb --version | head -n 1)"
else
    echo "✗ ADB is NOT installed or not in PATH."
    echo "  Hint: Install platform-tools or set export PATH=\$PATH:~/Library/Android/sdk/platform-tools"
fi

# Check Emulator
if command -v emulator &> /dev/null; then
    echo "✓ Emulator is installed: $(emulator -version | head -n 1)"
else
    echo "✗ Emulator is NOT installed or not in PATH."
    echo "  Hint: Install emulator or set export PATH=\$PATH:~/Library/Android/sdk/emulator"
fi

# Check Python
if command -v python3 &> /dev/null; then
    echo "✓ Python3 is installed: $(python3 --version)"
else
    echo "✗ Python3 is NOT installed."
fi

# Check UV (or pip)
if command -v uv &> /dev/null; then
    echo "✓ uv is installed: $(uv --version)"
elif command -v pip3 &> /dev/null; then
    echo "✓ pip3 is installed: $(pip3 --version)"
else
    echo "✗ Neither uv nor pip3 was found."
fi

echo "Dependency check complete."
