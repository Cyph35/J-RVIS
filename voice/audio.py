"""Microphone selection. Default: follow whatever input macOS has selected, even when it changes."""
import threading

import sounddevice as sd

import config

OUTPUT_ACTIVE = threading.Event()  # set while JARVIS is speaking


def refresh_devices() -> None:
    """Re-scan audio devices so newly plugged-in / removed mics are noticed.

    Only call this when NO audio stream is open (PortAudio caches the device list).
    """
    if OUTPUT_ACTIVE.is_set():
        return  # re-initialising PortAudio would cut off speech in progress
    try:
        sd._terminate()
        sd._initialize()
    except Exception:
        pass


def input_device() -> int | None:
    """Index of a pinned device (MIC_DEVICE substring), else None = system default input."""
    wanted = config.MIC_DEVICE.strip().lower()
    if wanted:
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0 and wanted in dev["name"].lower():
                return i
    return None


def input_name() -> str:
    idx = input_device()
    return sd.query_devices(idx if idx is not None else sd.default.device[0])["name"]
