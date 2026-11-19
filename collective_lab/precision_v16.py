"""Prospective precision calculations; never generates experimental task seeds."""
from __future__ import annotations

import argparse
import json
import math
from statistics import NormalDist, mean, variance

from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES

CELLS = tuple((kind, band) for kind in CAUSAL_TASK_CLASSES for band in DIFFICULTIES)


def planning_scenario(sd, *, effect=.05, half_width=.05, confidence=.95, power=.80, n=30):
    if (not all(math.isfinite(v) and v > 0 for v in (sd, effect, half_width)) or
            not .5 < confidence < 1 or not .5 < power < 1 or type(n) is not int or n < 2):
        raise ValueError("INVALID_PRECISION_INPUT")
    normal = NormalDist()
    z = normal.inv_cdf((1+confidence)/2)
    precision_n = math.ceil((z*sd/half_width)**2)
    power_n = math.ceil(((z+normal.inv_cdf(power))*sd/effect)**2)
    noncentrality = effect*math.sqrt(n)/sd
    return {"paired_sd": sd, "n": n, "approximate_half_width": z*sd/math.sqrt(n),
            "approximate_power": 1-normal.cdf(z-noncentrality)+normal.cdf(-z-noncentrality),
            "normal_approximation_n_for_precision": precision_n,
            "normal_approximation_n_for_power": power_n,
            "balanced_n_to_review": max(36, 9*math.ceil(max(precision_n, power_n)/9)),
            "automatic_sample_size_approval": False}


def stratified_interval(cells, *, confidence=.95):
    """Equal cell weights; paired differences are synthesis loss minus collective loss.

    Requires SciPy only for the Student-t quantile. This is an approximate
    independent-task interval, not a finite-sample coverage guarantee.
    """
    if set(cells) != set(CELLS) or not .5 < confidence < 1:
        raise ValueError("ALL_NINE_CELLS_REQUIRED")
    for values in cells.values():
        if len(values) < 2 or any(isinstance(v, bool) or not math.isfinite(v) or not -2 <= v <= 2 for v in values):
            raise ValueError("FINITE_PAIRED_DIFFERENCES_REQUIRED")
    estimate = mean(mean(values) for values in cells.values())
    terms = [variance(values)/(81*len(values)) for values in cells.values()]
    variance_estimate = sum(terms)
    weight_squared_sum = sum(1/(81*len(values)) for values in cells.values())
    bounded_half_width = 4*math.sqrt(math.log(2/(1-confidence))*weight_squared_sum/2)
    result = {"estimate": estimate, "n": sum(map(len, cells.values())), "confidence": confidence,
              "standard_error": math.sqrt(variance_estimate),
              "bounded_independent_task_interval": [max(-2, estimate-bounded_half_width), min(2, estimate+bounded_half_width)],
              "approximate_interval": None, "degrees_of_freedom": None,
              "automatic_promotion": False}
    if variance_estimate == 0:
        result["limitation"] = "Zero observed within-cell variance; no t-based significance claim."
        return result
    from scipy.stats import t
    df = variance_estimate**2 / sum(term**2/(len(values)-1) for term, values in zip(terms, cells.values()))
    margin = float(t.ppf((1+confidence)/2, df))*math.sqrt(variance_estimate)
    result.update(degrees_of_freedom=df, approximate_interval=[max(-2, estimate-margin), min(2, estimate+margin)])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sd", type=float, nargs="+", default=[.1, .2, .3, .5])
    args = parser.parse_args()
    print(json.dumps({"planning_only": True, "evaluation_seeds": None,
                      "scenarios": [planning_scenario(sd) for sd in args.sd]}, indent=2))


if __name__ == "__main__":
    main()
