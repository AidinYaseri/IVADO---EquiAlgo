"""Unit tests for monitoring.py. Run with `pytest` from the repository root."""
import numpy as np
import pytest

import equialgo as eq
import monitoring as mon
from test_equialgo import synthetic_applicants


@pytest.fixture(scope="module")
def training():
    return synthetic_applicants(seed=0)


@pytest.fixture(scope="module")
def batch():
    return synthetic_applicants(seed=1)


@pytest.fixture(scope="module")
def fair_decisions(training, batch):
    model = eq.BiasAwareModel().fit(training, training.decision_octroi)
    return eq.select_top(model.final_score(batch), eq.FINAL_RATE)


def test_band_status():
    band = mon.Band(alert=0.05, stop=0.10)
    assert [band.status(v) for v in (0.01, 0.07, 0.2)] == [mon.OK, mon.ALERT, mon.STOP]


@pytest.mark.parametrize("rate, expected", [(0.40, mon.OK), (0.37, mon.ALERT), (0.43, mon.ALERT),
                                            (0.35, mon.STOP), (0.45, mon.STOP)])
def test_grant_rate_status(rate, expected):
    assert mon.grant_rate_status(rate) == expected


def test_psi_is_zero_for_same_distribution_and_large_for_a_shift():
    x = np.random.default_rng(0).normal(size=5000)
    assert mon.psi(x, x) == pytest.approx(0.0, abs=1e-9)
    assert mon.psi(x, x + 1.0) > 0.25


def test_fair_batch_is_ok(training, batch, fair_decisions):
    report = mon.check_batch(batch, fair_decisions, training)
    assert len(report) == 9
    assert mon.overall_status(report) == mon.OK


def test_biased_batch_is_stopped(training, batch):
    # Grant only centre applicants: the budget can look fine while fairness collapses.
    remote = eq.is_remote(batch) == 1
    scores = batch.cote_r_equivalent.to_numpy() - 100 * remote
    report = mon.check_batch(batch, eq.select_top(scores, 0.40), training)
    assert report.loc[report.indicator.str.startswith("Parity"), "status"].item() == mon.STOP
    assert mon.overall_status(report) == mon.STOP


def test_hours_inflation_raises_drift_alert(training, batch, fair_decisions):
    gamed = batch.copy()
    gamed["heures_travail_semaine"] += 6
    report = mon.check_batch(gamed, fair_decisions, training)
    hours = report.loc[report.indicator.str.contains("hours"), "status"].item()
    assert hours in (mon.ALERT, mon.STOP)
