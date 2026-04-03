"""Audio device management and discovery using sounddevice."""

import json
from dataclasses import dataclass
from typing import Any

import sounddevice as sd
from loguru import logger


@dataclass
class DeviceInfo:
    """Information about an audio device."""

    name: str
    is_default: bool
    channels: int
    device_type: str  # "microphone" or "speaker"
    index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "is_default": self.is_default,
            "channels": self.channels,
            "type": self.device_type,
            "index": self.index,
        }


class DeviceManager:
    """Manages audio device discovery and selection using sounddevice."""

    @staticmethod
    def list_microphones() -> list[DeviceInfo]:
        devices = []
        try:
            default_input = sd.default.device[0] if sd.default.device else None
            for idx, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    is_default = (idx == default_input)
                    devices.append(DeviceInfo(
                        name=dev['name'],
                        is_default=is_default,
                        channels=dev['max_input_channels'],
                        device_type="microphone",
                        index=idx,
                    ))
        except Exception as e:
            logger.error(f"Error listing microphones: {e}")
        return devices

    @staticmethod
    def list_speakers() -> list[DeviceInfo]:
        devices = []
        try:
            default_output = sd.default.device[1] if sd.default.device else None
            for idx, dev in enumerate(sd.query_devices()):
                if dev['max_output_channels'] > 0:
                    is_default = (idx == default_output)
                    devices.append(DeviceInfo(
                        name=dev['name'],
                        is_default=is_default,
                        channels=dev['max_output_channels'],
                        device_type="speaker",
                        index=idx,
                    ))
        except Exception as e:
            logger.error(f"Error listing speakers: {e}")
        return devices

    @staticmethod
    def get_microphone(name: str | None = None) -> tuple[int, int]:
        try:
            if name:
                for idx, dev in enumerate(sd.query_devices()):
                    if dev['max_input_channels'] > 0 and dev['name'] == name:
                        logger.info(f"Selected microphone: {name}")
                        return (idx, dev['max_input_channels'])
                logger.warning(f"Microphone '{name}' not found, using default")

            default_input = sd.default.device[0] if sd.default.device else None
            if default_input is not None:
                dev = sd.query_devices(default_input)
                logger.info(f"Using default microphone: {dev['name']}")
                return (default_input, dev['max_input_channels'])

            for idx, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    logger.info(f"Using first available microphone: {dev['name']}")
                    return (idx, dev['max_input_channels'])

            raise RuntimeError("No microphone devices found")

        except Exception as e:
            logger.error(f"Error getting microphone: {e}")
            raise

    @staticmethod
    def get_speaker_loopback(name: str | None = None) -> tuple[int, int]:
        try:
            speaker_name = None
            if name:
                speaker_name = name
            else:
                default_output = sd.default.device[1] if sd.default.device else None
                if default_output is not None:
                    speaker_dev = sd.query_devices(default_output)
                    speaker_name = speaker_dev['name']
                    logger.info(f"Using default speaker for loopback: {speaker_name}")

            best_match = None
            best_match_score = 0

            for idx, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    dev_name_lower = dev['name'].lower()
                    is_loopback = any(keyword in dev_name_lower for keyword in [
                        'stereo mix', 'wave out', 'loopback', 'what u hear', 'wasapi'
                    ])
                    matches_speaker = False
                    score = 0
                    if speaker_name:
                        speaker_lower = speaker_name.lower()
                        if speaker_lower in dev_name_lower or dev_name_lower in speaker_lower:
                            matches_speaker = True
                            score = len(set(speaker_lower.split()) & set(dev_name_lower.split()))

                    if is_loopback or matches_speaker:
                        if score > best_match_score or (is_loopback and not best_match):
                            best_match = (idx, dev['max_input_channels'], dev['name'])
                            best_match_score = score

            if best_match:
                logger.info(f"Found loopback device: {best_match[2]}")
                return (best_match[0], best_match[1])

            logger.warning("No loopback device found. Make sure 'Stereo Mix' is enabled in Windows Sound settings.")
            logger.warning("Falling back to default input device (may not capture system audio)")

            default_input = sd.default.device[0] if sd.default.device else None
            if default_input is not None:
                dev = sd.query_devices(default_input)
                return (default_input, dev['max_input_channels'])

            raise RuntimeError("No suitable loopback or input device found")

        except Exception as e:
            logger.error(f"Error getting speaker loopback: {e}")
            raise

    @staticmethod
    def test_device_format(device_idx: int, is_input: bool, samplerate: int, channels: int, blocksize: int = 1024) -> tuple[bool, str]:
        try:
            if is_input:
                with sd.InputStream(device=device_idx, channels=channels, samplerate=samplerate, blocksize=blocksize):
                    pass
            else:
                with sd.OutputStream(device=device_idx, channels=channels, samplerate=samplerate, blocksize=blocksize):
                    pass
            return (True, "")
        except Exception as e:
            return (False, f"Error: {str(e)}")

    @staticmethod
    def find_supported_samplerate(device_idx: int, is_input: bool, channels: int = 1) -> int | None:
        common_rates = [48000, 44100, 32000, 24000, 16000, 8000]
        for rate in common_rates:
            success, _ = DeviceManager.test_device_format(device_idx, is_input, rate, channels)
            if success:
                logger.info(f"Found supported sample rate: {rate}Hz")
                return rate
        return None

    @staticmethod
    def print_devices(as_json: bool = False) -> None:
        mics = DeviceManager.list_microphones()
        speakers = DeviceManager.list_speakers()
        if as_json:
            output = {
                "microphones": [m.to_dict() for m in mics],
                "speakers": [s.to_dict() for s in speakers],
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print("\n=== MICROPHONES (Input Devices) ===")
            if not mics:
                print("  (none found)")
            for mic in mics:
                default_marker = " [DEFAULT]" if mic.is_default else ""
                print(f"  • [{mic.index}] {mic.name}{default_marker}")
                print(f"    Channels: {mic.channels}")
            print("\n=== SPEAKERS (Output Devices) ===")
            if not speakers:
                print("  (none found)")
            for spk in speakers:
                default_marker = " [DEFAULT]" if spk.is_default else ""
                print(f"  • [{spk.index}] {spk.name}{default_marker}")
                print(f"    Channels: {spk.channels}")
