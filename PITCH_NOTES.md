# Pitch notes: 5-minute script and Q&A prep

Team CertifiedHackerBoys · IVADO – ÉquiAlgo · deck: `presentation.pdf` (11 slides)

Target: 5:00. Times are cumulative. Speak to the numbers in **bold**; everything else is optional.
If you run long, cut slide 6 (metric) to one sentence and point to the notebook.

---

## Script

**Slide 1 · Title (0:00–0:10)**
"We're CertifiedHackerBoys. Our project is about one sentence: same R score, different postal code, different answer."

**Slide 2 · The problem (0:10–0:35)**
"The institution's model is 88% accurate. But it grants awards to **48%** of applicants from Montréal and Québec City,
and only **27%** from Bas-Saint-Laurent, Côte-Nord and Gaspésie. Their grades differ by **0.7 R points**. A 21-point gap
in awards, almost no gap in grades. The model is accurate because it copies the old committee, and the committee is
what's under audit."

**Slide 3 · Bias channel 1: the penalty (0:35–1:10)**
"Look at students with the same R score. Between 28 and 29, **59%** get an award in the centres and **26%** in the
regions. We modelled the committee and found a flat penalty worth **1.6 R points**, the same in all three remote
regions, and it explains **83%** of the gap. Then we asked the production model a simple question: what if a remote
student moved to Montréal, same grades, same job, same family? **190 students out of 1,628** flip from refused to
granted. Just by changing their address."

**Slide 4 · Proxies (1:10–1:35)**
"The obvious fix, deleting the region column, doesn't work. Distance and postal code identify the region almost
perfectly. SHAP shows distance costs remote students as much as the region label itself. Take the label away and
the model rebuilds the penalty from distance. **The bias is in the labels, not the columns.**"

**Slide 5 · Bias channel 2: income (1:35–2:10)**
"There was a second, quieter bias. The committee also rewarded **family income**, and remote families earn **25% less**.
The two stack up: under the production model, **four in ten deserving low-income remote students were refused**.
We confirmed it with 24 controlled experiments on HxBuddy: adding income always hurts agreement with the
reference, adding hours worked always helps."

**Slide 6 · Metric (2:10–2:30)**
"We measure fairness with **equal opportunity**: a deserving student in Gaspé should have the same chance as one in
Montréal. Not demographic parity, which forces equal rates whether merit differs or not. And never against the
committee's own labels: against those, the biased model looks fair."

**Slide 7 · The fix (2:30–3:00)**
"Our fix: we fit the committee model *with* an explicit region term, so the penalty lands there instead of hiding in
distance. Then we switch it off, along with the income bonus. What's left is the committee's own weighting of real
merit: **R score plus 0.146 points per weekly hour worked**. Top 41% get an award. One formula any applicant can check."

**Slide 8 · Pareto front (3:00–3:25)**
"We swept how much of the penalty to remove and compared against fairlearn's tools. Removing the bias improves fairness
*and* agreement with merit at the same time. The fairlearn methods barely move, because they measure fairness
against the biased labels."

**Slide 9 · Results (3:25–4:00)**
"Result: **41% in the centres, 41% in the regions**. Equal-opportunity gap from **0.30 to zero**. HxBuddy score **94.7%**,
up from 92.4% for our first version. 390 decisions change. And here's the part we care about: the students who gain
awards and the ones who lose them have **the same grades**. The ones who gain work **twice as many hours** and come
from families earning **half as much**. The old model was rewarding comfort, not merit."

**Slide 10 · Governance (4:00–4:35)**
"A fix is only as good as its monitoring, so we built it. `monitoring.py` checks every batch: budget, parity, every
region, income subgroups, and drift. We tested it on five scenarios. Someone redeploys the old model? **Stopped**, even
though the budget looks normal. Students inflate their hours? **Alert**, because otherwise 103 honest students lose their
award. Region and income are used only to measure bias, never to score. Applicants get a notice and a human review under Law 25."

