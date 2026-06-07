#!/bin/bash
# ============================================================================
#  Vrski — One-Time Human Google Sign-In
# ============================================================================
#  Run this ONCE. It boots the Android emulator, opens the Google Play Store
#  sign-in screen, and waits while YOU sign in with your Google account.
#
#  Why a human does this: Google protects new sign-ins with 2-Step
#  Verification (a "tap 35 on your phone" prompt). Only you can approve that.
#  After you sign in once, the account stays on the emulator and your AI
#  agent can use it forever — you never have to do this again.
#
#  Usage:   bash scripts/login.sh
# ============================================================================

set -uo pipefail

AVD_NAME="vrski_dev"
SERIAL="emulator-5554"
EMULATOR_PID=""
STARTED_EMULATOR="no"

# ---- Resolve JAVA_HOME (needed by the emulator) ----------------------------
if [ -z "${JAVA_HOME:-}" ] && [ -d "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
fi

# ---- Resolve Android SDK ---------------------------------------------------
ANDROID_SDK_PATHS=(
    "${HOME:-}/Library/Android/sdk"
    "/Library/Android/sdk"
    "/opt/homebrew/share/android-commandlinetools"
)
SDK_ROOT=""
for path in "${ANDROID_SDK_PATHS[@]}"; do
    if [ -d "$path" ]; then SDK_ROOT="$path"; break; fi
done
if [ -n "$SDK_ROOT" ]; then
    export PATH="$SDK_ROOT/platform-tools:$SDK_ROOT/emulator:$PATH"
fi

if ! command -v adb >/dev/null 2>&1; then
    echo "ERROR: 'adb' not found. Install the Android SDK first (see README)."
    exit 1
fi

echo "============================================================"
echo "  Vrski — One-Time Google Sign-In"
echo "============================================================"
echo ""

# ---- Is the AVD created? ---------------------------------------------------
if ! emulator -list-avds 2>/dev/null | grep -q "^${AVD_NAME}$"; then
    echo "ERROR: AVD '${AVD_NAME}' not found."
    echo "Create it first:   bash scripts/setup_avd.sh"
    exit 1
fi

# ---- Boot the emulator (reuse if already running) --------------------------
if adb devices | grep -q "^${SERIAL}[[:space:]]*device$"; then
    echo "[1/4] Emulator already running — reusing it."
else
    echo "[1/4] Starting the emulator window (this opens a phone on your screen)..."
    # NOTE: window IS shown on purpose — you need to see it to sign in.
    emulator -avd "$AVD_NAME" -no-audio -no-boot-anim -gpu swiftshader_indirect >/dev/null 2>&1 &
    EMULATOR_PID=$!
    STARTED_EMULATOR="yes"

    echo "[2/4] Waiting for the phone to finish booting..."
    adb wait-for-device
    tries=0
    while [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]; do
        sleep 3
        tries=$((tries + 1))
        if [ "$tries" -gt 60 ]; then
            echo "ERROR: Emulator did not boot within ~3 minutes."
            exit 1
        fi
    done
    sleep 2
fi
echo "       Phone is ready."

# ---- Open the Google Play Store sign-in screen -----------------------------
echo "[3/4] Opening the Google Play Store sign-in screen..."
adb shell am force-stop com.android.vending >/dev/null 2>&1
sleep 1
adb shell am start -n com.android.vending/.AssetBrowserActivity >/dev/null 2>&1
sleep 3

echo ""
echo "------------------------------------------------------------"
echo "  >>> ACTION NEEDED — look at the emulator window <<<"
echo "------------------------------------------------------------"
echo ""
echo "  1. Tap 'Sign in' in the Play Store."
echo "  2. Enter your Google email and password."
echo "  3. If Google asks to verify it's you, approve the prompt"
echo "     on your real phone (tap the matching number)."
echo "  4. Accept any terms until you reach the Play Store home."
echo ""
echo "  Take your time. When you can see the Play Store home"
echo "  screen (with the search bar), come back here."
echo ""
read -r -p "  Press [Enter] once you have signed in... " _

# ---- Verify the account is signed in ---------------------------------------
echo ""
echo "[4/4] Checking the signed-in account..."
ACCOUNT="$(adb shell dumpsys account 2>/dev/null | grep -oE '[a-zA-Z0-9._%+-]+@gmail\.com' | head -1 | tr -d '\r')"

if [ -n "$ACCOUNT" ]; then
    echo ""
    echo "  ✓ Signed in as: $ACCOUNT"

    # Best-effort: save a fast-boot snapshot of the logged-in state.
    echo "  Saving a logged-in snapshot (for faster startup later)..."
    adb -s "$SERIAL" emu avd snapshot save vrski_loggedin >/dev/null 2>&1 \
        && echo "  ✓ Snapshot 'vrski_loggedin' saved." \
        || echo "  (snapshot skipped — not critical; the account is saved anyway)"
else
    echo ""
    echo "  ⚠ Could not detect a signed-in Google account yet."
    echo "    If you are sure you finished, re-run this script and try again."
fi

# ---- Offer to shut the emulator down ---------------------------------------
echo ""
echo "------------------------------------------------------------"
if [ "$STARTED_EMULATOR" = "yes" ]; then
    read -r -p "  Close the emulator now? [Y/n] " ANSWER
    case "${ANSWER:-Y}" in
        [nN]*)
            echo "  Leaving the emulator running."
            ;;
        *)
            echo "  Closing the emulator..."
            adb -s "$SERIAL" emu kill >/dev/null 2>&1 || true
            sleep 2
            echo "  ✓ Emulator closed."
            ;;
    esac
else
    echo "  (You started this emulator yourself — leaving it as is.)"
    echo "  To close it manually:  adb -s $SERIAL emu kill"
fi

echo ""
echo "============================================================"
echo "  DONE. Your Google account is now on the Vrski emulator."
echo ""
echo "  Next: go to your Hermes agent and say —"
echo ""
echo "    \"I've signed into Vrski. Wire yourself up to it.\""
echo "    and tag the file  @VRSKIAGENT.md"
echo ""
echo "  The agent will start Vrski and take it from there."
echo "============================================================"
