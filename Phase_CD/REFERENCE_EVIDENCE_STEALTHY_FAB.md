# Stealthy-Fab ("…to Unsafe Driving") — paired claim/evidence sheet (full read, 2026-07-21)

## STATUS: ⏳ CLAUDE'S FULL READ DONE — **AWAITING SRINIVASA'S REVIEW + A4 (cite + tighten)**
Full 16-page read (arXiv:2605.01301v1, incl. appendices A–C + all 64 refs). **NOVELTY VERDICT: our closed-loop
claim SURVIVES** — but this is the single closest challenger to it, so the fix is *cite it + tighten one
clause* (exactly the triage call). Two honesty flags found (a stealth/harm-bind concept overlap; a shared
defense primitive). Bibliography scan: **zero new family members.** Closed only after Srinivasa's own read +
the manuscript edits.

**The paper:** Qingzhao Zhang (Univ. of Arizona), Runting Zhang, Z. Morley Mao (Univ. of Michigan),
*"From Stealthy Data Fabrication to Unsafe Driving: Realistic Scenario Attacks on Collaborative Perception"*,
arXiv:2605.01301v1 (2 May 2026, cs.CR). ⚠ VENUE = **preprint** — the PDF carries an ACM template with
placeholder "Conference acronym 'XX / 2018"; not yet a named venue (cs.CR + the Mao/CAD lineage ⇒ a security
venue target). Same **arXiv-preprint venue-recheck class** as PRBI/CoDynTrust/TrustFlip. PDF:
`Phase_CD/Research paper/Stealthy-Fab.pdf` (16 pp; verified page-1 header = correct paper, not a duplicate).

**What the paper does (their own words):** *"we present a stealthy, scenario-realistic data fabrication attack
that induces unsafe driving behaviors through end-to-end system effects. Instead of creating large, easily
detectable anomalies, our attack subtly manipulates the poses of existing objects in shared perception
results, keeping perturbations below detection thresholds. These small errors are then propagated through
downstream modules, including object tracking and trajectory prediction, leading to significant deviations in
predicted behaviors and ultimately unsafe driving decisions"* (Abstract). Contributions: **PosePert** (an
intermediate-fusion feature-map attack that shifts a target vehicle's *perceived pose* by <1 m via multi-view
ray-cast init + a learned PertNet); a **scenario-aware** observe–predict–plan–execute attack loop; and
**PoseGuard** (an object-level, safety-critical-region anomaly detector). Task = single-victim CAV driving;
downstream stack = **AB3DMOT tracking + GRIP++ / Trajectron++ prediction**; datasets = OPV2V + V2X-Real;
metrics = detection %Success/IoU + **ADE/FDE/MinDist/%Danger** (a scripted "would-brake" flag). Attack ≥90%
detection-error success, up to 50% "danger"; existing defenses (CAD/LUCIA/MADE/ROBOSAC/MATE) <13% TPR;
PoseGuard 57–84%.

---

## ⭐ THE NOVELTY CHECK (the reason this paper was flagged) — our claim SURVIVES
Our compound claim (related.tex l.158–162): *"…no prior work evaluates fabricated-obstacle attacks on
collaborative perception **inside a closed-loop learned navigation task (success, not detection accuracy, as
the end metric)**, analyzes … consistency-based trust with sensor noise …, closes … with a cross-agent temporal
bias test, and stress-tests … an adaptive attacker …."* It is an **AND** of four things. Stealthy-Fab, at most,
brushes the first. It does NOT satisfy it, on **four independent axes** (all with verbatim backing):

| Axis | OURS | Stealthy-Fab | Differentiates? |
|---|---|---|---|
| **Control layer** | a **learned RL navigation policy** consumes the attacked map and **executes an action every step** | a **modular pipeline** (AB3DMOT tracker → GRIP++ predictor); **no control policy in the loop** | ✅ |
| **End metric** | **navigation success** (did the agent reach its goal) | **prediction error** (ADE/FDE/MinDist) + a **scripted %Danger flag** (predicted trajectory crosses the lane within 5 m) | ✅ |
| **"Closed-loop" of the victim** | the agent **actually navigates and reacts** step-by-step; state evolves from its own actions | victim driving is **not simulated**; impact is *read off the prediction pipeline on replayed dataset trajectories* | ✅ |
| **Attack primitive** | **fabricated (phantom) obstacles** that are not in the ground truth | **pose-shift of EXISTING real objects** via a feature-map δ (creates no new obstacle) | ✅ |
| **Setting** | **multi-robot swarm** cooperatively navigating (10 agents) | **single victim vehicle** | ✅ |

