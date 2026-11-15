from __future__ import annotations

from dataclasses import asdict, dataclass

from .protocol_v12 import ComputePlanV12, V12_CONDITIONS


CAUSAL_V13_PROTOCOL_VERSION = "causal-1.3-dev"
V13_CONDITIONS = V12_CONDITIONS


@dataclass(frozen=True)
class PerspectiveLens:
    lens_id: str
    title: str
    instruction: str

    def mapping(self) -> dict[str, str]:
        return asdict(self)


PERSPECTIVE_LENSES = (
    PerspectiveLens(
        "causal_support",
        "Causal support",
        "Identify direct support and the cheapest observation that could falsify it.",
    ),
    PerspectiveLens(
        "dependency",
        "Dependency structure",
        "Track joint, paired, routed, and conditional evidence; reject marginal-only reasoning.",
    ),
    PerspectiveLens(
        "provenance",
        "Provenance and confounding",
        "Audit shared sources, calibration, stale proxies, and latent common causes.",
    ),
    PerspectiveLens(
        "resource_adversary",
        "Resource adversary",
        "Challenge the acquisition plan for decoys, duplicated spend, and unaffordable branches.",
    ),
)


def lens_charter() -> tuple[dict[str, str], ...]:
    """Return the information-equivalent charter shown to every condition.

    A single agent receives all four lenses. Independent agents and communicating
    deliberators each receive one lens, but no condition receives private task
    metadata or additional telemetry.
    """

    return tuple(lens.mapping() for lens in PERSPECTIVE_LENSES)


@dataclass(frozen=True)
class ComputePlanV13(ComputePlanV12):
    """Causal-1.3 keeps the proven causal-1.2 compute envelope unchanged."""
