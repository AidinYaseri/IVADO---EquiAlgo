"""Production fairness monitor for the ÉquiAlgo scholarship model.

Implements the per-batch indicators of GOVERNANCE.md, section 3.1. For one
scoring batch (applicants + decisions) it returns one row per indicator with its
value and a status:

    OK     inside the green band, nothing to do
    ALERT  a person must review the batch before decisions are sent
    STOP   decisions are held; the manual committee process takes over

The equal-opportunity gap is not computed per batch: it needs outcome data
(first-year results, blind-panel reviews), so it is a yearly check.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import equialgo as eq

OK, ALERT, STOP = "OK", "ALERT", "STOP"


@dataclass(frozen=True)
class Band:
    """Status bands for an indicator where larger values are worse."""

    alert: float
    stop: float

    def status(self, value: float) -> str:
        if value > self.stop:
            return STOP
        if value > self.alert:
            return ALERT
        return OK


# Thresholds from GOVERNANCE.md, section 3.1.
GRANT_RATE_GREEN = (0.38, 0.42)
GRANT_RATE_BUDGET = (eq.BUDGET_MIN, eq.BUDGET_MAX)
PARITY = Band(alert=0.05, stop=0.10)
REGION_DEVIATION = Band(alert=0.05, stop=0.10)
INTERSECTIONAL = Band(alert=0.05, stop=0.10)
PSI = Band(alert=0.10, stop=0.25)

DRIFT_COLUMNS = {
    "cote_r_equivalent": "R score",
    "heures_travail_semaine": "hours worked",
    "revenu_familial_estime": "family income",
    "distance_domicile_campus_km": "distance",
}


def grant_rate_status(rate: float) -> str:
    lo, hi = GRANT_RATE_GREEN
    if lo <= rate <= hi:
        return OK
    lo, hi = GRANT_RATE_BUDGET
    return ALERT if lo <= rate <= hi else STOP


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population stability index of `actual` against `expected` (decile bins of `expected`)."""
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, 1e-4, None), np.clip(a, 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


def categorical_psi(expected: pd.Series, actual: pd.Series) -> float:
    """PSI for a categorical column, using its categories as bins."""
    cats = sorted(set(expected) | set(actual))
    e = expected.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    a = actual.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    e, a = np.clip(e, 1e-4, None), np.clip(a, 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


def check_batch(batch: pd.DataFrame, decisions, training: pd.DataFrame) -> pd.DataFrame:
    """Run every per-batch indicator. `training` is the data the model was fitted on."""
    decisions = np.asarray(decisions).astype(int)
    grp = eq.group(batch)
    rows = []

    rate = decisions.mean()
    rows.append(("Grant rate", rate, grant_rate_status(rate), "green 38-42%, budget 36-44%"))

    gap = eq.parity_gap(decisions, grp)
    rows.append(("Parity gap (centre - remote)", gap, PARITY.status(abs(gap)), "|gap| alert > 0.05, stop > 0.10"))

    by_region = pd.Series(decisions).groupby(batch["region_administrative"].to_numpy()).mean()
    worst = (by_region - rate).abs()
    rows.append((f"Worst region vs overall ({worst.idxmax()})", worst.max(), REGION_DEVIATION.status(worst.max()),
                 "alert > 5 pts, stop > 10 pts"))

    # Within each income quartile, centre and remote applicants should be granted at similar rates.
    quartile = pd.qcut(batch["revenu_familial_estime"], 4, labels=False).to_numpy()
    cell = pd.DataFrame({"q": quartile, "g": grp, "d": decisions}).groupby(["q", "g"]).d.mean().unstack()
    inter = (cell[eq.CENTRE] - cell[eq.REMOTE]).abs().max()
    rows.append(("Worst region gap within an income quartile", inter, INTERSECTIONAL.status(inter),
                 "alert > 0.05, stop > 0.10"))

    for col, label in DRIFT_COLUMNS.items():
        value = psi(training[col].to_numpy(), batch[col].to_numpy())
        rows.append((f"Drift (PSI): {label}", value, PSI.status(value), "alert > 0.10, stop > 0.25"))
    value = categorical_psi(training["region_administrative"], batch["region_administrative"])
    rows.append(("Drift (PSI): region mix", value, PSI.status(value), "alert > 0.10, stop > 0.25"))

    return pd.DataFrame(rows, columns=["indicator", "value", "status", "rule"])


def overall_status(report: pd.DataFrame) -> str:
    """The batch takes the worst status of its indicators."""
    for level in (STOP, ALERT):
        if (report["status"] == level).any():
            return level
    return OK
