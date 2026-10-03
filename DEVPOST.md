# Devpost draft (copy into the project page)

**Project name:** ÉquiAlgo: removing two hidden regional biases from scholarship decisions
**Team:** CertifiedHackerBoys
**Members:** Ryan Morov, Aidin Yaseri, Arav Sahni, Makan Homayoun
**Challenge / prize to select:** IVADO – ÉquiAlgo (only this one)
**Repository:** `<GitHub URL, public or shared with the judges>`

## Inspiration
A scholarship model that is 88% accurate grants awards to 48% of applicants from Montréal and Québec City but only 27%
from Bas-Saint-Laurent, Côte-Nord and Gaspésie. It is accurate because it copies past committee decisions. We wanted to
know how much of that gap is merit and how much is bias.

## What it does
We audit 10,000 historical decisions, find two hidden channels of regional bias, remove them, and score the 4,000
evaluation applicants under the fixed budget. We also propose a monitoring and governance plan for production.

## How we built it
- **Diagnosis.** At the same R score, remote applicants were granted far less often (26% vs 59% between R 28 and 29).
  A logistic model of the committee finds a flat penalty of 2.2 logits (about 1.6 R points, 95% CI 1.4 to 1.7) on all
  three remote regions and neither centre. It explains 83% of the gap.
- **Second channel.** The committee also rewarded family income. Remote families earn 25% less, so that bonus also
  worked against them.
- **Proxies.** Distance and postal code identify the region almost perfectly. Without the region column, a model moves
  the penalty onto distance, so deleting columns does not help: the bias is in the labels.
- **Fix.** Fit the committee model *with* a remote-region term so it absorbs the penalty, then score with the penalty,
  the income bonus and distance removed. What remains is the committee's own weighting of real merit:
  **R score + 0.146 × weekly hours worked**. The top 41% receive an award.
- **Pareto front.** We sweep the share of the penalty removed (lambda, with and without income) and compare with
  fairlearn's ThresholdOptimizer and ExponentiatedGradient, each swept over its own constraint.
- **Metric.** Equal opportunity (TPR parity), measured against penalty-free merit references, never against the
  committee's own labels (against those, the biased model looks fair).
- **External check.** We used 13 HxBuddy submissions as controlled experiments, each changing one ingredient. They
  showed that income is not merit, hours worked are, and the committee's hours weight was already optimal.

## Results
- HxBuddy indicative score: **94.68% accuracy, 94.47% macro F1** (first submission: 92.38%).
- Grant rate 41.0% (budget 36–44%). Centres 40.9%, remote regions 41.1% (production: 46.8% vs 27.8%).
- Equal-opportunity gap against an R score + hours merit ranking: 0.296 for the production model, 0.000 for ours.

## Challenges
The only label available is the biased one. Fairlearn's TPR-parity tools measure fairness against that label, where the
production model already looks fair, so they barely move. We had to build our own merit references and use the
leaderboard as a careful experiment rather than a target.

## Limitations
- We do not have the jury's reference; using HxBuddy to choose two settings (drop income, 41% rate) is a mild form of
  tuning, which we disclose. We stopped once gains fell to 0.05 points.
- Against merit definitions that ignore hours worked, our model slightly favours remote applicants.
- ExponentiatedGradient with a tight demographic-parity bound is a close competitor; we prefer one readable formula.
- Synthetic data; a real deployment needs domain and legal review.

## How to run
See the README: create a venv, `pip install -r requirements.txt`, put the challenge CSVs in `data/`, then run
`audit_rapport.ipynb` and `model_corrige.ipynb`. The second notebook rewrites `predictions.csv`.

## Built with
Python, pandas, NumPy, scikit-learn, fairlearn, matplotlib, Jupyter. AI assistance: Claude Code (Anthropic), used to help
write code and documentation; every number comes from running the code.
