# FORWARD-CITATION SWEEP — TRACKER + CITATION LEDGER
_Started 2026-07-28. Single source of truth for "who cited our anchors AFTER publication."_

**Why this exists.** Every earlier sweep was **backward** (we read our competitors' bibliographies). A
bibliography can only contain papers **older** than the citing paper — so ~300 backward abstracts could not, even
in principle, surface a 2025–26 paper that beats us. This sweep goes **forward**: who *cites* our anchors.

**Headline.** Backward sweep found **0** new competitors. This forward sweep has already found **~35 new papers**,
**6 must-cites**, and **3 overstated claims**. It is **only 21% complete**.

⏳ **Nothing here is closed until Srinivasa audits it** (standing rule). None of it is in `related.tex` yet.

---

# PART 1 — PROGRESS TRACKER

## 1.1 Anchors swept: **4 of 19 (21%)**

| # | Anchor | arXiv ID | Citations pulled | Status |
|---|---|---|---|---|
| 1 | **CAD** (USENIX Sec'24) | 2309.12955 | 31 | ✅ DONE |
| 2 | **ROBOSAC** (ICCV'23) | 2303.09495 | 45 | ✅ DONE |
| 3 | **TruPercept** (IEEE IV'20) | 1909.07867 | 32 | ✅ DONE |
| 4 | **Coopernaut** (CVPR'22) | 2205.02222 | 43 | ✅ DONE |
| 5 | **ADoPT** (BMVC'23) | 2310.14504 | 21 | ✅ DONE 2026-07-28 |
| 6 | **3D-TC2** (MAISP'21) | S2 `114a30a0…` | 33 | ✅ DONE 2026-07-28 |
| 7 | **CP-Guard** (AAAI'25) | 2412.12000 | 15 | ✅ DONE 2026-07-28 |

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

## 1.2 Anchors REMAINING: **12**

| Priority | Anchor | ID / where | Why this priority |
|---|---|---|---|
| 🔴 **HIGH** | **MADE** (IROS'24) | 2310.11901 | Core CP-security anchor |
| 🟠 MED | **GCP** (TDSC'25) | 2501.02450 | Core CP-security anchor |
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
| 4 🚨 | **ANY** form of "first cross-agent temporal" — including "first per-neighbour temporal accumulation" | 🚨 **GCP** (2501.02450v2, a paper we already cite): per-neighbour motion-flow reconstruction, **K=5** cached frames per collaborator, matching chains, LSTM-autoencoder. This is squarely cross-agent temporal with per-neighbour state | **Delete the temporal-priority claim entirely.** Differentiate on: (i) navigation-success metric (GCP = AP@0.5); (ii) ranging-noise honest-disagreement regime (GCP *"does not explicitly model"* it; thresholds = conformal p-values + Benjamini–Hochberg on clean data); (iii) **closed-form zero-mean offset test vs learned LSTM-AE reconstruction error**; (iv) Byzantine fraction 7/10, no honest majority |

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
