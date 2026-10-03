"""Reproduce the whole project in one command: `python run_all.py`.

Runs the three notebooks in order (audit, corrected model, monitoring demo), then the
unit tests, then checks that predictions.csv meets the brief. Needs the challenge data
in data/ (donnees_demandes.csv, candidats_evaluation.csv).
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

import equialgo as eq

NOTEBOOKS = ["audit_rapport.ipynb", "model_corrige.ipynb", "monitoring_demo.ipynb"]


def run(cmd):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main():
    missing = [p for p in (eq.DATA_HIST, eq.DATA_EVAL) if not Path(p).exists()]
    if missing:
        sys.exit(f"Missing challenge data: {', '.join(missing)}. Copy the organisers' data/ folder here first.")

    for nb in NOTEBOOKS:
        run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", nb])
    run([sys.executable, "-m", "pytest", "-q"])

    sub = pd.read_csv("predictions.csv")
    cand = pd.read_csv(eq.DATA_EVAL)
    assert list(sub.columns) == ["id_candidat", "decision_octroi"], "wrong columns"
    assert len(sub) == len(cand) == 4000 and set(sub.id_candidat) == set(cand.id_candidat), "wrong applicants"
    assert set(sub.decision_octroi.unique()) <= {0, 1}, "values must be 0 or 1"
    rate = sub.decision_octroi.mean()
    assert eq.BUDGET_MIN <= rate <= eq.BUDGET_MAX, f"grant rate {rate:.1%} outside the budget"
    print(f"\nAll done. predictions.csv: {len(sub)} rows, grant rate {rate:.1%} (budget 36-44%).")


if __name__ == "__main__":
    main()
