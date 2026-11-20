"""Microphone selection."""
import sounddevice as sd

import config


def input_device() -> int | None:
    """Index of the first input device whose name contains MIC_DEVICE, else None (system default)."""
    wanted = config.MIC_DEVICE.strip().lower()
    if wanted:
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0 and wanted in dev["name"].lower():
                return i
    return None


def input_name() -> str:
    idx = input_device()
    return sd.query_devices(idx if idx is not None else sd.default.device[0])["name"]
