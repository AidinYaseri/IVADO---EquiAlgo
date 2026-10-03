# Governance, ethics and production monitoring plan

This document covers what happens after the corrected model is approved: who owns it,
how it is watched, and when a human must step in. The numbers it refers to come from
`audit_rapport.ipynb` and `model_corrige.ipynb`.

## 1. What we are deploying, in plain words

A single merit score: **R score + 0.146 × weekly hours worked**. The top 41% of scores
receive an award.

How we got there: we fitted a logistic model of the historical committee on R score, family
income, hours worked, distance and a "remote region" indicator. The indicator lets the model
measure the penalty the committee applied to remote applicants (about 2.2 logits, or 1.6 R
points) instead of letting proxies hide it. We then kept only the committee's weights on R score
and hours worked, and removed the regional penalty, the income bonus (a second channel that
disadvantaged remote applicants, whose families earn less) and distance (a pure regional proxy).

Region is used **only to measure and remove** bias. Neither region, postal code, distance nor
income changes an individual's score in production.

## 2. Ethical choices we made, and the ones we leave to the institution

| Choice | What we did | Why | Who should confirm |
|---|---|---|---|
| Fairness metric | Equal opportunity (TPR parity between centres and remote regions), with demographic parity reported | A merit scholarship promises that deserving students have the same chance wherever they live. Forcing equal rates would ignore real profile differences | Ethics committee |
| Use of a sensitive attribute | Region used at training time to estimate the penalty, never at scoring time | Dropping it does not work (proxies rebuild the penalty); using it openly is the only way to remove the penalty instead of hiding it | Legal / privacy officer |
| Income | Removed from the score | A merit scholarship should not reward family wealth, and income is a regional proxy (remote families earn 25% less). The HxBuddy experiments agree that the reference standard ignores it | Board / program owner |
| Need-based support | Not added | Lower income does not count as merit in the reference either. If the institution wants a need-based component, it should be a separate, explicit policy, not hidden in the merit score | Board / program owner |
| Hours worked | Kept (0.146 R points per weekly hour) | Students who work long hours earn their grades under more pressure; the committee's weight was confirmed as the best fit to the reference | Program owner |
| Budget | 41% grant rate, inside the 36–44% window | Best HxBuddy score among 40/41/42%, with margin on both sides of the budget window | Finance |
| Use of the leaderboard | 24 indicative submissions used as controlled experiments | Only external evidence available about merit; limited to two interpretable choices and disclosed | Ethics committee |

**Legal context (Québec).** The Québec Charter of human rights and freedoms prohibits
discrimination on grounds that include *social condition*. Regional origin is not a listed ground on its
own, but in this data it is tied to income and working hours, so a regional penalty can amount to
indirect discrimination. Law 25 (Act to modernize legislative provisions as regards the protection of
personal information) requires that a person be informed when a decision about them is made exclusively
through automated processing, and that they can ask for the information used and for a review by a
person. Our plan below is built to meet those obligations. It has not been reviewed by a lawyer.

## 3. Monitoring plan

### 3.1 What we measure, how often, and what triggers an alert

| Indicator | Computed on | Frequency | Green | Alert (human review) | Stop (fall back to manual committee) |
|---|---|---|---|---|---|
| Grant rate overall | every scoring batch | each batch | 38–42% | 36–38% or 42–44% | outside 36–44% |
| Parity gap (centre − remote) | each batch | each batch | ≤ 0.05 | 0.05–0.10 | > 0.10 |
| Grant rate per region (5 regions) | each batch | each batch | each within ±5 pts of overall | worst region 5–10 pts away | worst region > 10 pts away |
| Equal-opportunity gap vs merit reference | cohort with outcome data (see 3.2) | yearly | ≤ 0.05 | 0.05–0.10 | > 0.10 |
| Re-estimated regional penalty on new committee decisions | new human-reviewed files | each semester | CI includes the value in production | shift > 0.5 R point | sign change |
| Input drift (PSI on R score, income, hours, distance; region mix) | each batch vs training data | each batch | PSI < 0.1 | 0.1–0.25 | > 0.25 |
| Intersectional rates: centre vs remote within each income quartile | each batch | each batch | gaps ≤ 0.05 | 0.05–0.10 | > 0.10 |
| Intersectional rates: region × first-generation, region × program | each batch | each semester | gaps ≤ 0.05 | 0.05–0.10 | > 0.10 |
| Appeals and overturned decisions by region | appeal log | monthly | no regional pattern | one region > 2× the others | n/a |

