import platform
import shutil
import subprocess
from datetime import datetime


def get_current_time() -> str:
    return datetime.now().astimezone().strftime("%A, %B %d, %Y, %I:%M %p %Z")


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()


def get_system_info() -> str:
    """Read-only basics: macOS, chip, RAM, free disk, battery."""
    ram_gb = int(_run(["sysctl", "-n", "hw.memsize"]) or 0) / 2**30
    chip = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    disk = shutil.disk_usage("/")
    batt = _run(["pmset", "-g", "batt"]).splitlines()
    battery = batt[1].split("\t")[-1] if len(batt) > 1 else "no battery info"
    return (
        f"macOS {platform.mac_ver()[0]}, {chip}, {ram_gb:.0f} GB RAM, "
        f"{disk.free / 2**30:.0f} GB free on the system disk, battery: {battery}"
    )
