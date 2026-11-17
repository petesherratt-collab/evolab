from dataclasses import dataclass

from .protocol_v13 import PERSPECTIVE_LENSES, lens_charter
from .protocol_v14 import ComputePlanV14, V14_CONDITIONS

CAUSAL_V15_PROTOCOL_VERSION = "causal-1.5-dev"
V15_CONDITIONS = V14_CONDITIONS


@dataclass(frozen=True)
class ComputePlanV15(ComputePlanV14):
    """Preserve the common 25k–30k envelope and all existing request limits."""


EVIDENCE_DISCIPLINE = (
    "Treat proposals as hypotheses, not observations. Apply the purchased interpretation "
    "rules: match named reference/trace pairs for XOR; resolve the active branch; "
    "correct physical bits using calibration. You may intersect explicitly disclosed "
    "compatibility constraints after those prerequisites are resolved. This is distinct "
    "from multiplying correlated probabilities as if independent. Do not demand "
    "additional unspecified dependencies after the disclosed prerequisites are satisfied. "
    "Preserve residual uncertainty and justify diagnosis changes with acquired evidence. "
    "Return compact JSON with at most three rationale sentences."
)


def acquisition_schedule(max_rounds, round_index, tools_available):
    remaining = max(0, max_rounds-round_index) if tools_available else 0
    return (
        f"Acquisition schedule: {max_rounds} tool-enabled rounds per episode; "
        f"{remaining} remaining including this call. "
        "One buy_evidence call may request multiple evidence_ids; each item is charged. "
        "Read the topology registry before choosing ambiguous lane options. Use its "
        "interpretation registry to plan complete dependency bundles. Batch required "
        "items that fit your own remaining stage/agent budget; do not plan one item "
        "per future round when those rounds do not exist. Never assume another agent's "
        "budget is yours. Later private reviews cannot buy evidence. "
        + ("This is the last acquisition round; include all currently known affordable "
           "prerequisites needed for your chosen diagnostic bundle." if remaining == 1 else "")
    )
