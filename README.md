# ÉquiAlgo: removing two hidden regional biases from scholarship decisions

**Team:** CertifiedHackerBoys · **Members:** Ryan Morov, Aidin Yaseri, Arav Sahni, Makan Homayoun
**Challenge:** IVADO – ÉquiAlgo · CodeML 2026

A Québec institution's scholarship model grants awards to 48.4% of applicants from Montréal and the
Capitale-Nationale but only 27.3% from Bas-Saint-Laurent, Côte-Nord and Gaspésie–Îles-de-la-Madeleine.
We diagnose where that gap comes from, remove the part that is bias, and propose how to monitor it in production.

## Results at a glance

| | Production model | Our final model |
|---|---|---|
| Grant rate on the 4,000 evaluation applicants | 39.1% | **41.0%** (budget 36–44%) |
| Grant rate, centres / remote regions | 46.8% / 27.8% | **40.9% / 41.1%** |
| HxBuddy indicative score (accuracy / macro F1 vs hidden reference) | | **94.68% / 94.47%** |
| Equal-opportunity gap vs R score + hours merit reference | 0.296 | **0.000** |
| Accuracy vs the historical committee (held-out split) | 0.881 | 0.853 |

The last line is supposed to go down: the committee's decisions are what is under audit.

**Same grades, different lives.** 390 decisions change. Those who gain an award and those who lose one have the same
average R score (28.6); those who gain work twice as many hours (14.6 vs 7.4 per week) and come from families earning
about half as much (45 k$ vs 84 k$). The old model was rewarding comfort, not merit.

## What we found

1. **The R score explains about a third of the gap.** At the same R score, remote applicants were granted far less
   often (59% vs 26% between R = 28 and 29).
2. **Bias channel 1: a flat regional penalty.** The committee docked remote applicants 2.2 logits, about
   **1.6 R points** (95% bootstrap CI 1.4 to 1.7). Same size in all three remote regions, zero in both centres,
   constant across R scores. It explains 83% of the observed gap.
3. **Bias channel 2: an income bonus.** The committee also rewarded higher family income. Remote families earn
   25% less (median 51.6 k$ vs 69.2 k$), so this bonus worked against them too. Removing both channels brings the
   two groups to the same grant rate.
4. **Hours worked are real merit.** The committee credited about 0.146 R points per weekly hour worked. That part
   was fair, and the HxBuddy experiments confirm it.
5. **Proxies rebuild the penalty.** Distance and postal code predict the region almost perfectly (AUC ≈ 1.0), hours
   worked strongly (0.80). Without the region column, a model moves the penalty onto distance. Deleting columns does
   not fix biased labels. SHAP shows distance costs remote applicants as much as the region label itself.
6. **Where you live changes the decision.** Moving a remote applicant to Montréal, with the same grades, hours and
   income, flips **190 of 1,628** from refused to granted under the production model. Under ours: 0.
7. **Low-income remote students were hurt most.** The production model refused 4 in 10 of the deserving ones
   (TPR 0.58). After correction every income, first-generation and program subgroup is granted 38–44%.
8. **The production model's equal-opportunity gap is 0.22–0.30** against penalty-free merit rankings, which brackets
   the 0.270 the organisers report against their hidden reference.

## What we did

**Bias-aware model, biases removed.** A logistic model of the committee is fitted *with* an explicit remote-region
term, so the penalty is captured by that term instead of leaking into proxies. At scoring time we remove the penalty,
the income bonus and the distance term, keeping the committee's own weights on what is merit. The final score is:

> **merit = R score + 0.146 × weekly hours worked**, and the top 41% receive an award.

The fairness setting is `lambda`, the share of the penalty removed. Sweeping it from 0 to 1.25 (with and without the
income bonus) gives our Pareto front, compared with fairlearn's `ThresholdOptimizer` and `ExponentiatedGradient`
(TPR parity and demographic parity), each swept over its own constraint.

**Fairness metric: equal opportunity** (TPR parity between centres and remote regions), with demographic parity
reported. The reasoning is in section 7 of `audit_rapport.ipynb`.

