# Model card: ÉquiAlgo merit score

Format adapted from Mitchell et al., "Model Cards for Model Reporting" (FAT* 2019).

## Model details

- **Developed by:** team CertifiedHackerBoys (Ryan Morov, Aidin Yaseri, Arav Sahni, Makan Homayoun), CodeML 2026,
  for the IVADO ÉquiAlgo challenge. Synthetic data, fictional institution.
- **Type:** a bias-aware logistic regression of the historical committee's decisions, used to derive a linear merit
  score. The deployed rule is:

  > **merit = R score + 0.146 × weekly hours worked**; the top 41% of each batch receive an award.

- **How it was built:** the committee model is fitted on R score, log family income, hours worked, distance and a
  remote-region indicator. The indicator captures the committee's regional penalty (2.2 logits, about 1.6 R points).
  The deployed score keeps only the committee's weights on R score and hours worked, and removes the regional
  penalty, the income bonus and the distance term. Full details: `model_corrige.ipynb`; coefficients: `model_final.json`.
- **Code:** `equialgo.py` (`BiasAwareModel.final_score`), tests in `tests/`.

## Intended use

- Ranking scholarship applications under a fixed budget, as **decision support** with human review of alerts and appeals.
- Not intended for: loans, need-based aid, admissions, or any population outside the five regions in the data without a
  new audit.

## Factors

- **Sensitive attribute audited:** administrative region, grouped as large centres (Montréal, Capitale-Nationale) vs
  remote regions (Bas-Saint-Laurent, Côte-Nord, Gaspésie–Îles-de-la-Madeleine), and checked region by region.
- **Intersections checked:** region × family income quartile, × first-generation status, × program of study.
- **Proxies identified:** postal code and distance (identify the region almost perfectly), hours worked (strong), family
  income (moderate). None of the location proxies enter the deployed score.

## Metrics

- **Primary fairness metric:** equal opportunity (TPR gap between centres and remote regions) against penalty-free merit
  references. Secondary: demographic parity gap, per-region grant rates, intersectional rates.
- **Utility:** agreement with the organisers' hidden merit reference (HxBuddy indicative score).
- **Budget:** grant rate must stay within 36–44%.

## Evaluation data

- 4,000 evaluation applicants (`data/candidats_evaluation.csv`), unlabelled; scored by the organisers' HxBuddy platform.
- 30% held-out split of the historical data for the Pareto comparison.

## Training data

- 10,000 historical committee decisions (`data/donnees_demandes.csv`). These labels are **biased** (that is the point of
  the challenge) and are used only to estimate the committee's weights and its penalty, never as ground truth.

## Quantitative results (4,000 evaluation applicants)

| | Production model | This model |
|---|---|---|
| Grant rate | 39.1% | 41.0% |
| Grant rate, centres / remote | 46.8% / 27.8% | 40.9% / 41.1% |
| Parity gap (95% CI) | 0.19 (0.16 to 0.22) | −0.002 (−0.03 to 0.03) |
| Equal-opportunity gap vs R + hours reference | 0.30 | 0.00 |
| Worst subgroup TPR (low-income remote) | 0.58 | 1.00 |
| Remote applicants who flip to "granted" if moved to Montréal | 190 of 1,628 | 0 |
| HxBuddy indicative accuracy / macro F1 | | 94.68% / 94.47% |

## Ethical considerations

- Region is used at training time **only to measure and remove** a penalty; it never affects an individual score.
- Removing the income bonus is a value choice (wealth is not merit), supported by the organisers' reference.
- 154 centre applicants lose an award compared with the old model; a transition rule (no withdrawal of awards
  already granted) is recommended in `GOVERNANCE.md`.
- Hours worked are self-reported and now carry weight (7 hours ≈ 1 R point): verification is required.

## Caveats and recommendations

- The hidden reference was never observed; 24 indicative submissions were used as controlled experiments and are
  all disclosed (`audit_rapport.ipynb`, section 6).
- Synthetic data. Real deployment needs domain, legal (Québec Charter, Law 25) and stakeholder review.
- Monitor every batch with `monitoring.py` (thresholds in `GOVERNANCE.md`), and build an independent merit signal
  (first-year results, blind-panel reviews) to measure equal opportunity yearly.
