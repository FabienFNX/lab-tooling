"""Utility functions for recorder."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any


def get_timestamp() -> str:
    """Get current timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def get_monotonic_time() -> float:
    """Get monotonic time for reliable duration measurements."""
    return time.perf_counter()


def safe_path(base: Path, name: str) -> Path:
    """Create a safe path, ensuring the directory exists."""
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def format_bytes(size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_python_version() -> str:
    """Get Python version string."""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_package_versions() -> dict[str, str]:
    """Get versions of key packages."""
    import importlib.metadata

    packages = ["rich", "typer", "soundcard", "numpy", "soundfile", "pydantic", "loguru"]
    versions = {}

    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "unknown"

    return versions
