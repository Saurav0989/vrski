"""
AVD configuration constants for Vrski.

Target: API 34, arm64-v8a, Google Play system image — the most stable
combination on Apple Silicon (M1/M2/M3/M4).
"""

AVD_NAME = "vrski_dev"
SYSTEM_IMAGE = "system-images;android-34;google_apis_playstore;arm64-v8a"
DEVICE_PROFILE = "pixel_6"
API_LEVEL = 34
RAM_MB = 4096
STORAGE_GB = 6
EMULATOR_SERIAL = "emulator-5554"

# Emulator launch flags — optimised for headless CI and Apple Silicon
EMULATOR_FLAGS = [
    "-no-audio",
    "-no-boot-anim",
    "-gpu", "swiftshader_indirect",
]

# How long (seconds) to wait for sys.boot_completed after starting the emulator
BOOT_TIMEOUT_S = 120

# Snapshot name saved after a successful Play Store login (recovery point)
SNAPSHOT_LOGGEDIN = "vrski_loggedin"
