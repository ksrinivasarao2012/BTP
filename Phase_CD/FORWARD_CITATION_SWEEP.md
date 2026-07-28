# FORWARD-CITATION SWEEP — TRACKER + CITATION LEDGER
_Started 2026-07-28. Single source of truth for "who cited our anchors AFTER publication."_

**Why this exists.** Every earlier sweep was **backward** (we read our competitors' bibliographies). A
bibliography can only contain papers **older** than the citing paper — so ~300 backward abstracts could not, even
in principle, surface a 2025–26 paper that beats us. This sweep goes **forward**: who *cites* our anchors.

**Headline.** Backward sweep found **0** new competitors. This forward sweep has already found **~35 new papers**,
**6 must-cites**, and **3 overstated claims**. It is **only 21% complete**.

⏳ **Nothing here is closed until Srinivasa audits it** (standing rule). None of it is in `related.tex` yet.

---

# PART 0 — 🚨 METHOD DEFECT FOUND AND VERIFIED (2026-07-28, Srinivasa's catch)

**All citer counts recorded before this date are UNRELIABLE. The fetch summariser silently drops rows.**

### How it was proven
| Test | Call | Result |
|---|---|---|
| **Boundary** | `offset=200, limit=5` | `{"offset":200,"data":[]}`, **no `next` field** → list ends before 200 |
| **True end** | `offset=180, limit=10` | **9 entries** → Coopernaut's real count is **189** |
| **The defect** | same offset, earlier call at `limit=20` | reported only **7** — **2 rows silently dropped** |
| **Faithfulness** | `offset=0, limit=5` | exactly **5**, matching the earlier first-5 → **limit=5 is faithful** |

### Why it matters — the dropped rows were not random
The two rows dropped at `limit=20` were **both UAV/drone collaborative-perception papers** — the closest
platform match to this entire project:
- **C2F-Net** (IEEE'25) — coarse-to-fine **multi-drone** collaborative perception for object trajectory
  prediction; mIoU/VPQ metrics; introduces the **CoD-Pred** simulation dataset. ✅ read — **benign, no
  adversary, no trust** → NO CITE (but note it as evidence that multi-drone CP is an established setting).
- **AVCPNet** (IEEE TGRS'25) — **AAV–vehicle (aerial-ground)** collaborative 3-D detection; cross-domain
  cross-adaptation module; **V2U-COO** dataset. ✅ read — **benign, no adversary** → NO CITE (same note).

### Consequences
1. **Coopernaut = 189**, not 187 and certainly not the 43 the first pass claimed.
2. Every other anchor count in Part 1.1 (CAD 31 · ROBOSAC 45 · TruPercept 32 · ADoPT 21 · 3D-TC2 33 ·
   CP-Guard 15 · MADE 12 · GCP 11) is **suspect and probably an undercount** — each was gathered with a
   single large-limit call or 15–20-sized batches.
3. **Standing method rule from now on: paginate citation lists at `limit=5`** (the only size verified
   faithful), and **always probe the boundary** with a high offset to confirm the true end.
4. The "~240 citing papers examined" figure previously reported is **wrong**; the real total is higher and
   currently unknown.

**Nothing in the verdicts below is invalidated** — every paper that *was* read was read properly. The defect
is one of **coverage**, not of judgement: papers were missed, not misjudged.

---

# PART 0b — FULL-ABSTRACT PASS OVER THE HIGH-RISK SUBSET (2026-07-28, in progress)

Srinivasa's instruction: the 4-field rows are a summariser's output, not the abstracts themselves. So the
papers where a hidden security/temporal contribution is *plausible* — anything whose row flagged noise,
uncertainty, robustness, anomaly, consistency or a safety metric — are being re-read **one call per paper,
full abstract**. ~30 identified; **12 done**.

| Paper | Venue/Yr | What the full abstract actually says | Verdict |
|---|---|---|---|
| **UNCAP** | AAMAS'26 | CAVs transmit NL messages that *"quantitatively express their perception uncertainty"*; two-stage protocol; +31% driving-safety score | benign — uncertainty for **planning**, no adversary |
| **COOPERTRIM** | 2602.13287 | *"Conformal temporal uncertainty metric"* to gauge **feature relevance**; 80% bandwidth cut | benign — uncertainty for **transmission selection** |
| **UniSense** | MobiSys'25 | Uncertainty-driven sensor-data exchange; range 80→140 m, 1.33× accuracy | benign — uncertainty for **data exchange** |
| **A2MAML** | 2602.04763 | Per-modality stochastic estimates + **Bayesian inverse-variance weighting** to *"suppress corrupted or noisy modalities"*; +18.7% accident detection | benign — weighting for **sensor corruption**, not deception |
| **CAML** | NeurIPS'25 | Cross-modal distillation, infer with fewer modalities; +58.13% accident detection | benign — **missing modalities** |
| **DRCP** | 2509.24903 | Cross-modal fusion + diffusion refinement; "noise accumulation" = detection noise | benign |
| **SEAL** | 2506.21041 | VLM cooperative driving under **long-tail weather**; recalibrates *"ambiguous or corrupted features"* | benign — weather degradation |
| **MMCD** | IROS'25 | Teacher-student distillation for **missing modalities / missing vehicles**; +20.7% driving safety; aerial-ground | benign — **sensor failure** |
| **RCDN** | NeurIPS'24 | Neural rendering field to *"recover failed perceptual messages"* under **camera failure**; OPV2V-N dataset | benign — **recovery**, not detection |
| **RAO** | MobiCom'23 | Motion-compensated occupancy-flow fusion of **asynchronous** sensor data; +34% coverage. *(Authors incl. Q. Zhang & Z.M. Mao — the CAD group, writing benignly)* | benign — **asynchrony** |
| **Communication-Critical Planning** | Glaser & Kira'23 | Distributed, **uncertainty-aware**, bandwidth-efficient costmap planning; hard-collision rate −57% with 8 agents | benign — multi-agent + uncertainty + collision metric, **no adversary** |
| **GP3Net** | AAAI'24 | Spatiotemporal graph + PPO, CARLA route completion/infractions | benign — **single-vehicle** planning |
| **ER-CoPe** | IEEE T-ITS'25 | ✅ **FOUND** — full title is *"Efficient Collaborative Perception With Integrated Uncertainty Estimation via **Evidence Regression**"*. Evidential deep learning; Normal-Inverse-Gamma over **bounding-box parameters**; aleatoric + epistemic; OPV2V/V2X-Set | benign — uncertainty on **box regression**, no adversary. *(Earlier "not locatable" was my error: I searched the acronym, not the title.)* |
| **CoPeD** | RA-L'24 | Real-world **air-ground multi-robot** CP **dataset**; explicitly names *"sensor noise, occlusions, and sensor failures"* as challenges | benign — a dataset, no adversary. ⭐ platform-relevant (air-ground robots, RA-L) |
| **CoBEVFlow** | NeurIPS'23 | Compensates **temporal asynchrony** (delays, interruptions, clock misalignment) by reassigning features along BEV motion vectors; IRV2V dataset | benign — temporal used for **alignment**, not detection |
| **V2X-Boosted Federated Learning** | 2305.11654 | FL **client selection** by predicted communication latency | benign — not perception security |
| **Toward Ensuring Safety for AD Perception** | T-ITS'24 | **Standardisation + safety survey** (standards progress, research advances) | benign survey ⚠ *own abstract not fully retrieved — IEEE-walled* |
| **End-to-End Urban AD With Safety Constraints** | — | ⚠ **Not cleanly resolved** — searches returned adjacent single-vehicle RL-driving papers, not this one's own abstract. Clearly single-vehicle end-to-end RL with safety constraints, **no CP, no adversary**, but its own text was not obtained | **incomplete — treat as unverified** |

| **Towards V2X AD: Survey on CP** | 2308.16714 | ⭐ Surveys CP from many angles **including "attack/defense"**, AND separately benchmarks *"various simulated real-world noises… communication latency, lossy communication, localization errors, and mixed noises"*; names security as an open challenge | ⭐ **UPGRADE TO GROUP CITE** — the one survey covering **both** our axes, and it treats them in **separate sections**, which is citable evidence for the disjointness argument below |
| **AFFormer** | 2605.01888 | ⭐ Closest on *mechanism*: **"Multi-Agent and Temporal Aggregation… across agents and over time"** + **"Uncertainty-Guided Fusion"** (entropy-driven) + handles **"corrupted features"** | **No adversary** — corruption is **channel impairment** (noise, fading, interference), metrics = detection on V2XSet/DAIR-V2X. ⭐ **GROUP CITE as a boundary contrast**: cross-agent temporal + uncertainty already exists — *for channel noise, never for deception* |
| **CMiMC / What Makes Good Collaborative Views** | AAAI'24 | Contrastive mutual-information maximisation between pre- and post-collaboration features | benign — **fusion quality** |
| **Learning for V2V CP under Lossy Communication** | T-IV'22 | LC-aware Repair Network + **"uncertainty-aware inter-vehicle attention"** | benign — per-neighbour uncertainty weighting, but for **lossy comms**, not malice |
| **SiCP** | 2312.04822 | Dual-Perception Net supporting standalone **and** cooperative detection | benign |
| **Enhanced CP Using Imperfect Communication** | 2404.08013 | Selects the best **helper** by visual range + motion blur; radio-block optimisation | benign — helper selection |

## 🔑 THE FINDING THIS PASS PRODUCED — two disjoint literatures

Across every uncertainty-aware collaborative-perception paper read at full-abstract depth, **uncertainty is
used for fusion quality, bandwidth, sensor failure, weather, asynchrony or missing modalities. Not once is it
used to decide whether a neighbour is LYING.**

Conversely, every adversarial-CP paper (CAD, MADE, GCP, CP-Guard, ROBOSAC, CP-uniGuard, PRBI…) **assumes clean
sensing** and treats disagreement as evidence of attack — CP-Guard's threat model *"assumes adversarial
perturbations only"*; GCP *"does not explicitly model"* honest noise.

**The uncertainty-aware CP community and the adversarial CP community have not met.** Our contribution sits
precisely in that gap: the false-positive regime that appears only when honest ranging noise and a lying agent
are present *at the same time*.

**Use this framing in the paper** — it is stronger and safer than any "first to do X" claim, because it
describes a structural gap in the literature rather than asserting priority, and every claim-rewording in
Part 4 remains intact underneath it.

---

# PART 0c — ✅ VERBATIM VERIFICATION OF THE LOAD-BEARING QUOTES (2026-07-28)

**Method breakthrough.** Both WebFetch and WebSearch pass everything through a summarising model — WebFetch
truncates quotes to ~125 chars, WebSearch rewrites into an "Abstract Summary". So no claim sourced through them
could be certified verbatim. **Fix: `curl` the paper to disk, then `Read` the file — Read returns raw bytes with
no model in between.** Network from Bash works. Procedure now used:
1. `curl "http://export.arxiv.org/api/query?id_list=<ids>"` → Atom XML with **verbatim abstracts**
2. `curl "https://arxiv.org/pdf/<id>"` → PDF; extract with **pypdf**; regex the Conclusion section
3. `Read` the resulting file directly

Applied to the **8 papers our manuscript actually QUOTES** (the only ones where exact wording is checkable by a
reviewer). Files in the session scratchpad: `abs7.xml`, `conclusions.txt`, `extract.py`.

## 🚨 CORRECTION — CATS: my differentiator was WRONG (and the real one is better)

**What I claimed:** *"CATS requires an honest majority"* — planned as the foil for our no-honest-majority result.
**What CATS actually says (abstract, verbatim):** it *"blends together the best traits of reputation-based **and**
majority-based detection mechanisms"* — it combines them precisely to escape each one's weakness. **My claim was
an overstatement and must not be written.**

**The REAL differentiators vs CATS, all quoted from its own text:**
- ⭐ *"**Sensor attacks: Sensor-based attacks (e.g., fooling LiDARs with lasers) are considered out of scope**"* —
  CATS explicitly excludes the perception-level attack class that **is** our entire threat model. Cleanest
  possible differentiator, in their words.
- Threat model is *"bad data … of misbehaving vehicles"* covering *"malfunctioning vehicles"* and *"malicious
  vehicles"* — **message-layer**, not fabricated obstacles in the LiDAR field.
- Heavy infrastructure assumptions we do not make: *"the centralized Security Authority (SA) is trusted"*,
  private keys *"securely stored in tamper-proof hardware"*, plus an **out-of-band internet channel** for voting.
- Metric = message filtering, **not** driving success: *"an average 230x reduction of bad messages, while making
  a small (**4.2x on average**) tradeoff for **blocking good messages**"* → ⭐ **they DO block honest traffic; our
  no-harm column is flat.** This is a strong, quotable contrast.

## ⭐ MAJOR FIND — the V2X survey independently validates our σ = 0.6 m

`2308.16714` §5.5, verbatim: *"cooperative perception models are trained in the environment of perfect
localization while tested in an environment with simulated localization noises… The noises are sampled from
Gauss Distribution, with a mean of 0 and a changeable standard deviation."* And: *"early fusion is much more
sensitive to localization error, whose **AP@0.5 drops 70.5% when position error std is 0.6m**."*

**A 2023 survey shows collaborative perception collapsing at exactly σ = 0.6 m — benignly, with no attacker.**
Third-party support for both our noise regime and our specific σ. **Cite this in the setup/parameter
justification**, not just related work.

## Verbatim conclusions obtained

| Paper | Verbatim conclusion evidence | Effect on our claims |
|---|---|---|
| **SafeCoop** | *"Closed-loop evaluations on 32 CARLA scenarios show that SafeCoop substantially mitigates adversarial impact and can succesfully detect corrputed channels with up to 67.32% F1 score"* | ✅ confirms the driving-score claim-rewording #1 |
| **CONClave** | *"CONClave was able to detect more categories of faults and errors, **including both malicious and unintentional errors**, while being faster than … TruPercept"* | ✅ confirms fault+malice scope; **no driving metric** |
| **MVIG** | *"MVIG identifies vulnerable regions and optimal attack timing through spectral graph analysis and **temporal modeling**"*; future work: *"finding effective **defense strategies against such attacks**"* | ✅ confirms adaptive+temporal attack. ⭐ They explicitly call for the defense — **we are it** |
| **AFFormer** | *"jointly modeling **inter-agent, temporal, and spatial** correlations"*; limitation: *"The current framework **does not explicitly account for communication delays or packet loss**"* | ✅ confirms cross-agent temporal exists for channel noise; and its scope is narrower than the abstract implies |
| **LiDAR-Spoofing** (2302.07341) | ⚠️ **No conclusion section exists** — 9-page conference paper ending at references. Abstract verified verbatim | abstract-level claims stand |
| **Towards V2X Survey** | see σ=0.6 m find above | ⭐ upgraded from group-cite to a **setup-section cite** |

## Verified-verbatim quote bank (safe to put in the manuscript)
- LiDAR-Spoofing: *"spoofing attacks can typically only be mounted on **one vehicle at a time**"* · *"a control
  algorithm that **guarantees** that these estimated object locations are avoided"*
- SafeCoop: *"**69.15% driving score improvement** under malicious attacks"*
- CATS: *"Sensor-based attacks … are considered **out of scope**"* · *"**4.2x** … tradeoff for blocking good messages"*
- AFFormer: *"Multi-Agent and Temporal Aggregation for context-aware fusion **across agents and over time**"*
- MVIG: *"**temporal graph learning** to generate evolving fabrication risk maps"*
- Survey: *"AP@0.5 drops 70.5% when position error std is **0.6m**"*

## ⚠️ Still unverified
**RLCVP** (IEEE TMC 11006384) — not on arXiv, paywalled. It is a **Level-1 must-cite**, so its differentiator
sentence rests on abstract-level evidence only → `INSTITUTE_WIFI_TODO.md`.

**Standing rule added:** any paper we **quote** must be verified via the curl→Read path (or from a PDF on disk)
before its sentence goes into the manuscript. Papers we merely **list** in a grouped citation do not need this.

---

# PART 0d — 📋 PAPERS WITH **NO VERDICT** (the auditable unreachable list)

**Why this exists.** Unreachable papers were previously recorded as *counts* ("7 have no abstract") scattered
across three files. A count cannot be audited — you cannot check whether any of the 7 mattered. Every paper
that never received a verdict is now listed **by name**, with the anchor it came from and the wall it hit.

**Rule: nothing here is "safe". These are UNKNOWN.** They are excluded from every "0 pre-emptions" statement.

## A. NOT LOCATABLE — no abstract exists anywhere online (11)
These appear only as entries in other papers' reference lists. Repeated searches returned nothing.

| # | Paper | From anchor | Note |
|---|---|---|---|
| 1 | **An Attack Detection Method Based on Spatiotemporal Correlation** (2022) | 3D-TC2 | ⚠ "spatiotemporal" in the title — would want this one if it were reachable |
| 2 | **A Novel Multi-layer Task-centric Framework** (2025) | 3D-TC2 | title gives nothing away |
| 3 | **Stealth in Sight: Model-Free Assessment** (2026) | 3D-TC2 | — |
| 4 | **Secure3D-CV** (2026) | ADoPT | — |
| 5 | **End-to-End Urban Autonomous Driving With Safety Constraints** | ROBOSAC | ❗ **3 separate search attempts failed.** Appears single-vehicle RL driving with safety constraints — but never confirmed from its own text |
| 6 | **Sense2Com** (2026) | Coopernaut | sensing/comm/compute coordination per title |
| 7 | **Talking Vehicles: Cooperative Driving via Natural Language** | Coopernaut | no year listed in the record either |
| 8 | **QUEST: Query Stream for Vehicle-Infrastructure CP** | Coopernaut | (a different QUEST was read via CoDynTrust; this V2I variant had no abstract) |
| 9 | **An Efficient and Robust Object-Level Cooperative Perception Framework** (2022) | Coopernaut | ⚠ **object-level**, like ours — worth a look if ever reachable |
| 10 | **Co-driver: VLM-based Autonomous Driving Assistant** | Coopernaut | — |
| 11 | **A Survey on Autonomous Driving Datasets** (2024) | Coopernaut | survey |

## B. PAYWALLED — abstract obtained, **conclusion blocked** (9)
Verdict assigned on abstract only. Listed in `INSTITUTE_WIFI_TODO.md`.

| # | Paper | Wall | Priority |
|---|---|---|---|
| 12 | 🚨 **RLCVP** (IEEE TMC 11006384) | IEEE | **PRIORITY 0 — Level-1 must-cite, differentiator unverified** |
| 13 | **Fake-Objects-CPM Trust** (Springer LNCS) | Springer login | HIGH — fabricated objects + per-neighbour trust |
| 14 | **FNO-Guard** | ScienceDirect | group-cite |
| 15 | **Robust-CP: Adv. Training + Consensus** | IEEE (HTTP 418) | group-cite |
| 16 | **Adversarial CP in Autonomous Driving** | IEEE (HTTP 418) | group-cite |
| 17 | **Trust-Mgmt Framework for MDS in CP Services** (ICARCV'22) | IEEE + HAL Anubis | group-cite |
| 18 | **Yuce survey — MDS with CP in V2X** | Wiley | group-cite |
| 19 | **UniSense** (MobiSys'25) | ACM DL | no-cite |
| 20 | **Toward Ensuring Safety for AD Perception** (T-ITS'24) | IEEE | no-cite |

## C. WALL-BLOCKED — **title + venue only**, no abstract retrieved (6)

| # | Paper | Wall |
|---|---|---|
| 21 | **Sieve** (2026) | not indexed |
| 22 | **ALADCP** (2026) | ⚠ **late-fusion = object-level, like ours** — no text anywhere |
| 23 | **CIAK-CP** (ACM SAC'26) | ACM DL (try Zenodo 17804455) |
| 24 | **HA-GAN** (2026) | not indexed |
| 25 | **Point Cloud Object Tampering Attacks** (2025) | not indexed |
| 26 | **Zhang 2024 PhD thesis — Misbehavior Detection for CP** | HAL Anubis bot-block |

## Summary

| Category | Count |
|---|---|
| A. Not locatable | **11** |
| B. Abstract only, conclusion walled | **9** |
| C. Title only | **6** |
| **TOTAL WITH NO / PARTIAL VERDICT** | **26** |

**Of these, 4 would matter most if they turned out to be competitors:**
`RLCVP` (Level-1 must-cite) · `Fake-Objects-CPM` (fabricated objects + trust) · `ALADCP` (object-level like ours)
· `Attack Detection via Spatiotemporal Correlation` (temporal in the title).

**Resolved after initially being logged unreachable:** ER-CoPe (found — full title is *"Efficient Collaborative
Perception With Integrated Uncertainty Estimation via Evidence Regression"*, T-ITS'25) · Plug-and-Play/PnPDA
(ECCV'24) · Vehicle-road CP Technology (Acta Automatica Sinica). Kept here as a reminder that "not locatable"
sometimes just means the wrong search string.

---

# PART 1 — PROGRESS TRACKER

## 1.1 Anchors swept: **4 of 19 (21%)**

| # | Anchor | arXiv ID | Citations pulled | Status |
|---|---|---|---|---|
| 1 | **CAD** (USENIX Sec'24) | 2309.12955 | 31 | ✅ DONE |
| 2 | **ROBOSAC** (ICCV'23) | 2303.09495 | 45 | ✅ DONE |
| 3 | **TruPercept** (IEEE IV'20) | 1909.07867 | 32 | ✅ DONE |
| 4 | **Coopernaut** (CVPR'22) | 2205.02222 | **187** | ✅ **RE-DONE PROPERLY 2026-07-28** — 180 individually assessed, 7 no-abstract |

### ⭐ COOPERNAUT RE-SWEEP (2026-07-28) — the first pass was bulk-screened; this one is per-paper
The original Coopernaut pass (and CAD / ROBOSAC / TruPercept) predates Srinivasa's zero-title-grade rule and
was **bulk-screened**. Re-done properly: the citation list was pulled in batches and **every paper got its own
row** derived from **its own abstract** — adversary? metric? cross-agent temporal? honest-noise modelled?
The API reported **187 citers** (far more than the 43 the first pass saw). **180 assessed · 7 have no abstract
published anywhere → logged UNKNOWN, no verdict** (incl. `Sense2Com`, `Talking Vehicles`, `Plug and Play`).

**Result: ZERO new competitors across all 187.**

**Every adversarial paper in the list was already known or is out-of-family:**
| Paper | Status |
|---|---|
| RCDM · TrustFlip · SafeCoop · CP-FREEZER · CATS · BadMDA · CAD | already read/categorised |
| **V2XP-ASG** (2022) | adversarial *scene generation* (perturbs agent poses), AP-scored — out |
| **Edge-Assisted CP Against Jamming & Interference** (TWC'25) | **jamming/interference = availability**, RL chooses regions/channel/power. Not fabrication — out |
| **RCP-Bench** (CVPR'25) | "corruptions" = **weather / sensor failure / temporal misalignment**, *not* malicious agents. Benign robustness benchmark — out |
| **Robust & transferable end-to-end navigation** (2024) | adversarial training on **one vehicle's** sensor input; no collaborative perception — out |

### 🔑 THE MOST USEFUL PATTERN THIS RE-SWEEP REVEALED
**Driving-success metrics are completely standard in the benign learned-CP-driving family.** At least 15 of
Coopernaut's descendants score exactly the way we do — and **none of them has an adversary**:
*Defer-to-Plan* (driving score 79.72) · *CooperDrive* (TTC, stopping margin) · *E2E-V2X-CP* (driving score) ·
*CoopReflect* (collision avoidance) · *UNCAP* (+31% driving-safety score) · *MMCD* (+20.7% driving safety) ·
*SafeEdge* (96% success rate) · *GP3Net* (route completion, infractions) · *ReasonNet* (CARLA) ·
*Toward Collaborative Autonomous Driving* (driving score + collision rate) · *Select2Drive* (route completion) ·
*V2V-LLM* (collision rate) · *ICOP* · *VI-Planning* · *Communication-Critical Planning* (collision rate).

**Only SafeCoop combines a driving-success metric WITH an adversary — and it is language-layer, not geometric.**

**Why this helps us:** it reframes claim-rewording #1 from a weakness into a strength. Our metric is not exotic
— it is the *native* metric of the learned-CP-driving family. What is unoccupied is the **intersection**:
driving-success metric **+** a fabricating adversary **+** ranging noise **+** cross-agent temporal offset.
Say it that way, citing the benign family for the metric and SafeCoop for the adversarial precedent.
| 5 | **ADoPT** (BMVC'23) | 2310.14504 | 21 | ✅ DONE 2026-07-28 |
| 6 | **3D-TC2** (MAISP'21) | S2 `114a30a0…` | 33 | ✅ DONE 2026-07-28 |
| 7 | **CP-Guard** (AAAI'25) | 2412.12000 | 15 | ✅ DONE 2026-07-28 |
| 8 | **MADE** (IROS'24) | 2310.11901 | 12 | ✅ DONE 2026-07-28 — **0 new competitors** |
| 9 | **GCP** (TDSC'25) | 2501.02450 | 11 | ✅ DONE 2026-07-28 — **0 new competitors** |

### GCP sweep result — clean (2026-07-28)
11 citers. **9 already read** via other anchors (Multi-Agent-Embodied-AD, Security-in-Collaborative-Driving,
V2XCrafter, PRBI, RecoverMark, MVIG, Decoder-Gradient-Shields, Task-Aware-PEFT, CP-Guard). Only **2 new**, both
read to abstract + conclusion, both benign:

| Paper | Verified reason it is out |
|---|---|
| **FRUC** (2605.29997) | Feedforward **3D Gaussian-splatting scene reconstruction** from uncalibrated collaborative driving views; targeted blind-spot recovery. Scored by **rendering quality/efficiency** on V2XReal + UrbanIng-V2X. No adversary |
| **Birdcast** (2604.00701) | **BEV multicasting** for V2I collaborative perception — a communication-efficiency framework using "maps of interest". Metrics = system utility + mAP. No adversary |

**Notable:** GCP — our closest temporal rival — has attracted **no follower that closes our gap**. The only
adversarial paper citing it is **MVIG** (already a must-cite).

### ⚠ CP-uniGuard precision point (from its body, 2506.22890)
Do **not** write "CP-uniGuard does not model sensor noise." Its observation model **explicitly includes
per-agent Gaussian noise**: `x_{i,t} = h_i(s_t) + η_{i,t}, η_{i,t} ~ N(0, σ_i² I)`. What it does **not** do is
use that noise model to **distinguish honest inter-agent disagreement from malicious perturbation** during
verification. Its *"online adaptive threshold via dual sliding windows"* is **per-frame threshold adaptation**
(the (1−α)-quantile of a benign window at each frame) — **not** a per-neighbour accumulated statistic.
Same trap-shape as the Allig correction.

### MADE sweep result — clean (2026-07-28)
12 citers, **all individually read, zero title-grade**. **No new must-cite, no new group-cite.** Half were
already read via other anchors (HyDRA, Adversarial-CP-in-AD, CP-uniGuard, GCP, CP-Guard, Survey-Intermediate-
Fusion). The 6 genuinely new ones are all **benign or out-of-domain**:

| Paper | Verified reason it is out |
|---|---|
| **V2X-INCOP** (2304.11821, T-IV'24) | Recovers information lost to **communication interruption** (packet drop) via multi-scale spatial-temporal prediction + knowledge distillation. **No adversary at all** — temporal is used for *recovery*, not detection. AP metrics |
| **NegoCollab** (NeurIPS'25, 2510.27647) | Negotiated common representation to close **domain gaps between heterogeneous agent models**. Benign |
| **mmCooper** (ICCV'25, 2501.12263) | Multi-stage intermediate/late fusion balance for **bandwidth + calibration error**. Benign |
| **Heterogeneous Swarms** (NeurIPS'25, 2502.04510) | **Multi-LLM system design** via particle-swarm optimisation of DAG roles/weights. Entirely out of domain |
| **Survey: Intermediate Fusion Methods** (2404.16139) | Survey of intermediate-fusion CP by real-world challenge; has an adversarial-defense subsection. *Optional* field-survey cite at most |
| **Collaborative Perception for CAD: Challenges** (2401.01544) | 🚨 **VERDICT CORRECTED after reading the body.** The abstract-only read said *"no adversarial content, does not name security as an open problem"* — **that was WRONG.** Full text: **§IV-A discusses detecting evasion attacks** where *"malicious vehicles can alter feature maps"*, describes malicious-vehicle detection via **consistency testing and match-loss statistics**, and **§IV-B names "Collaborative Perception with Security Consideration" as a future opportunity**, calling for a *"shift in focus towards enhancing trust among collaborating agents."* Still **no pre-emption** (benign channel-aware method, no navigation metric, no per-neighbour temporal), but it is now a **useful supporting cite** — a 2024 survey naming inter-agent trust as an open problem |
| **HyDRA** (2603.23975, KAIST) | ✅ **Re-read properly.** Heterogeneity from *"differences in model architecture or training data distributions"*; domain classifier routes heterogeneous agents to a late-fusion branch + anchor-guided pose-graph optimisation. **Benign — no adversary.** Conclusion: comparable to SOTA heterogeneity-aware CP *"despite requiring no additional training"* |
| **V2X Cooperative Perception for AD** (2310.03525) | ✅ **Re-read properly.** Survey of benign CP developments. **No adversarial/malicious/trust coverage**; future directions are privacy-preserving AI, collaborative intelligence, integrated sensing — security is **not** named as an open challenge |

> ⚠ **Process note (2026-07-28, Srinivasa's catch — TWO rounds):**
> **Round 1:** the first MADE pass glossed three papers — `2401.01544` and `2310.03525` were accepted on
> *topic-adjacent* search text rather than the papers' own abstracts, and **HyDRA** rested on a one-line gist
> from the citation API.
> **Round 2:** Srinivasa then asked whether *abstract **+ conclusion*** had really been read for all 12. It had
> not — only **6 of 12**. Chasing the missing conclusions **overturned a verdict**: `2401.01544`'s abstract
> shows no security content, but its **body has a whole adversarial-defense section and names inter-agent
> trust as a future opportunity**.
> **Lesson, now load-bearing: an abstract-only verdict is not reliable for "does this paper cover X?"** — an
> abstract can omit an entire section. Conclusions/bodies are required wherever the verdict is "it does NOT
> do X". Also note WebFetch truncates quoted text to ~125 chars, so "verbatim abstract" quotes in this file
> are fragments; the analysis under them derives from the full page the fetcher read.

### Conclusions retrieved on the second pass
- **CP-Guard** (2412.12000v1) — *"CP-Guard … consists of two parts, the first is PASAC which can effectively
  sample the collaborators without the prior probabilities of malicious agents. The second is collaborative
  consistency loss verification which calculates the discrepancy between the ego CAV and the collaborators…"*
  Body confirms: **verification is per-iteration/per-frame, no temporal accumulation**; metrics = **mIoU +
  verification count**; **honest sensor noise causing inter-agent disagreement is NOT modelled** — the threat
  model *"assumes adversarial perturbations only."* → our Level-1 differentiators vs CP-Guard hold.
- **Survey: Intermediate Fusion Methods** (2404.16139) — conclusion flags scalability/real-world gaps
  (simulations *"rarely capture the complexities of real-world scenarios"*, datasets use *"only a small number
  of collaborative agents"*). Its adversarial section lists only **AdvAttack / ROBOSAC / CAD / MADE** and is
  explicitly brief; it does **not** identify temporal-defense, noise-aware-threshold, or driving-outcome gaps.
  Useful evidence that the adversarial-CP literature was still thin as of 2024.

**Side finding:** MADE's citation record confirms **GCP's attack is "blind area confusion (BAC)" — a
defense-aware attack**. That is a third independent datapoint for claim-rewording #3 (adaptive attacker),
alongside MVIG and Stealthy-Fab.

### 🚨 CRITICAL FINDING FROM THE CP-GUARD SWEEP — **GCP IS CROSS-AGENT TEMPORAL WITH PER-NEIGHBOUR STATE**

The CP-Guard citation list pointed back at **GCP — one of our own dossiered competitors** — with the phrase
*"temporal anomalies by reconstructing historical bird's eye view motion flows."* Reading GCP's full text
(arXiv 2501.02450v2) to settle it produced the following, and it is **worse for us than the dossier implies**:

| Question | GCP's actual answer |
|---|---|
| Per-neighbour or scene-level? | **PER-NEIGHBOUR.** It reconstructs motion trajectories of *"specific neighbor agents across frames"*, matching *"detected low-confidence bounding boxes from a particular collaborator across historical frames"* |
| Frames of history | **K = 5** (optimal per their ablation, Fig. 6) |
| Per-(ego, neighbour) running state? | **YES** — caches historical detection frames per neighbour *i*, plus *"cached matching chains for each tracked flow"*; an **LSTM-autoencoder** learns the temporal pattern |
| Honest sensor/localization noise causing honest disagreement | ❌ **"Not explicitly modeled."** Thresholds come from **conformal p-values + Benjamini–Hochberg FDR**, not from a noise model |
| Metric | **AP@0.5** — no driving/navigation outcome |

**Consequence — a FOURTH claim must be dropped.** We can no longer say "first cross-agent temporal trust" in
any form. GCP already accumulates per-neighbour evidence over 5 frames. What survives is narrower and must be
stated exactly:

> **Our differentiators vs GCP:** (i) **navigation-success metric** — GCP scores AP@0.5 only; (ii) the
> **ranging-noise honest-disagreement regime** — GCP explicitly does not model it, and its conformal/BH
> thresholds are calibrated on clean data; (iii) **mechanism** — GCP learns an **LSTM-autoencoder
> reconstruction error over motion-flow sequences**, whereas ours is a **closed-form zero-mean test on a
> geometric offset vector**, which is what makes it survive √2σ honest disagreement; (iv) **Byzantine
> fraction** — we hold to 7/10 with no honest majority.

**Also settled — PRBI is SAFE on this axis.** Its "temporal perceptual discrepancy" uses **the ego's OWN
preceding frame** as a dynamic reference — **one** frame of history, per-frame operation (*"2.5 verifications
per frame"*), metric = detection precision. **No per-neighbour accumulation.** Good: our nearest 2026 rival
did *not* take the cross-agent temporal step.

**Other CP-Guard citers** (15 total, 6 already read elsewhere): **V2XCrafter** (2605.29471 — multi-agent
driving-**scene generation** via diffusion, benign) · **HyDRA** (heterogeneous fusion, benign) · **V2X-DSC** /
**InfoCom** (communication-efficiency, benign) · **Privacy-Aware Sharing / SHARP** (privacy leakage, not
adversarial security) · **RecoverMark** + **Decoder Gradient Shields** (image/face **watermarking** — out of
domain) · **Distribution-Aligned Decoding** + **Task-Aware PEFT** (LLM / fine-tuning — out of domain).
All read to abstract; **all NO CITE**.

### 📋 EVIDENCE GRADE — ZERO TITLE-GRADE (standing rule, enforced 2026-07-28)
**Srinivasa's standing rule: no paper receives a verdict on its title.** Every one of the 54 ADoPT + 3D-TC2
descendants was individually read to **abstract (and conclusion where reachable)**. Bulk screening was used
only to decide the reading order — never as a verdict.

**Final count: 41 read · 4 not locatable anywhere online · 0 title-grade.**

#### The 4 that could not be located (no abstract exists on the open web; the title appears only inside other papers' reference lists — these carry NO verdict)
`An Attack Detection Method Based on Spatiotemporal Correlation` (2022) · `A Novel Multi-layer Task-centric
Framework` (2025) · `Stealth in Sight: Model-Free Assessment` (2026) · `Secure3D-CV` (2026)

#### The 41 read — every one out-of-family, with the reason
**Defenses (all single-vehicle):**
| Paper | Verified reason it is out |
|---|---|
| **PhyScout** (CCS'24) | Checks *"spatio-temporal consistency of **their** environment"* via the ego's own image feature points |
| **DSADA** (ACM TAAS'25) | Cross-validates detector output against **its own** point-cloud spatial shapes. TPR 100%, FPR 3.97% |
| **Hyper3Def** (MobiSys'25) | Hypernet ensemble vs **adaptive** attackers — but single-vehicle detection; no agents, no trust |
| **Effects of Redundant LiDAR Sensors** (COMPSAC'25) | Redundancy = **multiple LiDARs on ONE car**, not multiple agents |
| **Detection of LiDAR & Camera Spoofing** (2025) | Cross-modal check **between sensors on one vehicle** |
| **Spoofing Detection: Physical-Layer** (IEEE'24) | Doppler frequency shift at the **signal layer** |
| **Insertion/Removal Attack Detection** (IEEE'25) | Physical coherence of one vehicle's point cloud |
| **Leveraging Intensity as a Feature** (ACSAC'24) | LiDAR **intensity** channel, single-vehicle |
| **STAnDS / anomaly recognition** (2022) | Spatial-temporal, but *"residual error spatial detector with time-based expected change"* on **one** vehicle |
| **ISD-SLAM** (inside D-SLAMSpoof, 2026) | Inertial dead-reckoning cross-check, single-vehicle localization |
| **Monitoring of Perception Systems** (2205.10906) | Runtime fault detection on one AV (Apollo/LGSVL) |
| **Cocoon** (2410.12592) | Uncertainty across **modalities on one car**; **no adversary** |
| **Task-Aware Risk Estimation** (2305.01870) | **Natural** perception failures, no adversary |
| **LiDAR point cloud transmission** (Comp&Sec'25) | Spoof ID + path selection, but **single-vehicle**; TPR/precision metrics |

**Attacks (all single-vehicle):** SLACK (SLAM point injection) · D-SLAMSpoof · EMTrig (electromagnetic +
roadside objects) · Rain-Reaper (rain-exploiting GA attack) · Leveraging-Adverse-Weather · FlowCraft (scene-flow
regression) · Adversarial-3D-Virtual-Patches (object hiding) · Explainability-Aware-Frustum-Attack (ECCV'26,
saliency-guided) · First-Physical-World-Trajectory-Prediction-Attack (63% collision rate, but attacks **one**
victim's prediction).

**Surveys / out-of-domain / non-security:** SoK-How-Sensor-Attacks-Disrupt-AVs · SoK-Semantic-AI-Security ·
SoK-Cybersecurity-of-Humanoid-Ecosystem (humanoid robots) · Adversarial-ML-20-Year-Survey (250+ papers, 5
domains) · Autonomous-Driving-Security-State-of-the-Art (IoT-J'22) · Automotive-Hacking · Survey-of-
Navigational-Perception-Sensors-Security (IEEE Access'25) · Adversarial-Attacks-on-ADS-Physical-World (TIV) ·
Overview-of-Sensing-Attacks · LiDAR-in-Connected-and-Autonomous-Vehicles · Cyberattacks-and-Defenses-for-
Autonomous-Navigation (125-article review) · Multi-Agent-Embodied-AD (380+ paper survey; **no** per-neighbour
temporal defense proposed) · A-Probabilistic-Approach-to-SNR (LiDAR physics/design, not security) ·
**Fundamental-Architectures-for-High-Integrity-Georeferenced-Lidar** = **Toward-High-Integrity-Roadway-
Applications** (same work, ION conference + NAVIGATION journal versions; **positioning integrity**, not
perception security).

| The 9 doubtful papers | Verified verdict |
|---|---|
| **PhyScout** (CCS'24) | ✅ **Single-vehicle** — checks *"spatio-temporal consistency of **their** environment"* via the ego's own image feature points |
| **Cocoon** (2410.12592) | ✅ Single-vehicle **multi-modal** fusion; disagreement is **between sensors on one car**, not between agents; **no adversary** |
| **Task-Aware Risk Estimation** (2305.01870) | ✅ Single-vehicle; **natural** perception failures, no adversary; does link failure→motion plan, but no agents |
| **Monitoring of Perception Systems** (2205.10906) | ✅ Single-vehicle runtime fault detection/identification (Apollo + LGSVL) |
| **First Physical-World Trajectory Prediction Attack** (2406.11707, USENIX'24) | ✅ Single-vehicle: physical stickers → victim's LiDAR → prediction error → **63% collision rate**. Attack, not collaborative. *(Optional cite only as extra precedent that driving-outcome metrics exist.)* |
| **Cyberattacks & Defenses for Autonomous Navigation Systems** (Computer Networks'25) | ✅ **Systematic literature review** of 125 articles — survey, not a method |
| **Multi-Agent Embodied Autonomous Driving** (2606.13840) | ✅ **Survey** of 380+ publications. **No per-neighbour temporal defense proposed.** Notes *"verifiable shared-state maintenance"* as an OPEN problem → mild support for us |
| **An Attack Detection Method Based on Spatiotemporal Correlation** (2022) | ❌ **NOT LOCATABLE** — no abstract found anywhere; title appears only in citation lists |
| **A Novel Multi-layer Task-centric Framework** (2025) | ❌ **NOT LOCATABLE** — same |

### ⭐⭐ HEADLINE RESULT — the temporal lineage is ENTIRELY SINGLE-VEHICLE (2026-07-28)

**54 citing papers across ADoPT + 3D-TC2. NOT ONE applies temporal consistency to a NEIGHBOUR's shared
claims.** Every descendant checks a **single vehicle's own past frames**. Explicit verdict from the 3D-TC2
citation sweep: *"No papers check multiple vehicles' shared claims across time. All defenses operate on
single-vehicle perception… none model trust relationships between neighboring agents verifying each other's
detections… No papers explicitly model how environmental noise or legitimate measurement variance causes
different agents to report conflicting observations over time."*

Verified against the closest-named descendant: **PhyScout** (CCS'24, *"Detecting Sensor Spoofing Attacks via
Spatio-temporal Consistency"*) — despite the near-identical name, it checks *"spatio-temporal consistency of
**their** environment"* using **the ego's own image feature points**; single-vehicle, no neighbour claims.

**What this buys us:** the **cross-agent** half of our temporal claim is now verified from BOTH directions —
backward (3D-TC2/ADoPT dossiers) and forward (54 descendants). The single-vehicle temporal lineage never
crossed into multi-agent. Combined with §Part 4 item 2 (CONClave/CATS/MVIG accumulate *scores*, not offsets),
the precise defensible claim is: **first to accumulate a cross-agent geometric OFFSET statistic under ranging
noise.** Both halves now have evidence.

## 1.2 Anchors REMAINING: **11**

| Priority | Anchor | ID / where | Why this priority |
|---|---|---|---|
| 🔴 **HIGH** | **GCP** (TDSC'25) | 2501.02450 | Core CP-security anchor — **and now our closest temporal rival**, so its citers matter most |
| 🟠 MED | **PRBI** (2026) | 2603.08498 | Newest defense; few citers expected but cheap |
| 🟠 MED | **MATE** (CCS'25) | 2503.04954 | Trust-estimation line |
| 🟠 MED | **AerialTrust** (ICCPS'25) | — | UAV trust — closest to our platform |
| 🟠 MED | **Stealthy-Fab** (2026) | 2605.01301 | Attack-side anchor |
| 🟠 MED | **TrustFlip** (2026) | 2605.22122 | Trust-poisoning line |
| 🟡 LOW | **CoDynTrust** | 2502.08169 | Benign paper → citers likely benign |
| 🟡 LOW | **Tu et al.** (ICCV'21) | 2101.06560 | Seminal but old; citers already caught via CAD/ROBOSAC |
| 🟡 LOW | **Vadivelu** (CoRL'20) | 2011.05289 | Benign precedent |
| 🟡 LOW | **SwarmRaft** | 2508.00622 | Consensus layer, out of family |
| 🟡 LOW | **Conformity** | 2606.21206 | Decision layer, out of family |

## 1.3 Other sweep tasks

| Task | Status |
|---|---|
| **Google Scholar "Cited by → Since 2025"** on 9 anchors (Scholar blocks the fetcher — **Srinivasa must run it**) | ❌ NOT STARTED — steps in Part 4 |
| Read the 2 PDFs Srinivasa is downloading (Fake-Objects-CPM, ST-GNN) | ⏳ awaiting files |
| Apply the 3 claim rewordings to `related.tex` / `discussion.tex` | ❌ NOT STARTED |

---

# PART 2 — THE 3-QUESTION TEST (how every paper below was categorised)

| | Question | Ours |
|---|---|---|
| **Q1** | Closed-loop control of a robot to a goal, scored by task success? | ✅ |
| **Q2** | Models sensor NOISE making **honest** agents disagree, and survives that false-positive regime? | ✅ |
| **Q3** | Accumulates a per-**neighbour** statistic across many frames? | ✅ |

A paper answering **no** to any one cannot pre-empt the compound claim.
**Category rule:** Level 1 = could be mistaken for us → needs its own differentiator paragraph.
Level 2 = same field, clearly different → one shared sentence. Level 3 = different problem → not cited.

---

# PART 3 — CITATION LEDGER (every paper, its category, and the reason)

## 3.1 🔴 MUST CITE — own differentiator paragraph (6)

| Paper | Yr | Depth | **Reason it is Level 1** | **Our stated difference** |
|---|---|---|---|---|
| **CP for Safe Control under LiDAR Spoofing** (2302.07341) | 2023 | full | ⭐ **Closest paper in the entire project.** Fabricated ("non-existing") obstacle + **ego-vs-neighbour LiDAR comparison** + **control that avoids the object**, in CARLA. Even carries noise bounds ζₙ, ζᵣ | Threat model is *"spoofing … can typically only be mounted on **one vehicle at a time**"* — we handle **up to 7 of 10**. Their noise handling is a **fixed geometric margin**, not a statistical honest-disagreement regime. **No temporal accumulation.** Hand-designed controller vs our learned MAPPO policy. Control reported **qualitatively**, no success rate |
| **SafeCoop** (2510.18123) | 2025 | full | Reports the **CARLA Driving Score under attack**, closed-loop, 32 scenarios → **breaks our metric-novelty claim** | Agents exchange **natural-language text**, not geometry. Attacks = loss / replay / **semantic** spoof / Sybil — *"none explicitly fabricate a physically non-existent obstacle."* Sensor noise: *"not modeled."* Detection is *"per-message, single-frame"* (τ=2.5) |
| **CONClave** (2409.02863, DAC) | 2024 | full | Detects **fabricated objects**, keeps **per-agent trust over time**, AND models honest sensor disagreement → hits **Q2 and Q3** | **No driving metric** — scored by *mean time to detection*. Needs **authentication + a consensus round** (infrastructure we don't assume). Trust = **std-dev-score buffers**, not a geometric offset mean. Its *"rule of three"* needs **three sensors agreeing** — redundancy we deliberately break |
| **CATS** (2503.00659, TVT) | 2025 | full | **"Phantom red-light violator"** = fabricated non-existent vehicle; **long-term per-vehicle reputation** | ⭐ **Requires an honest majority** (*"majority view"* across peer reports) — a **perfect foil** for our no-honest-majority result. Metric = message FP/FN, **no driving outcome**. Noise modelled *"minimally"* |
| **MVIG** (2602.19596, CVPR) | 2026 | full | Adaptive, **defense-aware** attacker using **temporal graph learning (k=5 frames + GRU)**; explicitly defeats threshold-based consensus → **breaks our adaptive-attacker claim** | It is the **attack**, we are the **defense**. **Feature-level** perturbation vs our object-level. Metrics ASR/DSR/ΔAP@50 — **no navigation**. No honest-noise regime |
| **RLCVP** (IEEE TMC 11006384) | 2025 | abstract ⚠ | Title reads exactly like ours: **RL + data-fabrication defense** | Its **RL selects which CAV to collaborate with** (inconsistency degree, confidence score, channel gain) — **not a driving policy**. Check is **spatial consistency + hypothesis-test threshold**, per-frame. ⚠ conclusion owed |

## 3.2 🟡 GROUP CITE — one shared sentence (19)

All fail **Q1 and Q3**; none is a novelty threat. Reason = why it is in the field but not a rival.

| Paper | Yr | Depth | Reason it is only Level 2 |
|---|---|---|---|
| **CP-uniGuard** (2506.22890) | 2025 | full | Journal extension of CP-Guard (PASAC + CCLoss + adaptive threshold). AP/mIoU; **per-frame consensus**; has Gaussian sensor noise in the model but **no honest-disagreement regime** |
| **TUQCP** (2502.02537) | 2025 | full | Adversarial training + uncertainty quantification vs PGD. AP/KLD/NLL. **Explicitly does NOT separate honest uncertainty from adversarial perturbation.** No temporal, no navigation |
| **RCDM / Plug-and-Play Reweighting** (2607.10037) | 2026 | full | Task = **binary braking decision** (metric ADR). Down-weights points deviating from the **local median**, per-frame. **Does not identify which agent is malicious.** Treats honest noise and attack identically |
| **FNO-Guard** (ScienceDirect) | 2026 | abstract ⚠ | Fourier-operator functional-inconsistency score on full feature maps, 62 FPS. Feature-level, per-frame |
| **MAST** (2401.09387) | 2024 | full | **Testbed, not a defense.** Implements coordinated/uncoordinated false-object injection, but authors state analysis *"stopped at the level of the command center"* — **no planning/control evaluation, no trust over time** |
| **CP-FREEZER** (2508.01062) | 2025 | full | **Latency/availability** attack (NMS blow-up, 90× slowdown) — **not fabrication**. **No defense proposed**; notes ROBOSAC *amplifies* the latency |
| **Fake-Objects-CPM Trust** (Springer) | 2025 | partial ⚠ | Fake-object attack + verification/tagging + trust calculation, but **message-layer CPM**. ⚠ **May move to Level 1 once the PDF is read** |
| **Trust-Mgmt-CPM** (ICARCV'22) | 2022 | abstract ⚠ | Trust framework over transmitted CPMs; classical CPM-MDS lineage, message layer |
| **Misbehavior Detection w/ Privacy** (2111.03461) | 2021 | full | CPM used to validate CAMs under pseudonyms. FP/TP rates. No per-neighbour temporal trust, no noise regime |
| **Robust-CP: Adv. Training + Consensus** (IEEE 11097632) | 2025 | abstract ⚠ | White-box untargeted attacks on feature-level fusion; model-agnostic adversarial training |
| **Adversarial CP in Autonomous Driving** (IEEE 11185995) | 2025 | abstract ⚠ | White-box vs black-box adversarial-example *study*, not a defense |
| **CIAK-CP** (ACM SAC'26) | 2026 | abstract ⚠ | Injects real vehicle **image snippets** into camera feeds — camera modality, **attack-only** |
| **ALADCP** | 2026 | title ⚠ | **Late-fusion = object level, like ours** — but anomaly detection, expected per-frame + detection-scored. ⚠ unverified |
| **Sieve** | 2026 | title ⚠ | Hierarchical adversarial **feature** detection (per title). ⚠ unverified |
| **BadMDA** | 2025 | abstract | Backdoor injected during **domain adaptation** — training-time supply chain, not runtime fabrication |
| **Yuce survey — MDS with CP in V2X** (Wiley ETT) | 2025 | abstract ⚠ | **Survey of exactly our sub-field.** Cite as the field pointer; reviewers from that community expect it |
| **PIMRC'25 — SOTA + first synthetic MDS-CP dataset** (Yüce et al.) | 2025 | abstract | Newest work in the space; applies **ST-GNN / EvolveGCN** to CPM misbehaviour on synthetic data. Message-layer, classification-scored |
| **Zero-Knowledge Proof of Traffic** (2312.07948) | 2023 | full | **Cryptographic** cross-verification — its own abstract says it works *"without relying on ground truth, probabilistic, or plausibility evaluations"*, i.e. the **opposite** of our statistical approach. Metric = cross-verification ratio 80–96%. **Optional** |
| ⭐ **Security in Collaborative Driving: A Survey** (Electronics'26) | 2026 | abstract | ⭐ **Cite in the INTRO, not just related work.** Its stated open challenges include **"uncertainty-aware defenses"** — a 2026 survey declaring our exact contribution an open problem |
| ⭐ **PhyScout** (CCS'24) | 2024 | abstract | ⭐ **Valuable contrast cite.** Nearest paper by NAME (*"Spatio-temporal Consistency"*) yet it is **single-vehicle** — checks *"spatio-temporal consistency of **their** environment"* via the ego's own image feature points. Use it to make the single-vehicle-vs-cross-agent boundary explicit and pre-empt "isn't this just PhyScout?" |

## 3.3 🟢 NO CITE (with the reason each was dropped)

| Paper | Reason dropped |
|---|---|
| **CPAD** (2501.17329) | Detects **driving-behaviour anomalies** (zigzag, tailgating) under comm loss. **No adversary at all.** F1/AUC |
| **Coop-WD** (2505.03528) | **Channel impairments** (Rician fading) only; **does not identify malicious agents**. AP only |
| **AdapAM** (2511.15292) | Generic black-box **multi-agent RL** attack; not collaborative perception, no object fabrication |
| **Physics-Aware Spatiotemporal Consistency** (Sensors'26) | **Single-vehicle**; threat = physical patches (RP2/CAPatch/SLAP); temporal consistency is over **the ego's own past frames**, not a neighbour's claims |
| **Confidence-V2X** (Adv. Eng. Informatics'26) | **Communication-efficiency** paper (sparse feature gating). **No adversary** |
| **HA-GAN** · **Point-Cloud-Tampering** | Watermarking / tampering studies outside the fabrication-defense family; no abstract retrievable |
| Benign CP systems: HyDRA · CABLE · V2X-DSC · NegoCollab · CoBEVMoE · STAMP · mmCooper · AFFormer · ER-CoPe · COOPERTRIM · A2MAML · DiffAlign · GT-Space | Benign fusion / communication / heterogeneity work — no adversary, no trust |
| Benign learned-CP driving: E2E-V2X-CP · CooperDrive · OmniV2X · Defer-to-Plan · CoopReflect · AutoAgent | The **Coopernaut lineage** — the paradigm is already credited via our Coopernaut cite; none is adversarial |
| Generic surveys: SoK sensor attacks · Taxonomy of System-Level Attacks · Cybersecurity Challenges of Autonomous Systems · Multi-Agent Embodied AD survey | Broad AV-security surveys, no CP-fabrication defense contribution |

## 3.4 ⏳ PENDING — category not yet assigned

| Paper | Why it is open | Action |
|---|---|---|
| **"Misbehavior detection with spatio-temporal graph neural networks"** (2024, ResearchGate 380252382) | **Spatio-temporal** → touches our **Q3**. Title-only so far. Expected: message-layer CPM classification (fails Q1/Q2), but unverified | Srinivasa downloading → `STGNN_MDS.pdf` |
| **Cooperative Trust Based Detection for Fake Objects in CPM** (Springer) | Fake objects + per-neighbour trust = **same shape as ours**. Abstract only | Srinivasa downloading → `FakeObjectsCPM_Trust.pdf` |

---

# PART 4 — ⚠️ FOUR CLAIMS WE MUST REWORD

| # | Claim we can no longer make | Evidence against it | Safe replacement |
|---|---|---|---|
| 1 | "First to evaluate a CP defense by **navigation/driving success**" | **SafeCoop** (CARLA Driving Score under attack, 2025); **LiDAR-Spoofing Safe Control** (control law that provably avoids the estimated obstacle, CARLA, 2023) | "First to do so **under ranging noise, with a learned multi-agent policy, at a Byzantine fraction up to 7/10**" |
| 2 | "First / only **cross-agent temporal** trust" | **CONClave** (per-participant std-dev buffers over consensus rounds); **CATS** (long-term per-vehicle reputation); **MVIG** (k=5-frame temporal graph) | Novelty is **WHAT** accumulates: a **geometric offset-vector mean**, zero-mean under honest noise, persistently biased for a camouflage liar. None of the three accumulates a spatial offset |
| 3 | "First **adaptive / defense-aware** attacker" | **MVIG** (CVPR'26); **Stealthy-Fab** (already dossiered); **Hyper3Def** (MobiSys'25, single-vehicle but explicitly adaptive-attacker-aware) | "Consistent with recent adaptive attacks [MVIG, Stealthy-Fab], we also stress-test our filter with a filter-aware adversary" |
| 4 🚨 | **ANY** form of "first cross-agent temporal" — including "first per-neighbour temporal accumulation" | 🚨 **GCP** (2501.02450v2, a paper we already cite): per-neighbour motion-flow reconstruction, **K=5** cached frames per collaborator, matching chains, LSTM-autoencoder. This is squarely cross-agent temporal with per-neighbour state. ⚠️ **EVIDENCE IS SUMMARISER-GRADE — NOT YET RAW-TEXT VERIFIED.** Obtained via WebFetch over GCP's HTML, i.e. the same footing on which the CATS differentiator proved **wrong** the same day. **Do not apply this rewording until `POST_SWEEP_TODO.md` §1b item 4 is done.** If GCP's mechanism is scene-level rather than per-neighbour, this rewording is wrong and the temporal claim partially survives | **Delete the temporal-priority claim entirely.** Differentiate on: (i) navigation-success metric (GCP = AP@0.5); (ii) ranging-noise honest-disagreement regime (GCP *"does not explicitly model"* it; thresholds = conformal p-values + Benjamini–Hochberg on clean data); (iii) **closed-form zero-mean offset test vs learned LSTM-AE reconstruction error**; (iv) Byzantine fraction 7/10, no honest majority |

**Note on #4:** GCP is a **dossiered competitor we already cite** — this was not a new paper, it was a
mis-characterisation in our own understanding of it, surfaced only because CP-Guard's citation list quoted
GCP's temporal phrasing. `REFERENCE_EVIDENCE_GCP.md` must be checked to confirm it records the per-neighbour
caching and K=5; if it does not, the dossier understates the rival.

**Compound novelty still SURVIVES:** no paper found does fabricated-obstacle attack **+** learned navigation success
**+** ranging-noise honest-disagreement **+** cross-agent temporal **offset** together.

---

# PART 5 — DEPTH LEDGER (per Srinivasa's mandate: abstract **and** conclusion for every paper)

| Depth achieved | Count | Which |
|---|---|---|
| **Abstract + conclusion / body from full text** | **19** | SafeCoop · MVIG · RCDM · CP-uniGuard · CONClave · CATS · MAST · CP-FREEZER · TUQCP · CPAD · Coop-WD · AdapAM · LiDAR-Spoofing-Safe-Control · Misbehavior-Privacy · Physics-Aware · Confidence-V2X · ZKP-Traffic · Security-in-Collab-Driving · PIMRC-dataset |
| **Abstract only — conclusion paywalled** | **6** | RLCVP (IEEE) · FNO-Guard (ScienceDirect) · Robust-CP (IEEE) · Adversarial-CP-in-AD (IEEE) · Trust-Mgmt-CPM (IEEE/HAL) · Fake-Objects-CPM (Springer) · *(+ Yuce survey, Wiley)* |
| **Title + venue only — no text online anywhere** | **4** | Sieve · ALADCP · HA-GAN · Point-Cloud-Tampering |

**The four walls** (why the last two rows exist):
1. **Paywall** — IEEE / Springer / Elsevier / Wiley subscription. → opens on campus wifi.
2. **Bot block** — IEEE returned HTTP 418, MDPI 403, HAL runs Anubis, Semantic Scholar rate-limits (429). Even on campus **Claude** cannot fetch these; **Srinivasa must download them**.
3. **Not indexed** — Sieve, ALADCP, HA-GAN, Point-Cloud-Tampering exist only as lines in other papers' reference lists; no abstract published anywhere.
4. **Claude gave up too early** — happened on 3 papers (Security-in-Collab-Driving survey, Zhang thesis→IV'24 paper, CIAK-CP); all recovered on a retry. Logged so the pattern is not repeated.

All blocked items are mirrored in **`INSTITUTE_WIFI_TODO.md` §PRIORITY 1b**.

---

# PART 6 — THE MISSING 10% (Srinivasa's Google Scholar pass)

Scholar blocks automated access but indexes preprints, theses and workshop papers that Semantic Scholar misses.

1. scholar.google.com → search the anchor title
2. click **"Cited by NNN"**
3. left sidebar → **"Since 2025"**
4. skim titles; copy anything mentioning attack / defense / trust / fabrication / collaborative perception
5. paste the list here for triage

Run for: **CAD · ROBOSAC · MADE · MATE · PRBI · TruPercept · CP-Guard · Coopernaut · ADoPT**

---

# PART 7 — RUNNING TOTALS

| Metric | Value |
|---|---|
| Anchors swept | **7 / 19 (37%)** |
| Citing papers examined | **~220** |
| New papers surfaced | **~50** |
| Must cite (Level 1) | **6** |
| Group cite (Level 2) | **20** |
| No cite (Level 3) | **~75** |
| Pending category | **2** (Srinivasa downloading) |
| **Unknown — not locatable, NO verdict given** | **4** |
| **Title-grade verdicts** | **0** ✅ (standing rule) |
| Claims requiring rewording | **4** (🚨 #4 = GCP, the most serious) |
| Pre-emptions of the compound claim | **0** |

**Standing rule in force:** zero title-grade. Every verdict rests on at least an abstract; unreachable papers
are logged as **unknown**, never as "safe". Saved to memory as `paper-reading-depth-standard`.

## 7.1 Also dropped from the ADoPT / 3D-TC2 sweeps (single-vehicle LiDAR spoofing family — NO CITE)
D-SLAMSpoof · SLACK · Rain-Reaper · FlowCraft · EMTrig · DSADA · Cocoon · Leveraging-Adverse-Weather ·
Leveraging-Intensity · Adversarial-3D-Virtual-Patches · Secure3D-CV · Dynamic-Defense-Car-Borne-LiDAR ·
Insertion-and-Removal-Attacks · Explainability-Aware-Frustum-Attack · Stealth-in-Sight · Temporal-Misalignment-
Attacks · Monitoring-of-Perception-Systems · Task-Aware-Risk-Estimation · plus ~15 AV-security surveys.
**Reason for all:** single-vehicle sensor spoofing — no collaborative perception, no inter-agent trust, no
neighbour claims. *(One borderline: "A First Physical-World Trajectory Prediction Attack" (2024) reports a
**63% collision rate** — a driving-outcome metric — but it attacks single-vehicle trajectory prediction, not
collaborative perception. Optional cite only if we want more precedent that driving-outcome metrics exist.)*
