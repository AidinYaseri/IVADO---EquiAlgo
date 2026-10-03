"""Unit tests for equialgo.py. Run with `pytest` from the repository root."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import equialgo as eq

ROOT = Path(__file__).resolve().parent.parent


def synthetic_applicants(n=4000, penalty_logits=2.0, seed=0):
    """Applicants shaped like the challenge data, with a known regional penalty in the labels."""
    rng = np.random.default_rng(seed)
    remote = rng.random(n) < 0.4
    regions = np.where(remote, rng.choice(eq.REMOTE_REGIONS, n), rng.choice(["Montreal", "Capitale-Nationale"], n))
    df = pd.DataFrame({
        "id_candidat": [f"C{i:06d}" for i in range(n)],
        "cote_r_equivalent": rng.normal(27.7, 3.0, n).round(2),
        "programme_etudes": rng.choice(["Genie", "Sante", "Sciences"], n),
        "region_administrative": regions,
        "code_postal_3": np.where(remote, "G4X", "H2X"),
        "revenu_familial_estime": np.exp(rng.normal(11.0, 0.4, n)).round(),
        "heures_travail_semaine": rng.integers(1, 25, n),
        "distance_domicile_campus_km": np.where(remote, rng.uniform(100, 400, n), rng.uniform(1, 40, n)).round(1),
        "premiere_generation_universitaire": rng.integers(0, 2, n),
    })
    logit = (1.4 * (df.cote_r_equivalent - 28) + 0.2 * (df.heures_travail_semaine - 10)
             - penalty_logits * remote)
    df["decision_octroi"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


@pytest.fixture(scope="module")
def data():
    return synthetic_applicants()


@pytest.fixture(scope="module")
def model(data):
    return eq.BiasAwareModel().fit(data, data.decision_octroi)


# --- budget selection -------------------------------------------------------

def test_select_top_grants_exact_budget():
    scores = np.random.default_rng(1).normal(size=1000)
    assert eq.select_top(scores, 0.41).sum() == 410


def test_select_top_picks_highest_scores():
    scores = np.array([0.1, 5.0, 3.0, -1.0, 4.0])
    assert eq.select_top(scores, 0.4).tolist() == [0, 1, 0, 0, 1]


def test_select_top_breaks_ties_by_file_order():
    scores = np.array([1.0, 2.0, 2.0, 0.0])
    assert eq.select_top(scores, 0.25).tolist() == [0, 1, 0, 0]


# --- fairness metrics -------------------------------------------------------

def test_parity_gap_sign():
    grp = np.array([eq.CENTRE] * 4 + [eq.REMOTE] * 4)
    pred = np.array([1, 1, 1, 0, 1, 0, 0, 0])
    assert eq.parity_gap(pred, grp) == pytest.approx(0.75 - 0.25)


def test_tpr_gap_counts_only_deserving_applicants():
    grp = np.array([eq.CENTRE] * 4 + [eq.REMOTE] * 4)
    ref = np.array([1, 1, 0, 0, 1, 1, 0, 0])
    pred = np.array([1, 1, 0, 0, 1, 0, 1, 1])
    assert eq.tpr_gap(ref, pred, grp) == pytest.approx(1.0 - 0.5)


# --- bias-aware model --------------------------------------------------------

def test_penalty_is_recovered(model):
    assert model.penalty == pytest.approx(2.0, abs=0.35)


def test_removing_penalty_makes_location_irrelevant(data, model):
    a = data.iloc[[0]].copy()
    a["region_administrative"], a["code_postal_3"], a["distance_domicile_campus_km"] = "Montreal", "H2X", 10.0
    b = a.copy()
    b["region_administrative"], b["code_postal_3"], b["distance_domicile_campus_km"] = "Cote-Nord", "G4R", 300.0
    assert model.final_score(a)[0] == pytest.approx(model.final_score(b)[0])
    # With lambda = 0 the committee's penalty is still there.
    assert model.score(a, 0.0)[0] > model.score(b, 0.0)[0]


def test_final_score_ignores_income(data, model):
    a = data.iloc[[0]].copy()
    b = a.copy()
    b["revenu_familial_estime"] = a["revenu_familial_estime"] * 5
    assert model.final_score(a)[0] == pytest.approx(model.final_score(b)[0])


def test_final_score_ranks_like_neutralised_committee(data, model):
    # The committee score with penalty, income and distance removed is an increasing affine
    # function of the final score, so both rank applicants the same way.
    direct = model.final_score(data)
    via_committee = model.score(data, 1.0, eq.FINAL_DROP)
    offset = via_committee - model.coef_["cote_r"] * direct
    assert model.coef_["cote_r"] > 0
    assert np.ptp(offset) < 1e-8


def test_final_score_is_r_plus_weighted_hours(data, model):
    expected = data.cote_r_equivalent + model.hours_weight * data.heures_travail_semaine
    assert np.allclose(model.final_score(data), expected)


# --- submitted file ----------------------------------------------------------

@pytest.mark.skipif(not (ROOT / "predictions.csv").exists(), reason="predictions.csv not generated yet")
def test_predictions_file_meets_the_brief():
    sub = pd.read_csv(ROOT / "predictions.csv")
    assert list(sub.columns) == ["id_candidat", "decision_octroi"]
    assert len(sub) == 4000 and sub.id_candidat.is_unique
    assert set(sub.decision_octroi.unique()) <= {0, 1}
    assert eq.BUDGET_MIN <= sub.decision_octroi.mean() <= eq.BUDGET_MAX
    cand_path = ROOT / eq.DATA_EVAL
    if cand_path.exists():
        assert set(sub.id_candidat) == set(pd.read_csv(cand_path).id_candidat)
