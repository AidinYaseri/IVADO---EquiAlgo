# ÉquiAlgo: project summary

**Team:** CertifiedHackerBoys · Ryan Morov, Aidin Yaseri, Arav Sahni, Makan Homayoun
**Challenge:** IVADO – ÉquiAlgo, CodeML 2026 (Polytechnique Montréal, October 3–4, 2026)
**Final HxBuddy score:** 94.68% accuracy, 94.47% macro F1 (first submission: 92.38%)

## 1. The problem

A Québec institution scores scholarship applications with a machine learning model that is 88% accurate. It grants
awards to 48.4% of applicants from Montréal and the Capitale-Nationale but only 27.3% from Bas-Saint-Laurent,
Côte-Nord and Gaspésie–Îles-de-la-Madeleine, even though their average R scores differ by only 0.7 points. The model
is accurate because it copies a historical committee, and that committee is under audit. Our job: diagnose the bias,
correct it under a fixed budget (36–44% of applicants funded), and propose how to monitor it in production. All data
is synthetic.

The trap in the brief: the label `decision_octroi` records what the biased committee did. The jury scores against a
hidden "real merit" reference. Copying the label perfectly means copying the bias perfectly.

## 2. What we found (the diagnosis)

1. **A flat regional penalty.** At the same R score, remote applicants were funded far less often (26% vs 59%
   between R 28 and 29). A logistic model of the committee shows a penalty of 2.2 logits, about **1.6 R points**
   (95% CI 1.4–1.7), identical in all three remote regions and absent in both centres. It explains 83% of the gap.
2. **A second, hidden bias: family income.** The committee also rewarded higher family income. Remote families earn
   25% less (median 51.6 k$ vs 69.2 k$), so this bonus worked against them too.
3. **Proxies rebuild the penalty.** Postal code and distance identify the region almost perfectly (AUC ≈ 1.0); hours
   worked strongly (0.80), income moderately (0.68). SHAP on the production model shows distance costs remote
   applicants as much as the region label itself: location moves their probability by about −10 points (centres +6).
   Deleting the region column just moves the penalty onto distance. **The bias is in the labels, not the columns.**
4. **Where you live changes the decision.** Moving a remote applicant to Montréal, with the same grades, hours and
   income, flips **190 of 1,628** from refused to funded under the production model.
5. **Low-income remote students were hurt most.** The production model refused 4 in 10 of the deserving ones.
6. **The audit "passes" if you measure it wrong.** Against the committee's own labels the production model's
   equal-opportunity gap is only 0.06. Against penalty-free merit rankings it is 0.22–0.30, bracketing the 0.270 the
   organisers report against their hidden reference.

## 3. What we built (the fix)

**Bias-aware model, biases switched off.** We fit a logistic model of the committee *with* an explicit remote-region
term, so the penalty is captured by that term instead of hiding in distance. We then score everyone with the penalty,
the income bonus and the distance term removed. What remains is the committee's own weighting of real merit:

> **merit = R score + 0.146 × weekly hours worked**, and the top 41% of applicants receive an award.

**Fairness metric:** equal opportunity (deserving students get the same chance in every region), with demographic
parity reported as a secondary check.

**Pareto front:** we swept the share of the penalty removed (λ from 0 to 1.25, with and without income) and compared
against fairlearn's ThresholdOptimizer and ExponentiatedGradient. Removing the bias improves fairness and agreement with
merit at the same time. The fairlearn tools barely move with TPR parity, because they measure fairness against the
biased labels.

**External check:** 24 HxBuddy submissions used as controlled experiments, each changing one ingredient. Income always
hurt, hours worked always helped, program and first-generation status added nothing, and nothing near the committee's
own hours weight (0.146 at 41%) beat it. Our simulation puts the realistic ceiling for any formula at about 94.8%; the
top five teams are all between 94.6% and 94.8%.

## 4. Results on the 4,000 evaluation applicants

| | Production model | Our model |
|---|---|---|
| Grant rate | 39.1% | 41.0% |
| Grant rate, centres / remote | 46.8% / 27.8% | 40.9% / 41.1% |
| Parity gap (95% CI) | 0.19 (0.16–0.22) | −0.002 (−0.03 to 0.03) |
| Equal-opportunity gap vs R + hours merit | 0.30 | 0.00 |
| Remote applicants funded only if they move to Montréal | 190 | 0 |
| Worst subgroup TPR (low-income remote) | 0.58 | 1.00 |
| HxBuddy accuracy / macro F1 | | 94.68% / 94.47% |

**Same grades, different lives.** 390 decisions change. Those who gain an award (mostly remote) and those who lose one
(mostly centre) have the same average R score (28.6). The gainers work twice as many hours (14.6 vs 7.4 per week) and
come from families earning about half as much (45 k$ vs 84 k$).

## 5. Governance and ethics

- **Monitoring as code:** `monitoring.py` checks every batch (grant rate, parity gap, each region, income subgroups,
  input drift) with OK / ALERT / STOP thresholds. Tested on five scenarios: a redeployed biased model is stopped even
  though its budget looks normal; inflated hours raise an alert (otherwise 103 honest students lose out); a population
  shift raises a drift alert without a fairness alarm; a reused fixed cutoff is stopped at a 55% grant rate.
- **Sensitive attribute:** region and income are used only to measure and remove bias, never to score anyone.
- **Québec law:** Law 25 notice of automated decisions, main factors on request, human review on appeal; the Charter's
  "social condition" ground makes a regional penalty a possible form of indirect discrimination.
- **Transition rule:** awards already granted are never withdrawn; the new rule applies to new applications.
- **Independent merit signal:** first-year results, persistence and blind-panel reviews to measure equal opportunity
  yearly, without relying on any committee.

## 6. Limitations

- We never saw the jury's reference; using 24 leaderboard submissions to choose two settings (drop income, 41%) is a
  mild form of tuning, fully disclosed.
- If merit should ignore hours worked, our model slightly favours remote applicants (gap about −0.05).
- Hours worked are self-reported and now matter (7 hours ≈ 1 R point): they must be verified.
- ExponentiatedGradient with a tight demographic-parity bound is a close competitor; we prefer one readable formula.
- Synthetic data with five regions in two blocks; a real deployment needs other regions, domain and legal review.

## 7. Deliverables

| File | What it is |
|---|---|
| `predictions.csv` | The 4,000 decisions (94.68% on HxBuddy) |
| `audit_rapport.ipynb` | Full diagnosis: bias, proxies, SHAP, counterfactual, income channel, experiments, subgroups, metric choice |
| `model_corrige.ipynb` | The fix, Pareto front, robustness, who gains and who loses |
| `monitoring_demo.ipynb`, `monitoring.py` | Production monitor and its five-scenario test |
| `equialgo.py`, `model_final.json` | Shared code and the fitted model |
| `tests/`, `run_all.py` | 21 unit tests; one command reproduces everything |
| `GOVERNANCE.md`, `MODEL_CARD.md` | Governance plan, legal notes, transition rule, model card |
| `presentation.pptx`, `presentation.pdf`, `PITCH_NOTES.md` | Five-minute pitch with speaker notes and jury Q&A |
| `README.md`, `DEVPOST.md` | Project page and Devpost text |

Tools: Python, pandas, NumPy, scikit-learn, fairlearn, SHAP, matplotlib, Jupyter, pytest. AI assistance: Claude Code
(Anthropic). Every number comes from running the code in the repository.
