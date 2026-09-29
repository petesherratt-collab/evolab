from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import glob
import os
import resource
import time
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetrySample:
    captured_at_utc: str
    process_cpu_seconds: float
    max_rss_mb: float
    available_ram_mb: float | None
    swap_used_mb: float | None
    load_1m: float | None
    temperatures_c: dict[str, float]

    def mapping(self) -> dict[str, Any]:
        return asdict(self)


def _meminfo_mb() -> tuple[float | None, float | None]:
    try:
        values: dict[str, float] = {}
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                key, _, raw = line.partition(":")
                if raw.strip().endswith(" kB"):
                    values[key] = float(raw.strip()[:-3]) / 1024
        available = values.get("MemAvailable")
        swap_total = values.get("SwapTotal")
        swap_free = values.get("SwapFree")
        swap_used = None if swap_total is None or swap_free is None else swap_total - swap_free
        return available, swap_used
    except (OSError, ValueError):
        return None, None


def _temperatures_c() -> dict[str, float]:
    temperatures: dict[str, float] = {}
    for path in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp")):
        try:
            zone = os.path.basename(os.path.dirname(path))
            with open(path, encoding="utf-8") as handle:
                temperatures[zone] = float(handle.read().strip()) / 1000
        except (OSError, ValueError):
            continue
    return temperatures


def sample() -> TelemetrySample:
    available_ram, swap_used = _meminfo_mb()
    try:
        load_1m = os.getloadavg()[0]
    except OSError:
        load_1m = None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return TelemetrySample(
        captured_at_utc=datetime.now(timezone.utc).isoformat(),
        process_cpu_seconds=time.process_time(),
        max_rss_mb=usage.ru_maxrss / 1024,
        available_ram_mb=available_ram,
        swap_used_mb=swap_used,
        load_1m=load_1m,
        temperatures_c=_temperatures_c(),
    )