**THEY WROTE (the load-bearing quotes):**
- Modular pipeline, not a learned policy: *"the downstream autonomous driving stack uses AB3DMOT … for
  multi-object tracking and GRIP++ … for trajectory prediction"* (§6.1). There is **no navigation/control
  policy** — the pipeline ends at prediction.
- Metric is a predicted-danger flag, not executed success: *"%Danger, the fraction where emergency braking
  would typically be triggered: predicted trajectory enters victim's lane … AND MinDist<5m"* (§6.3.1). And the
  case study: *"making the predicted future trajectory cross with the victim's path and triggering a safety
  response"* (§6.3.3) — i.e. the "response" is **inferred from the prediction**, not simulated.
- Attack shifts existing objects (not fabricated phantoms): *"our attack subtly manipulates the poses of
  existing objects"* (Abstract); *"object pose perturbation … subtly shifts existing detections"* (§2). Their
  own Table 1 labels it "Pose Perturb," distinct from "Spoof" (create) / "Remove."
- Single victim: *"a designated victim vehicle"* threat model (§4); scenarios have 2–5 vehicles, one victim.

**Bottom line:** their headline is *"unsafe driving"* via a **perception→tracking→prediction** pipeline scored
by a **prediction-based danger flag** on **replayed single-vehicle scenarios**. OURS is a **learned control
policy executing in a closed loop** scored by **task success** in a **multi-robot swarm**, under a **fabricated-
obstacle** threat. The claim holds. **RECOMMENDATION: cite it (it IS the closest driving-consequences work) and
tighten one clause** so no reviewer conflates "unsafe driving" with "closed-loop learned navigation."

---

## TWO HONESTY FLAGS (must not over-claim next to this paper)
**FLAG 1 — Stealthy-Fab ALSO exhibits a stealth/harm tradeoff.** Do NOT present the *concept* of a stealth/harm
bind as ours-first. Theirs: *"using large perturbations (β≫1) increases the probability of shifting the
detection but also increases the anomaly score … Conversely, small perturbations (β≈1) evade detection but fail
to shift the object reliably"* (§5.3.3); *"a tradeoff between attack effectiveness and stealthiness"* (§1).
**Their bind is via perturbation MAGNITUDE (β) against a feature-level detector; OURS is via geometric
PLACEMENT (phantom offset) against a temporal geometric test in closed-loop navigation.** Frame our stealth/
harm analysis as *the bind in our specific setting*, not as first discovery of the phenomenon. (Our
contribution wording "stress-tests the closure against an adaptive attacker" is a *robustness* claim, not a
"first tradeoff" claim — so it is already safe; just don't upgrade it in edits.)

**FLAG 2 — PoseGuard shares the "verify against own sensing" primitive but does NOT pre-empt our temporal
mechanism.** PoseGuard Stage 2 = *"compares the fused detection … with the ego-only detection … If the two …
agree … genuine"* (§5.3.2) — the same fused-vs-ego primitive we already attribute to the object-level family
(CAD/ROBOSAC/MATE) in our "On baseline comparison" paragraph. Stage 3 = **single-frame, feature-level** per-
object L1 (*"following LUCIA's methodology … but applied per-object"*). It is **not temporal, not geometric-
offset, not cross-agent-accumulated** — so it does not touch our temporal offset-bias contribution. If we cite
PoseGuard, bracket it with the object-level/feature-level family, never as a temporal analogue.

## Corroborations noted (useful under reviewer fire; no manuscript change)
- **Whole defense family fails on stealthy perturbations:** *"Existing defenses (CAD, LUCIA, MADE, ROBOSAC,
  MATE) largely fail under these constraints, detecting fewer than 13% of attacks"* (§1). Independent support
  for our motivation that threshold/consensus defenses miss sub-threshold attacks — cite via Stealthy-Fab if a
  reviewer asks "do these defenses not already work?", but note the attack class differs (feature pose-shift vs
  our geometric phantom).
- **They confirm our reference-signal story on the tracker/predictor:** *"the tracking module … converges to
  the biased trajectory, and the prediction module extrapolates the bias"* (§3) — a *temporal* amplification of
  a *persistent* bias, conceptually adjacent to why our persistent-offset test works; different layer, note only.

