"""WAV file writers for audio recording."""

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import soundfile as sf
from loguru import logger


@dataclass
class AudioBlock:
    """A block of audio data with metadata."""

    data: npt.NDArray[np.floating[Any]]  # type: ignore
    timestamp: float
    block_index: int


class WavWriter:
    """Thread-safe WAV file writer that consumes audio blocks from a queue."""

    def __init__(
        self,
        path: Path,
        samplerate: int,
        channels: int,
        subtype: str | None = None,
        file_format: str | None = None,
        queue_maxsize: int = 100,
    ):
        self.path = path
        self.samplerate = samplerate
        self.channels = channels
        self.file_format = file_format
        self.subtype = subtype or self._default_subtype(file_format)

        self.queue: queue.Queue[AudioBlock | None] = queue.Queue(maxsize=queue_maxsize)
        self.thread: threading.Thread | None = None
        self.is_running = False

        self.frames_written = 0
        self.dropped_blocks = 0

        self._file: sf.SoundFile | None = None

    def start(self) -> None:
        """Start the writer thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._write_loop, daemon=False)
        self.thread.start()
        logger.info(f"Started writer for {self.path}")

    def stop(self) -> None:
        """Stop the writer thread and close the file."""
        if not self.is_running:
            return
        self.is_running = False
        self.queue.put(None)
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info(f"Stopped writer for {self.path} ({self.frames_written} frames written)")

    def write(self, block: AudioBlock) -> bool:
        """Write an audio block (non-blocking). Returns False if queue was full (dropped)."""
        try:
            self.queue.put(block, block=False)
            return True
        except queue.Full:
            self.dropped_blocks += 1
            logger.warning(f"Dropped block {block.block_index} for {self.path}")
            return False

    def _write_loop(self) -> None:
        """Main write loop (runs in thread)."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = sf.SoundFile(
                str(self.path),
                mode="w",
                samplerate=self.samplerate,
                channels=self.channels,
                subtype=self.subtype,
                format=self.file_format,
            )

            while self.is_running:
                try:
                    block = self.queue.get(timeout=0.1)
                    if block is None:
                        break
                    self._file.write(block.data)
                    self.frames_written += len(block.data)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error writing block: {e}")

        except Exception as e:
            logger.error(f"Error in write loop: {e}")
        finally:
            if self._file:
                try:
                    self._file.close()
                except Exception as e:
                    logger.error(f"Error closing file: {e}")

    def get_file_size(self) -> int:
        if self.path.exists():
            return self.path.stat().st_size
        return 0

    @staticmethod
    def _default_subtype(file_format: str | None) -> str:
        if file_format == "MP3":
            return "MPEG_LAYER_III"
        return "PCM_16"


class MixWriter:
    """Write a mixdown of two audio sources to a WAV file."""

    def __init__(
        self,
        path: Path,
        samplerate: int,
        channels: int,
        mic_gain: float = 1.0,
        sys_gain: float = 1.0,
        subtype: str | None = None,
        file_format: str | None = None,
    ):
        self.writer = WavWriter(path, samplerate, channels, subtype, file_format)
        self.mic_gain = mic_gain
        self.sys_gain = sys_gain
        self.channels = channels

    def start(self) -> None:
        self.writer.start()

    def stop(self) -> None:
        self.writer.stop()

    def write_mix(
        self,
        mic_data: npt.NDArray[np.floating[Any]],  # type: ignore
        sys_data: npt.NDArray[np.floating[Any]],  # type: ignore
        timestamp: float,
        block_index: int,
    ) -> bool:
        try:
            min_len = min(len(mic_data), len(sys_data))
            mic_data = mic_data[:min_len]
            sys_data = sys_data[:min_len]

            mixed = mic_data * self.mic_gain + sys_data * self.sys_gain

            if mixed.ndim == 1 and self.channels > 1:
                mixed = np.column_stack([mixed] * self.channels)
            elif mixed.ndim == 2 and mixed.shape[1] != self.channels:
                if mixed.shape[1] > self.channels:
                    mixed = mixed[:, :self.channels]
                else:
                    padding = np.zeros((mixed.shape[0], self.channels - mixed.shape[1]))
                    mixed = np.column_stack([mixed, padding])

            block = AudioBlock(data=mixed, timestamp=timestamp, block_index=block_index)
            return self.writer.write(block)

        except Exception as e:
            logger.error(f"Error mixing audio: {e}")
            return False

    @property
    def frames_written(self) -> int:
        return self.writer.frames_written

    @property
    def dropped_blocks(self) -> int:
        return self.writer.dropped_blocks

    def get_file_size(self) -> int:
        return self.writer.get_file_size()