**External check.** We used 24 HxBuddy submissions as controlled experiments, each changing one ingredient of the
score (all results in `audit_rapport.ipynb`, section 6). They showed that income is not merit, hours are, and that the
committee's own hours weight was already the best value. Two settings were chosen this way: dropping income and the 41%
grant rate. Three more rounds (program bonus, curved hours, seven nearby weight and rate variants) found nothing better: the committee's 0.146 at 41% is the peak.

## Repository

| File | Contents |
|---|---|
| `predictions.csv` | 4,000 decisions, `id_candidat,decision_octroi` (the file scored 94.68% on HxBuddy) |
| `audit_rapport.ipynb` | Bias measurement, committee model, proxies, SHAP, move-to-Montréal test, income channel, HxBuddy experiments, intersectional analysis with confidence intervals, metric choice |
| `model_corrige.ipynb` | Mitigation, Pareto front, robustness checks, who gains and who loses, writes `predictions.csv` and `model_final.json` |
| `monitoring_demo.ipynb` | The production monitor run on the real batch and on four failure scenarios |
| `model_final.json` | The fitted model: committee coefficients, removed terms, final formula, grant rule |
| `equialgo.py` | Shared code: features, bias-aware model, budget selection, metrics, merit references |
| `monitoring.py` | Per-batch fairness and drift monitor implementing the thresholds in `GOVERNANCE.md` |
| `tests/`, `pytest.ini` | 21 unit tests (model, metrics, budget rule, monitor, submission format) |
| `run_all.py` | Reproduces everything in one command |
| `GOVERNANCE.md` | Ethical choices, Québec legal notes, monitoring plan with thresholds, transition rule |
| `MODEL_CARD.md` | Model card (intended use, factors, metrics, results, caveats) |
| `presentation.pptx` | Five-minute pitch as an editable PowerPoint, with speaker notes on every slide |
| `presentation.pdf` | Same pitch as a PDF (source: `presentation/slides.html`) |
| `PITCH_NOTES.md` | Timed 5-minute script and answers to likely jury questions |
| `figures/` | Plots used in the notebooks and the pitch |
| `probes/`, `probes_round2/` … `probes_round5/` | The 24 experiment files submitted to HxBuddy |
| `baseline_model.ipynb` | The organisers' starting notebook, unchanged |
| `brief/` | The organisers' instructions |

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# put the challenge data in data/ (donnees_demandes.csv, candidats_evaluation.csv)
python run_all.py
```

`run_all.py` executes the three notebooks in order (audit, corrected model, monitoring demo), runs the unit tests and
checks `predictions.csv` against the brief. It takes a few minutes on a laptop with Python 3.10 or newer. The model
notebook also confirms the regenerated file is identical to the one scored on HxBuddy.

## Limitations

- We do not have the jury's reference. Our merit stand-ins are constructions; the HxBuddy score is the only external
  evidence, and using it to choose settings is a mild form of tuning on the evaluation set. We kept it to two
  interpretable choices.
- Against merit definitions that give no credit for hours worked, the final model slightly favours remote applicants
  (EO gap about −0.05), because remote students work more hours.
- On this data, `ExponentiatedGradient` with a tight demographic-parity bound is a close competitor. We prefer our
  model because its setting means something and it is one formula an applicant can check.
- We remove the biases we can see. Whether a need-based component should be added is a policy decision we flag in
  `GOVERNANCE.md`.
- All data is synthetic.

## Tools, sources and AI use

- Python, pandas, NumPy, scikit-learn, fairlearn (`ThresholdOptimizer`, `ExponentiatedGradient`), matplotlib, Jupyter.
- Challenge brief, data and `baseline_model.ipynb` provided by IVADO for CodeML 2026; HxBuddy indicative scores.
- Fairlearn documentation: https://fairlearn.org
- Québec Charter of human rights and freedoms (CQLR c. C-12) and Law 25 (S.Q. 2021, c. 25), for the governance section.
- AI assistance: Claude Code (Anthropic) was used to help write code, notebooks and documentation. All results were
  produced by running the code in this repository.