### 3.2 Building an independent merit signal

The hardest part of equal opportunity is knowing who deserved the award. In production we would not
rely on committee decisions again. Instead:

- **Outcome follow-up**: first-year GPA, persistence into second year and program completion for funded
  *and* a random sample of unfunded applicants near the threshold (with their consent). This gives a merit
  label that the committee did not produce.
- **Blind panel review**: each semester, a panel reviews ~200 files with region, postal code and distance
  hidden. Their decisions act as a second reference.
- **Exploration band**: a small share of awards (for example 2%) given by lottery among applicants just
  below the threshold, so that outcome data exists on both sides of it.

### 3.3 Roles

| Role | Responsibility |
|---|---|
| Model owner (data science) | Runs the monitoring dashboard, investigates alerts within 5 working days |
| Fairness reviewer (independent of the model owner) | Signs off each semester's audit, can trigger a stop |
| Program owner | Decides on policy questions (income as a criterion, budget) |
| Privacy officer | Law 25 notices, access requests, retention of region data |
| Applicants | Receive a notice that a model is used, the main factors in their score, and a path to human review |

### 3.4 The plan is code: `monitoring.py`

Every per-batch indicator above is implemented in `monitoring.py` (`check_batch`), with the same thresholds, and
tested in `tests/test_monitoring.py`. `monitoring_demo.ipynb` runs it on the real evaluation batch and on four
failure scenarios; each one trips its own alarm and nothing else:

| Scenario | Result |
|---|---|
| Normal batch (4,000 evaluation applicants) | all OK |
| Old biased model redeployed | STOP on parity, region and income-quartile gaps, while the grant rate looks normal |
| A quarter of applicants inflate hours by 6/week | ALERT on hours drift (otherwise 103 honest applicants lose their award) |
| Remote applications double | ALERT on region mix and distance drift; fairness indicators stay OK |
| Last year's fixed score cutoff reused on a stronger cohort | STOP: 55% grant rate, far over budget |

### 3.5 Transition rule for the people affected

Switching from the old model changes 390 of 4,000 decisions: 219 remote applicants gain an award and 154 centre
applicants lose one. Both groups have the same average R score (about 28.6); those who lose work about half as many
hours and come from families earning about twice as much. They did nothing wrong, so:

- awards already granted are never withdrawn, and renewals are honoured;
- the new rule applies to new applications only, announced before the application period opens;
- applicants who would have been funded under the old rule are told the reason for the change if they ask.

## 4. Transparency and recourse

- Each applicant is told that an automated score is used and which two inputs count (R score and weekly hours worked).
- On request, an applicant receives their score, the threshold for their cohort, and how far they were from it.
- Any applicant can ask for a human review. Reviewers see the file without region or postal code first.
- A short model card (inputs, metric choice, known limits, last audit date) is published each year.

## 5. Re-training rules

- Re-estimate the model once a year, or after a stop alert.
- Never retrain on the corrected model's own decisions as labels: that would freeze our assumptions.
  Train on blind-panel decisions and outcome data instead.
- Every new version must be compared with the current one on the same Pareto plot before release.

## 6. Known risks

- **Wrong merit definition.** If true merit depends on something we cannot see, removing the penalty could
  under- or over-correct. The outcome follow-up in 3.2 is how we would find out.
- **Gaming.** Hours worked are self-reported and now carry real weight (7 hours ≈ 1 R point). In our simulation,
  a quarter of applicants adding 6 hours would push out 103 honest applicants. Spot checks against pay stubs or
  employer letters are needed, and the hours drift indicator (3.1) flags the pattern.
- **Region coding.** A student who moved recently may be coded to the wrong region. Region is only used for
  measurement, so this affects monitoring, not the individual decision.
- **Two-block view.** Our groups are centres vs remote regions. Other regions of Québec (not in this data)
  must be added to the audit before any wider roll-out.
