"""
Emulator lifecycle management: start, stop, reset, snapshot.

All methods are synchronous and call SDK CLI tools via subprocess.
The FastAPI server calls these at startup/shutdown; scripts also use them directly.
"""
import os
import shutil
import subprocess
import logging
import time
from typing import Optional

from vrski.emulator.config import (
    AVD_NAME, SYSTEM_IMAGE, DEVICE_PROFILE,
    RAM_MB, STORAGE_GB, EMULATOR_FLAGS, BOOT_TIMEOUT_S,
    SNAPSHOT_LOGGEDIN,
)

logger = logging.getLogger("vrski.emulator.manager")


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    logger.info(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def sdk_tool(name: str) -> Optional[str]:
    """Resolves the full path to an Android SDK CLI tool, or None if not found."""
    path = shutil.which(name)
    if path:
        return path
    # Common install locations on macOS with Android Studio
    candidates = [
        os.path.expanduser(f"~/Library/Android/sdk/cmdline-tools/latest/bin/{name}"),
        os.path.expanduser(f"~/Library/Android/sdk/tools/bin/{name}"),
        os.path.expanduser(f"~/Android/Sdk/cmdline-tools/latest/bin/{name}"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def emulator_binary() -> Optional[str]:
    path = shutil.which("emulator")
    if path:
        return path
    candidates = [
        os.path.expanduser("~/Library/Android/sdk/emulator/emulator"),
        os.path.expanduser("~/Android/Sdk/emulator/emulator"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def avd_exists(avd_name: str = AVD_NAME) -> bool:
    avdmanager = sdk_tool("avdmanager")
    if not avdmanager:
        logger.warning("avdmanager not found — cannot verify AVD existence")
        return False
    result = _run([avdmanager, "list", "avd"])
    return avd_name in result.stdout


def create_avd(avd_name: str = AVD_NAME, force: bool = False) -> bool:
    """Creates the Vrski AVD. Idempotent if force=False and AVD already exists."""
    if not force and avd_exists(avd_name):
        logger.info(f"AVD '{avd_name}' already exists — skipping creation")
        return True

    sdkmanager = sdk_tool("sdkmanager")
    avdmanager = sdk_tool("avdmanager")
    if not sdkmanager or not avdmanager:
        logger.error("sdkmanager or avdmanager not found — cannot create AVD")
        return False

    logger.info(f"Installing system image: {SYSTEM_IMAGE}")
    r = _run([sdkmanager, "--install", SYSTEM_IMAGE, "platform-tools", "emulator"], timeout=600)
    if r.returncode != 0:
        logger.error(f"sdkmanager failed: {r.stderr}")
        return False

    logger.info(f"Creating AVD: {avd_name}")
    r = _run([
        avdmanager, "create", "avd",
        "--name", avd_name,
        "--package", SYSTEM_IMAGE,
        "--device", DEVICE_PROFILE,
        "--force",
    ])
    if r.returncode != 0:
        logger.error(f"avdmanager create failed: {r.stderr}")
        return False

    # Write RAM / storage overrides into config.ini
    config_path = os.path.expanduser(f"~/.android/avd/{avd_name}.avd/config.ini")
    if os.path.exists(config_path):
        with open(config_path, "a") as f:
            f.write(f"\nhw.ramSize={RAM_MB}\n")
            f.write(f"disk.dataPartition.size={STORAGE_GB}G\n")
            f.write("hw.keyboard=yes\n")
            f.write("hw.mainKeys=no\n")
        logger.info(f"AVD config written: {config_path}")

    return True


def start_emulator(avd_name: str = AVD_NAME) -> Optional[subprocess.Popen]:
    """Starts the emulator in the background and returns the Popen handle."""
    binary = emulator_binary()
    if not binary:
        logger.error("emulator binary not found")
        return None

    cmd = [binary, "-avd", avd_name] + EMULATOR_FLAGS
    logger.info(f"Starting emulator: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc


def wait_for_boot(serial: str = "emulator-5554", timeout: int = BOOT_TIMEOUT_S) -> bool:
    """Polls sys.boot_completed until the emulator is fully booted."""
    logger.info(f"Waiting for {serial} to boot (timeout={timeout}s)...")
    adb = shutil.which("adb") or "adb"
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            [adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip() == "1":
            logger.info(f"{serial} is fully booted")
            return True
        time.sleep(3)
    logger.error(f"Emulator did not boot within {timeout}s")
    return False


def stop_emulator(serial: str = "emulator-5554") -> bool:
    """Gracefully shuts down the emulator."""
    adb = shutil.which("adb") or "adb"
    r = _run([adb, "-s", serial, "emu", "kill"])
    return r.returncode == 0


def save_snapshot(serial: str = "emulator-5554", snapshot: str = SNAPSHOT_LOGGEDIN) -> bool:
    """Saves an AVD snapshot (use after Play Store login as a recovery point)."""
    adb = shutil.which("adb") or "adb"
    r = _run([adb, "-s", serial, "emu", "avd", "snapshot", "save", snapshot], timeout=120)
    if r.returncode == 0:
        logger.info(f"Snapshot '{snapshot}' saved on {serial}")
        return True
    logger.error(f"Failed to save snapshot: {r.stderr}")
    return False


def restore_snapshot(serial: str = "emulator-5554", snapshot: str = SNAPSHOT_LOGGEDIN) -> bool:
    """Restores an AVD snapshot."""
    adb = shutil.which("adb") or "adb"
    r = _run([adb, "-s", serial, "emu", "avd", "snapshot", "load", snapshot], timeout=120)
    if r.returncode == 0:
        logger.info(f"Snapshot '{snapshot}' restored on {serial}")
        return True
    logger.error(f"Failed to restore snapshot: {r.stderr}")
    return False


def wipe_data(avd_name: str = AVD_NAME) -> bool:
    """Wipes the AVD user data partition (cold reset). Emulator must be stopped first."""
    binary = emulator_binary()
    if not binary:
        return False
    r = _run([binary, "-avd", avd_name, "-wipe-data", "-no-window", "-quit-after-boot", "1"])
    return r.returncode == 0