## Second-order sweep — 64-ref bibliography: title scan 2026-07-21 + ABSTRACT pass 2026-07-26
⚠ **CORRECTION (2026-07-26):** the title scan's "zero new" was over-stated. The abstract pass
(`SECOND_ORDER_ABSTRACT_PASS.md`) surfaced **[18] Cui et al., "Coopernaut: End-to-End Driving with Cooperative
Perception for Networked Vehicles" (CVPR'22)** — a **benign** precedent (no attacker/trust) that is
nonetheless the **closed-loop-learned-CP-driving-with-success-metric *paradigm*** our combination-novelty
sentence leans on. It does **NOT** pre-empt our security contribution, but **requires a citation + a
novelty-wording safeguard** (credit Coopernaut for the benign paradigm; we own the attack+defense layer). I
had title-rejected it as "plumbing." Full-PDF read owed once Srinivasa provides `Coopernaut.pdf`. **Zero new
*defense/attack* family members otherwise.** The CP-security refs are all **already tracked**: CAD [59], MADE [62], ROBOSAC [27],
MATE [20], LUCIA/SOMBRA [49], PB/Pretend-Benign [30], CP-Guard+ [21], Tu et al. 2021 [47]. Downstream stack:
AB3DMOT [51], GRIP++ [26], Trajectron++ [40] (tracking/prediction models — methodology). A **trajectory-
prediction / tracking-attack cluster** ([32] Zhang adv-robustness-of-trajectory-prediction CVPR'22, [33]
ControlLoc, [35] physical hijacking of object trackers CCS'22, [58] trajectory-prediction attack) — these
attack the **downstream predictor/tracker**, not the collaborative-perception *trust* layer; our paper does not
model that layer → **out of family, not promoted.** Single-vehicle sensor-attack line ([13][19][22][28][41][46]
[64] Cao/Jin/Tu/Shen/Zhu — GPS/LiDAR spoofing, physical objects, camera-LiDAR fusion) — already bracketed by our
3D-TC2/ADoPT paragraph. CP architectures/datasets (AttFusion/V2VNet/CoBEVT/OPV2V/V2X-Real, F-Cooper, Coopernaut,
EMP, VIPS) — plumbing. Adversarial-ML classics (PGD). **No new collaborative-perception trust/consistency-
defense member beyond what we already cite.**

## PROPOSED WE-WRITE (for A4 — cite + tighten; Srinivasa's call)
Add near the combination claim (related.tex ~155–162), and tighten the closed-loop clause:
> "Closest in outcome, the recent PosePert attack~\cite{stealthyfab2026} propagates small,
> stealthy pose perturbations of \emph{existing} objects through a modular tracking-and-prediction stack to
> induce driving-level consequences on a single vehicle, measured by trajectory-prediction error and a
> scripted braking-risk rate. Our setting differs in the attack (fabricated obstacles, not pose shifts of real
> ones), the control layer (a learned navigation policy executing in closed loop, rather than a
> tracker-plus-predictor pipeline), the end metric (task success, not prediction error or a safety flag), and
> the multi-robot rather than single-vehicle scope."

Optional micro-tighten of l.160: keep "closed-loop learned navigation task (success … as the end metric)" — it
already excludes them; the sentence above makes the exclusion explicit so a reviewer can't conflate the two.

## Srinivasa's verification checklist (page pointers, arXiv v1)
| # | what to check | where in PDF |
|---|---|---|
| 1 | attack = pose-shift of EXISTING objects (not fabricated phantoms) | p.1 Abstract + p.2 §2 + p.3 Table 1 |
| 2 | downstream = AB3DMOT + GRIP++/Trajectron++ (modular; NO learned control policy) | p.9 §6.1 |
| 3 | metric = ADE/FDE/MinDist + %Danger (predicted-braking flag), not navigation success | p.11 §6.3.1 |
| 4 | single victim vehicle; scenarios 2–5 vehicles | p.4 §4 + p.9 §6.1 |
| 5 | their stealth/harm tradeoff (β magnitude vs feature detector) — FLAG 1 | p.1 §1 + p.8 §5.3.3 |
| 6 | PoseGuard = single-frame, per-object feature L1 + fused-vs-ego filter — FLAG 2 | p.8 §5.3.2 |
| 7 | existing defenses <13% TPR on their attack | p.2 §1 + p.10 Table 2 |

## Bookkeeping — TODO before A4
- **refs.bib entry does NOT exist.** Add (venue TODO-VERIFY, currently preprint):
  `@misc{stealthyfab2026, title={From Stealthy Data Fabrication to Unsafe Driving: Realistic Scenario Attacks
  on Collaborative Perception}, author={Zhang, Qingzhao and Zhang, Runting and Mao, Z. Morley}, year={2026},
  note={arXiv:2605.01301}}`. Re-check for a named venue before submission (same class as PRBI/TrustFlip).
- Not cited in any section yet → A4 insert is a NEW citation.
- No catches against existing text; the two edits are (a) the cite+differentiate sentence above, (b) leaving the
  compound claim intact (it survives). FLAGS 1–2 are guardrails for the wording, not required edits.
