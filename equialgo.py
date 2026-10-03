"""Shared helpers for the EquiAlgo audit and mitigation notebooks.

Everything the two notebooks have in common lives here: data loading, the
centre / remote grouping, the feature set, the bias-aware committee model,
budget-constrained selection and the fairness metrics.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

DATA_HIST = "data/donnees_demandes.csv"
DATA_EVAL = "data/candidats_evaluation.csv"

REMOTE_REGIONS = ["Bas-Saint-Laurent", "Cote-Nord", "Gaspesie-Iles-de-la-Madeleine"]
CENTRE, REMOTE = "Centre", "Eloignee"

# Budget window imposed by the brief, and the rate we target inside it.
BUDGET_MIN, BUDGET_MAX = 0.36, 0.44
TARGET_RATE = 0.40
# Rate used for the final submission (chosen with the HxBuddy indicative score,
# see model_corrige.ipynb section 7). Still well inside the budget window.
FINAL_RATE = 0.41

# Committee inputs removed from the final merit score, on top of the regional
# penalty: family income (a second channel of regional bias, audit section 5)
# and distance (a pure proxy for region with no merit content).
FINAL_DROP = ("log_revenu", "distance_100km")

# Merit-related columns the committee is allowed to use. Region and postal
# code are never used as merit signals; region only enters the model as an
# explicit bias term that is switched off at scoring time.
MERIT_COLUMNS = ["cote_r", "log_revenu", "heures", "distance_100km"]


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    hist = pd.read_csv(DATA_HIST)
    cand = pd.read_csv(DATA_EVAL)
    return hist, cand


def group(df: pd.DataFrame) -> np.ndarray:
    """Two-level sensitive attribute: large centres vs remote regions."""
    return np.where(df["region_administrative"].isin(REMOTE_REGIONS), REMOTE, CENTRE)


def is_remote(df: pd.DataFrame) -> np.ndarray:
    return df["region_administrative"].isin(REMOTE_REGIONS).to_numpy().astype(int)


def features(df: pd.DataFrame) -> pd.DataFrame:
    """Merit features plus the explicit remote indicator.

    Income enters as a log: it fits the committee's decisions better than the
    raw amount (see audit section 3).
    """
    return pd.DataFrame(
        {
            "cote_r": df["cote_r_equivalent"].to_numpy(),
            "log_revenu": np.log(df["revenu_familial_estime"].to_numpy()),
            "heures": df["heures_travail_semaine"].to_numpy(),
            "distance_100km": df["distance_domicile_campus_km"].to_numpy() / 100,
            "eloignee": is_remote(df),
        },
        index=df.index,
    )


@dataclass
class BiasAwareModel:
    """Logistic model of the committee with an explicit regional penalty term.

    Fitting with the remote indicator in the model lets the indicator absorb
    the regional penalty, so the merit coefficients are estimated *net* of it
    instead of the proxies (distance, hours, income) soaking it up.

    At scoring time `penalty_removed` (lambda in [0, 1]) sets how much of the
    estimated penalty we cancel: 0 reproduces the committee, 1 scores every
    applicant as if the committee had no regional penalty. `drop` removes the
    contribution of other committee inputs (used to remove the income bonus).
    """

    C: float = 1e4

    def fit(self, df: pd.DataFrame, y) -> "BiasAwareModel":
        X = features(df)
        self.lr_ = LogisticRegression(C=self.C, max_iter=10_000).fit(X, y)
        self.coef_ = pd.Series(self.lr_.coef_[0], index=X.columns)
        self.means_ = X.mean()
        return self

    @property
    def penalty(self) -> float:
        """Estimated regional penalty, in logits (positive = disadvantage)."""
        return -self.coef_["eloignee"]

    @property
    def penalty_in_r_points(self) -> float:
        return self.penalty / self.coef_["cote_r"]

    def score(self, df: pd.DataFrame, penalty_removed: float = 1.0,
              drop: tuple[str, ...] = ()) -> np.ndarray:
        X = features(df)
        raw = self.lr_.decision_function(X)
        raw = raw + penalty_removed * self.penalty * X["eloignee"].to_numpy()
        for col in drop:
            # Replace the applicant's value by the historical mean: the term no
            # longer ranks applicants, and the score stays on the same scale.
            raw = raw - self.coef_[col] * (X[col].to_numpy() - self.means_[col])
        return raw

    @property
    def hours_weight(self) -> float:
        """Committee's credit for one weekly hour worked, in R points."""
        return self.coef_["heures"] / self.coef_["cote_r"]

    def final_score(self, df: pd.DataFrame) -> np.ndarray:
        """Merit score used for the submission, in R points: R + hours_weight * hours.

        Same ranking as `score(df, 1.0, FINAL_DROP)` (no penalty, no income, no
        distance), written directly so that tied applicants stay exactly tied.
        """
        return (df["cote_r_equivalent"].to_numpy()
                + self.hours_weight * df["heures_travail_semaine"].to_numpy())


def select_top(scores: np.ndarray, rate: float = TARGET_RATE) -> np.ndarray:
    """Grant exactly round(rate * n) awards to the highest scores (fixed budget)."""
    n_grant = int(round(rate * len(scores)))
    order = np.argsort(-scores, kind="stable")
    decision = np.zeros(len(scores), dtype=int)
    decision[order[:n_grant]] = 1
    return decision


def selection_rates(pred, grp) -> dict:
    pred, grp = np.asarray(pred), np.asarray(grp)
    return {g: pred[grp == g].mean() for g in (CENTRE, REMOTE)}


def parity_gap(pred, grp) -> float:
    r = selection_rates(pred, grp)
    return r[CENTRE] - r[REMOTE]


def tpr_gap(y_ref, pred, grp) -> float:
    """Equal-opportunity gap: TPR(centre) - TPR(remote) against a reference label.

    Signed on purpose: a positive gap means deserving remote applicants are
    under-served.
    """
    y_ref, pred, grp = map(np.asarray, (y_ref, pred, grp))
    tpr = {g: pred[(grp == g) & (y_ref == 1)].mean() for g in (CENTRE, REMOTE)}
    return tpr[CENTRE] - tpr[REMOTE]


def merit_references(df: pd.DataFrame, model: BiasAwareModel, rate: float = TARGET_RATE,
                     noise: float = 0.0, seed: int = 0) -> dict[str, np.ndarray]:
    """Plausible stand-ins for the hidden reference standard.

    We do not have the jury's reference. Instead of trusting one guess, every
    method is checked against several definitions of "merit":

    - committee_sans_penalite: the committee's own criteria with the regional
      penalty removed (the definition our model is built on, so it flatters us);
    - cote_r_seule: academic merit only, R score ranking;
    - cote_r_heures: R score with credit for hours worked;
    - cote_r_revenu_heures: linear version of the committee's criteria.

    `noise` adds logistic noise to each latent score, to mimic a reference that
    is not a deterministic function of the columns we see.
    """
    rng = np.random.default_rng(seed)
    r = df["cote_r_equivalent"].to_numpy()
    h = df["heures_travail_semaine"].to_numpy()
    inc = df["revenu_familial_estime"].to_numpy() / 1e4
    latents = {
        "committee_sans_penalite": model.score(df, 1.0),
        "cote_r_seule": 1.38 * r,
        "cote_r_heures": 1.38 * r + 0.20 * h,
        "cote_r_revenu_heures": 1.38 * r + 0.24 * inc + 0.20 * h,
    }
    return {k: select_top(v + noise * rng.logistic(size=len(v)), rate) for k, v in latents.items()}