**Slide 11 · Limits and takeaway (4:35–5:00)**
"What we can't claim: we never saw the jury's reference, and we disclose every leaderboard experiment. Hours worked are
self-reported, so they need verification. But the main lesson is simple: **the fix wasn't a better classifier. It was
refusing to treat past decisions as the truth.** Thank you."

---

## Likely questions and short answers

**Why equal opportunity and not demographic parity?**
A merit award promises equal chances to equally deserving students. Demographic parity forces equal rates even if merit
differs, and can be met while picking the wrong people in each group. As it happens, our model ends up with near-equal
rates too (40.9% vs 41.1%), because once the biases are removed, the two groups' merit is similar.

**You used the leaderboard 24 times. Isn't that overfitting?**
We used it as a controlled experiment, one ingredient per file, to answer two yes/no questions: does income belong in
merit (no) and which grant rate (41%). The hours weight came from the committee model, not from the leaderboard; the
experiments only confirmed it: seven nearby weight and rate variants all scored lower than the committee's 0.146 at 41%.
That is the opposite of overfitting: we tried to beat the principled choice and could not. We stopped when three more
rounds found nothing better, and every experiment is documented in
the audit notebook, section 6.

**You use the region in training. Isn't that discrimination?**
The opposite: we use it to *measure* the penalty so we can remove it. Without it the penalty hides in distance and postal
code (we show this). In production, region never enters anyone's score. This use must be documented under Law 25,
which `GOVERNANCE.md` covers.

**Why remove income? Shouldn't poorer students get more help?**
A merit scholarship shouldn't reward family wealth, and income is a regional proxy. We also tested the reverse
(need-based scoring): it scored worse against the reference. If the institution wants need-based support, it should be a
separate, explicit program, not hidden in a merit score.

**How do you know hours worked is merit and not another bias?**
Three signals: the committee weighted it the same way in both regions; leaving it out drops HxBuddy accuracy by more than
2 points; and students working long hours earn their grades under more pressure. The best weight (0.146) is exactly the
committee's own.

**Your equal-opportunity gap is 0.000. Isn't that circular?**
Partly, and we say so: that reference uses the same formula. The independent evidence is HxBuddy (94.7% against the
organisers' hidden reference) and the fact that our references put the production model's gap at 0.22–0.30, bracketing the
organisers' published 0.270.

**What about the 154 students in the centres who lose an award?**
They did nothing wrong. Their awards came from the penalty and the income bonus. We recommend a transition rule: awards
already granted are never withdrawn, renewals are honoured, and the new rule applies to new applications. No one loses an
award to an applicant with a lower merit score.

**Why not just use fairlearn's ThresholdOptimizer or ExponentiatedGradient?**
We tried both and they're on our Pareto plot. With TPR parity, they measure fairness against the biased labels, where the
model already looks fair, so they barely move. ExponentiatedGradient with demographic parity is a close competitor; we
prefer one readable formula whose setting means something.

**Why a simple linear model?**
On the committee's decisions, logistic regression fits better than gradient boosting (log-loss 0.259 vs 0.287). It's
auditable, explainable to applicants, and the leaderboard ceiling (~95%) comes from noise in the reference, not from model
capacity.

**Why not higher than 94.7%?**
Our fit says the reference contains randomness we can't see, roughly half an R point per applicant. A perfect formula would
score about 95%. The top five teams are all between 94.6% and 94.8%, which is consistent with that ceiling.

**What if someone lies about their hours?**
Our monitoring demo shows it: if a quarter of applicants added 6 hours, 103 honest students would lose their award. The
monitor raises a drift alert, and we recommend spot checks against pay stubs or employer letters.

**Does it work for other regions of Québec?**
The data only has five regions in two blocks. Before any wider roll-out, the audit must be rerun with all regions and at
intersections; the monitoring code already reports per region.

**What would you do with more time?**
Build an independent merit signal (first-year results, persistence, blind panel reviews) so equal opportunity can be
measured without relying on any committee, and recalibrate the monitoring thresholds on real batches.
