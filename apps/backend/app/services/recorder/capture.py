"""Audio capture from microphone and system loopback using sounddevice."""

import threading
from typing import Any

import numpy as np
import sounddevice as sd
from loguru import logger

from app.services.recorder.meters import AudioMeter, create_meter
from app.services.recorder.util import get_monotonic_time
from app.services.recorder.writer import AudioBlock, WavWriter


class AudioCapture:
    """Base class for audio capture using sounddevice."""

    def __init__(
        self,
        device_idx: int,
        channels: int,
        writer: WavWriter,
        samplerate: int,
        blocksize: int,
        name: str,
    ):
        self.device_idx = device_idx
        self.channels = channels
        self.writer = writer
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.name = name

        self.meter = create_meter()
        self.is_running = False
        self.thread: threading.Thread | None = None

        self.block_index = 0
        self.total_frames = 0

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=False)
        self.thread.start()
        logger.info(f"Started {self.name} capture")

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info(f"Stopped {self.name} capture ({self.total_frames} frames)")

    def _capture_loop(self) -> None:
        try:
            with sd.InputStream(
                device=self.device_idx,
                channels=self.channels,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                dtype=np.float32,
            ) as stream:
                logger.info(f"{self.name} recorder initialized: {self.samplerate}Hz, blocksize={self.blocksize}, channels={self.channels}")

                while self.is_running:
                    try:
                        data, overflowed = stream.read(self.blocksize)

                        if overflowed:
                            logger.warning(f"{self.name}: Input overflow detected (audio buffer overrun)")

                        if data.dtype != np.float32:
                            data = data.astype(np.float32, copy=False)

                        if data.ndim > 1:
                            meter_data = np.mean(data, axis=1, dtype=np.float32)
                        else:
                            meter_data = data

                        self.meter.update(meter_data)

                        timestamp = get_monotonic_time()
                        block = AudioBlock(
                            data=data,
                            timestamp=timestamp,
                            block_index=self.block_index,
                        )

                        self.writer.write(block)

                        self.block_index += 1
                        self.total_frames += len(data)

                    except Exception as e:
                        logger.error(f"Error recording {self.name} block: {e}")
                        if not self.is_running:
                            break

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error setting up {self.name} recorder: {error_msg}")
            self.is_running = False

    def get_latest_data(self) -> tuple[np.ndarray, float, int]:
        return np.array([], dtype=np.float32), get_monotonic_time(), self.block_index


class MicrophoneCapture(AudioCapture):
    def __init__(self, device_idx: int, channels: int, writer: WavWriter, samplerate: int, blocksize: int):
        super().__init__(device_idx, channels, writer, samplerate, blocksize, "Microphone")


class LoopbackCapture(AudioCapture):
    def __init__(self, device_idx: int, channels: int, writer: WavWriter, samplerate: int, blocksize: int):
        super().__init__(device_idx, channels, writer, samplerate, blocksize, "System")


class RecordingSession:
    """Manages a complete recording session with mic and/or system capture."""

    def __init__(
        self,
        mic_capture: MicrophoneCapture | None,
        sys_capture: LoopbackCapture | None,
    ):
        self.mic_capture = mic_capture
        self.sys_capture = sys_capture
        self.start_time = 0.0

    def start(self) -> None:
        self.start_time = get_monotonic_time()

        if self.mic_capture:
            self.mic_capture.writer.start()
        if self.sys_capture:
            self.sys_capture.writer.start()

        if self.mic_capture:
            self.mic_capture.start()
        if self.sys_capture:
            self.sys_capture.start()

        logger.info("Recording session started")

    def stop(self) -> None:
        if self.mic_capture:
            self.mic_capture.stop()
        if self.sys_capture:
            self.sys_capture.stop()

        if self.mic_capture:
            self.mic_capture.writer.stop()
        if self.sys_capture:
            self.sys_capture.writer.stop()

        duration = get_monotonic_time() - self.start_time
        logger.info(f"Recording session stopped (duration: {duration:.2f}s)")

    def get_duration(self) -> float:
        if self.start_time == 0.0:
            return 0.0
        return get_monotonic_time() - self.start_time

    def get_stats(self) -> dict[str, Any]:
        def empty_stats() -> dict[str, Any]:
            return {
                "available": False,
                "frames": 0,
                "blocks": 0,
                "dropped": 0,
                "file_size": 0,
            }

        mic_stats = empty_stats()
        if self.mic_capture:
            mic_stats = {
                "available": True,
                "frames": self.mic_capture.total_frames,
                "blocks": self.mic_capture.block_index,
                "dropped": self.mic_capture.writer.dropped_blocks,
                "file_size": self.mic_capture.writer.get_file_size(),
            }

        sys_stats = empty_stats()
        if self.sys_capture:
            sys_stats = {
                "available": True,
                "frames": self.sys_capture.total_frames,
                "blocks": self.sys_capture.block_index,
                "dropped": self.sys_capture.writer.dropped_blocks,
                "file_size": self.sys_capture.writer.get_file_size(),
            }

        return {
            "duration": self.get_duration(),
            "mic": mic_stats,
            "system": sys_stats,
        }
