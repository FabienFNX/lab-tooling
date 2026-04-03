"""Audio level meters and calculations."""

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt


@dataclass
class MeterState:
    """State of an audio level meter."""

    rms: float = 0.0
    peak: float = 0.0
    db_rms: float = -60.0
    db_peak: float = -60.0


class AudioMeter:
    """Calculate audio levels (RMS, peak, dB) from audio buffers."""

    def __init__(self, epsilon: float = 1e-10, db_min: float = -60.0, db_max: float = 0.0):
        self.epsilon = epsilon
        self.db_min = db_min
        self.db_max = db_max
        self.state = MeterState()

    def update(self, data: npt.NDArray[np.floating[Any]]) -> MeterState:  # type: ignore
        if data.size == 0:
            return self.state

        rms = float(np.sqrt(np.mean(data ** 2)))
        peak = float(np.max(np.abs(data)))
        db_rms = self._to_db(rms)
        db_peak = self._to_db(peak)

        self.state = MeterState(rms=rms, peak=peak, db_rms=db_rms, db_peak=db_peak)
        return self.state

    def _to_db(self, value: float) -> float:
        if value < self.epsilon:
            return self.db_min
        db = 20.0 * math.log10(value)
        return max(self.db_min, min(self.db_max, db))

    def get_bar_string(self, width: int = 40) -> str:
        db_range = self.db_max - self.db_min
        normalized = (self.state.db_rms - self.db_min) / db_range
        normalized = max(0.0, min(1.0, normalized))
        filled = int(normalized * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    def get_level_string(self) -> str:
        return f"RMS: {self.state.db_rms:+.1f}dB  Peak: {self.state.db_peak:+.1f}dB"


def create_meter() -> AudioMeter:
    return AudioMeter()
