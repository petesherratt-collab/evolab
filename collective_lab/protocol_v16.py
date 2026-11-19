"""A new contract; historical manifests and promotion verdicts are untouched."""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from .protocol_v12 import ComputePlanV12

VERSION = "causal-1.6-dev"
REASONING_CONDITIONS = (
    "single_agent", "independent_vote", "independent_synthesizer", "communicating_collective",
)
ACQUISITION_CONDITIONS = ("acquisition_single", "acquisition_collective")


@dataclass(frozen=True)
class ComputePlanV16(ComputePlanV12):
    # Equal ceilings, not a claim of equal realized compute. No padding reviews.
    target_tokens: int = 30_000
    tolerance: float = 0.0
    max_completion_tokens: int = 1_800
    minimum_completion_tokens: int = 512
    max_condition_requests: int = 7
    max_private_reviews: int = 0

    @property
    def lower_bound(self):
        return 0.0


MAX_ACQUISITION_DECISIONS = 6
DISCIPLINE = (
    "Apply the disclosed causal and probability model. Distinguish the observed signature "
    "from the latent fault. Peer reports are fallible interpretations, not additional "
    "independent observations. Use paired XOR, branch routing and polarity correction "
    "where specified. Cite only evidence in the supplied packet. Return concise JSON."
)
ACQUISITION_CONTRACT = (
    "All participants use one wallet and one shared evidence log. There are no private "
    "allocations. A buy decision purchases the whole specified dependency bundle atomically; "
    "already-owned evidence is free. Choose action=buy or action=finish explicitly. "
    "For buy, list every prerequisite in evidence_ids and explain its expected value. "
    "For finish, set evidence_ids=[] and describe remaining uncertainty, list the best "
    "remaining relevant bundle (or [] if none), and explain why stopping is worthwhile. "
    "When your listed remaining bundle is affordable, also set accept_early_stop=true "
    "to confirm deliberate stopping. Otherwise the remaining decision opportunities "
    "stay available. A normal diagnosis report does not finish acquisition."
)


def source_hashes():
    root = Path(__file__).resolve().parents[1]
    paths = sorted([*root.glob("collective_lab/*.py"), *root.glob("evolutionary_lab/*.py"),
                    *root.glob("tests/*.py"), root/"pyproject.toml",
                    root/"CAUSAL_1_6_DEVELOPMENT_DESIGN.md"])
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
