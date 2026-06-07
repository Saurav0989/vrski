import os
import subprocess
import shutil
import logging
from typing import List, Optional

logger = logging.getLogger("vrski.adb")

class ADBClient:
    def __init__(self, serial: Optional[str] = None, mock: Optional[bool] = None):
        self.serial = serial
        
        # Determine if we should run in mock mode
        if mock is not None:
            self.mock = mock
        else:
            # Auto-detect mock mode: either explicit env var, or adb is missing from path
            env_mock = os.environ.get("VRSKI_MOCK", "").lower() in ("1", "true", "yes")
            adb_exists = shutil.which("adb") is not None
            self.mock = env_mock or not adb_exists
            
        if self.mock:
            logger.info("ADBClient initialized in MOCK mode")
        else:
            logger.info(f"ADBClient initialized (serial: {self.serial})")
            
        self.mock_packages = [
            "com.android.settings",
            "com.android.vending",
            "com.whatsapp",
            "com.instagram.android",
            "com.google.android.gms"
        ]

    def _get_base_cmd(self) -> List[str]:
        if self.serial:
            return ["adb", "-s", self.serial]
        return ["adb"]

    def run_cmd(self, args: List[str], capture_output: bool = True, timeout: int = 20) -> subprocess.CompletedProcess:
        """Runs an ADB command. In mock mode, simulates the run."""
        if self.mock:
            # Simulate a successful execution
            # Special parsing mock behaviors
            stdout = b""
            stderr = b""
            returncode = 0
            
            # Simple simulation logic based on command
            if len(args) >= 2 and args[0] == "shell" and args[1] == "pm" and "list" in args and "packages" in args:
                stdout_str = "\n".join([f"package:{p}" for p in self.mock_packages]) + "\n"
                stdout = stdout_str.encode("utf-8")
            
            return subprocess.CompletedProcess(
                args=args,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr
            )
            
        cmd = self._get_base_cmd() + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                check=False,
                text=True if capture_output else False,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"ADB command timed out after {timeout}s: {' '.join(cmd)}")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-1,
                stdout="" if capture_output else b"",
                stderr=f"TimeoutExpired: ADB execution timed out after {timeout} seconds".encode("utf-8") if not capture_output else f"TimeoutExpired: ADB execution timed out after {timeout} seconds"
            )
        except FileNotFoundError:
            # Fallback if adb was not found during execution
            logger.warning("adb command not found. Falling back to mock behavior.")
            self.mock = True
            return self.run_cmd(args, capture_output, timeout=timeout)

    def install_apk(self, path: str) -> bool:
        """Installs an APK file to the device."""
        if self.mock:
            logger.info(f"[Mock] Installing APK from {path}")
            return True
            
        result = self.run_cmd(["install", "-r", path])
        if result.returncode == 0:
            logger.info(f"Successfully installed APK: {path}")
            return True
        logger.error(f"Failed to install APK {path}: {result.stderr}")
        return False

    def uninstall_package(self, package: str) -> bool:
        """Uninstalls a package from the device."""
        if self.mock:
            logger.info(f"[Mock] Uninstalling package {package}")
            if package in self.mock_packages:
                self.mock_packages.remove(package)
            return True
            
        result = self.run_cmd(["uninstall", package])
        return result.returncode == 0

    def launch_package(self, package: str) -> bool:
        """Launches an app package using the monkey tool."""
        if self.mock:
            logger.info(f"[Mock] Launching package {package}")
            return True
            
        # Standard way to launch a package by name without knowing the main activity
        result = self.run_cmd(["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
        return result.returncode == 0

    def force_stop(self, package: str) -> bool:
        """Force stops an app package."""
        if self.mock:
            logger.info(f"[Mock] Force stopping package {package}")
            return True
            
        result = self.run_cmd(["shell", "am", "force-stop", package])
        return result.returncode == 0

    def list_packages(self) -> List[str]:
        """Lists all installed packages on the device."""
        result = self.run_cmd(["shell", "pm", "list", "packages"])
        if result.returncode != 0:
            return []
            
        stdout = result.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8")
            
        packages = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.replace("package:", ""))
        return packages

    def is_installed(self, package: str) -> bool:
        """Checks if a package is installed."""
        if self.mock:
            return package in self.mock_packages
        return package in self.list_packages()

    def key_back(self) -> bool:
        """Sends a BACK key event."""
        return self.key_event(4)

    def key_home(self) -> bool:
        """Sends a HOME key event."""
        return self.key_event(3)

    def key_recent_apps(self) -> bool:
        """Sends a APP_SWITCH (recent apps) key event."""
        return self.key_event(187)

    def key_event(self, keycode: int) -> bool:
        """Sends a generic key event."""
        if self.mock:
            logger.info(f"[Mock] Sending key event {keycode}")
            return True
            
        result = self.run_cmd(["shell", "input", "keyevent", str(keycode)])
        return result.returncode == 0

    def raw_tap(self, x: int, y: int) -> bool:
        """Performs a raw coordinate tap."""
        if self.mock:
            logger.info(f"[Mock] Raw tap at ({x}, {y})")
            return True
            
        result = self.run_cmd(["shell", "input", "tap", str(x), str(y)])
        return result.returncode == 0

    def screenshot(self, local_path: str, timeout: int = 20) -> bool:
        """Takes a screenshot and saves it to local_path."""
        if self.mock:
            logger.info(f"[Mock] Saving mock screenshot to {local_path}")
            # Write a dummy 1x1 pixel PNG file or a tiny valid image
            # 1x1 transparent pixel PNG in hex
            dummy_png = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00"
                b"\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            try:
                os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(dummy_png)
                return True
            except Exception as e:
                logger.error(f"Failed to write mock screenshot: {e}")
                return False
                
        # Non-mock implementation using exec-out screencap for performance
        try:
            cmd = self._get_base_cmd() + ["exec-out", "screencap", "-p"]
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            with open(local_path, "wb") as f:
                subprocess.run(cmd, stdout=f, check=True, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to capture screenshot via exec-out: {e}")
            # Fallback to shell + pull (automatically protected by run_cmd timeouts)
            try:
                self.run_cmd(["shell", "screencap", "-p", "/sdcard/screencap.png"], timeout=timeout)
                self.run_cmd(["pull", "/sdcard/screencap.png", local_path], timeout=timeout)
                self.run_cmd(["shell", "rm", "/sdcard/screencap.png"], timeout=timeout)
                return True
            except Exception as e2:
                logger.error(f"Screenshot fallback also failed: {e2}")
                return False

    def connect(self, serial: Optional[str] = None) -> bool:
        """Connects to the device. For ADBClient, connection is implicit via subprocess."""
        if serial:
            self.serial = serial
        if self.mock:
            logger.info(f"[Mock] ADB connected (serial: {self.serial or 'default'})")
            return True
        # Verify adb can see a device
        result = self.run_cmd(["devices"])
        return result.returncode == 0

    def tap(self, x: int, y: int) -> bool:
        """Performs a tap at coordinates (x, y). Alias for raw_tap."""
        return self.raw_tap(x, y)

    def type_text(self, text: str) -> bool:
        """Types text using ADB input text command."""
        if self.mock:
            logger.info(f"[Mock] Typing text: '{text}'")
            return True
        # Escape special characters for shell
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        result = self.run_cmd(["shell", "input", "text", escaped])
        return result.returncode == 0
