from dataclasses import dataclass

from .protocol_v13 import ComputePlanV13, V13_CONDITIONS

CAUSAL_V14_PROTOCOL_VERSION = "causal-1.4-dev"
V14_CONDITIONS = V13_CONDITIONS


@dataclass(frozen=True)
class ComputePlanV14(ComputePlanV13):
    """One 25k–30k envelope for every task; report recovery shares this budget."""

    max_completion_tokens: int = 1800
    minimum_completion_tokens: int = 512


EVIDENCE_DISCIPLINE = (
    "Treat other agents' proposals and confidence as hypotheses, not observations. "
    "For relational evidence, resolve routing and polarity before combining channels; "
    "list unresolved dependencies instead of intersecting marginal candidate sets. "
    "Before changing a diagnosis, identify the purchased evidence and causal relation "
    "that warrants the change. Retain uncertainty when that relation is unresolved. "
    "Return compact JSON; keep the rationale to at most three sentences."
)
