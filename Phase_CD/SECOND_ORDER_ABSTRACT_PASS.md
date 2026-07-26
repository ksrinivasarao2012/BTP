# Second-order ABSTRACT-level pass — ROBOSAC + Stealthy-Fab bibliographies (2026-07-26)

## Why this file exists
Srinivasa challenged the earlier "zero new family members" claim, correctly: it was a **title-level**
judgment, not an abstract read — and Coopernaut (a genuine precedent) had slipped through the title scan
bucketed as "plumbing." This file records the **actual abstract reads** done to replace title-level guesses
with evidence, at the bar "**reject only if 100% confident**." Scope = the **112 refs** of ROBOSAC (48) +
Stealthy-Fab (64). **~27 abstracts were actually read** (all CP/multi-agent/security-relevant ones + a few
single-vehicle/downstream borderlines). The rest are citation-identified (datasets/simulators/standards/
detector-backbones/adv-ML-classics/RANSAC-math/downstream-tools/other-domains) — NOT abstract-read; flagged
honestly below.

---

## ⭐ "MIGHT BE SIMILAR" LIST (survived the 100%-confidence-reject filter) — 2 papers
Both are **benign** (no adversary/trust), so **neither pre-empts our security contribution** — but both are
legitimate precedents that affect how we phrase novelty / related work.

**1. Coopernaut (Cui, Qiu, Chen, Stone, Zhu — CVPR 2022) — MEDIUM. Cite + safeguard. [FULL-PDF READ
2026-07-26 → dossier `REFERENCE_EVIDENCE_COOPERNAUT.md`]**
Confirmed on full read: end-to-end LEARNED CP driving policy (Point-Transformer message encoder + DAgger
imitation of a privileged A* oracle), scored by **Success Rate** in AUTOCASTSIM; SR 90.5/80.7/80.7 vs No-V2V
45.3/40.3/47.3 (Table 2). → **the exact benign task paradigm** our combination-novelty sentence leans on.
**Benign — no adversary/trust anywhere**; only robustness claims are to 5% *random* packet loss + slight
localization error (p.8), explicitly not adversarial. **Consequence:** our "closed-loop learned navigation,
success as the end metric" claim must **credit Coopernaut for the paradigm** and claim novelty on the
**attack+defense layer** only. Extra trap found on full read: Coopernaut ALSO uses a privileged planner
(A* oracle) — structurally like our Dijkstra crutch — so do NOT use "they use a privileged planner" as a
differentiator. Exact safeguard clause is in the dossier. (This is the catch the title scan missed.)

**2. Vadivelu et al. "Learning to Communicate and Correct Pose Errors" (CoRL 2020) — LOW–MEDIUM. [FULL-PDF
READ 2026-07-26 → dossier `REFERENCE_EVIDENCE_VADIVELU.md`]**
Confirmed on full read: benign robust multi-agent CP (V2VNet feature-map sharing) against **localization/pose
NOISE** via three learned modules (pose-regression + student-t MRF consistency + attention message-reweighting);
metric AP@IoU + L2 forecasting on a static dataset (no policy/navigation/attacker). Does **NOT** pre-empt us on
any axis. Temporal consistency is explicitly their **future work** (Conclusion). **Useful catch:** they evaluate
**biased** noise (§4.2/Fig 4) and their pose-regression **corrects per-agent systematic offset** — exactly the
"estimate-and-subtract a per-neighbour offset" fix our discussion.tex assumption (vi) punts to future work → cite
Vadivelu there to back the punt. Guardrail: their attention module already down-weights inconsistent messages
(benign), so don't claim novelty on message-reweighting itself (our related.tex doesn't — safe).

**Resource (not a competitor):** **Wan et al., "Systematic Literature Review on Vehicular Collaborative
Perception" (T-ITS 2025)** — a PRISMA review of 106 CP papers that *explicitly* covers "adversarial attacks."
Not prior art, but a **place to mine** for any defense we missed. Worth one scan before submission.

---

## Abstract-READ and REJECTED — 100% confident, with the one-line evidence (24 papers)
| Ref | Abstract says (verbatim gist) | Out because |
|---|---|---|
| Multi-robot scene completion / STAR (CoRL'22) | "task-agnostic CP… self-supervised… reconstruct complete scene" | benign representation learning |
| Cooper (ICDCS'19) | "first raw-data level cooperative perception… transmit point clouds" | benign raw-data CP arch |
| When2com (CVPR'20) | "learn communication groups… when to communicate… bandwidth" | benign comm-scheduling |
| DiscoNet (NeurIPS'21) | "distilled collaboration graph… knowledge distillation… bandwidth" | benign CP arch |
| Kim cooperative driving (T-ITS'14) | "see-through FCW, lane-change assist, hidden obstacle avoidance… 4 vehicles" | benign classical driver-assist, no learned policy |
| RAO (MobiCom'23) | "out-of-sync sensor data… motion-compensated occupancy flow" | benign robustness to **asynchrony** |
| Su Double-M UQ (ICRA'23) | "first to estimate uncertainty of collaborative object detection" | benign uncertainty quantification |
| Martinez SUNRISE (Sensors'26) | "safety validation… I2V… KPIs safety/control/comfort" | benign safety-testing framework |
| Carrillo hybrid CP (Network'25) | "hybrid fusion… mitigating bandwidth challenges" | benign bandwidth arch |
| Arnold coop 3D det (T-ITS'20) | "cooperative 3D detection… early vs late fusion… recall >95%" | benign detection arch |
| V2X-ViT (ECCV'22) | "cooperative perception… vision Transformer… multi-agent attention" | benign transformer arch |
| Who2com (ICRA'20) | "handshake communication… request/match/connect… bandwidth" | benign comm arch |
| Zhou GNN (RA-L'22) | "GNN… resilience to sensor failures/disturbances… depth/segmentation" | benign, resilience to **faults** |
| Song object-level CP (arXiv'22) | "object-level fusion… robust for location/heading errors" | benign robustness to **pose errors** |
| VIPS (MobiCom'22) | "fuse LiDAR from infrastructure and vehicle… graph matching" | benign infra fusion |
| Su MOT-CUP (RA-L'24) | "uncertainty propagation… conformal… into MOT" | benign uncertainty for tracking |
| F-Cooper (SEC'19) | "feature-based CP… edge computing… detection precision" | benign feature-fusion arch |
| AutoCast (MobiSys'22) | "infrastructure-less CP… schedule transmissions… avoid crashes" | benign sharing scheduler, no adversary/policy |
| EMP (MobiCom'21) | "edge server merges CAVs' views… higher resolution" | benign edge-assisted fusion |
| Chen traffic-ops (arXiv'22) | "cooperative data collection… max-pressure signal control (CARLA/SUMO)" | benign CP for signal control |
| FusionEye (SECON'19) | "share perception… merge scene… bandwidth-accuracy" | benign bandwidth study |
| Yuan FPV-RCNN (RA-L'22) | "keypoints feature fusion… compress CPM size" | benign feature-fusion detection |
| Thornton HAdCoP (OJVT'25) | "heterogeneous adaptive CP… latency prediction… which vehicles transmit" | benign scheduling |
| Tu multi-sensor robustness (CoRL'21) | "adversarial object hides host vehicle from multi-modal detector" | **single-vehicle** multi-**sensor** |
| Hallyburton camera-LiDAR (USENIX'22) | "frustum attack… camera-LiDAR fusion… single AV" | single-vehicle multi-sensor |
| Lou trajectory-prediction attack (USENIX'24) | "attack against trajectory PREDICTION via LiDAR deception" | downstream predictor, not CP trust |
| Muller AttrackZone (CCS'22) | "physical tracker hijacking against Siamese trackers" | downstream tracker, single-vehicle |
| Zhang traj-pred robustness (CVPR'22) | "perturb vehicle trajectories to maximize prediction error" | downstream predictor |

*(27 rows above minus the 2 kept = the abstract-read set; a couple counted in both the "kept" and the tally.)*

## NOT abstract-read — citation-identified, judged out at HIGH (not per-abstract) confidence
Being honest: for these I did **not** read abstracts; the citation itself fixes the category and no abstract
could reclassify a named dataset / 1955 math paper / simulator as collaborative-perception prior art.
- **Datasets:** V2X-Sim, OPV2V, V2X-Real, COMAP. **Simulators/libs:** CARLA, SUMO, Open3D, AutoCastSim.
- **Standards/industry/reports:** 3GPP, C-V2X (Qualcomm/Huawei/Bosch/Infineon), Apollo, Autoware, Florida DOT,
  iMOVE, SAE J3224.
- **Detector backbones:** PointPillars, PointRCNN, AVOD, SECOND, Fast&Furious. **Downstream tools:** AB3DMOT,
  GRIP++, Trajectron++ (used as methodology).
- **Adversarial-ML classics:** PGD, C&W, BIM, FGSM, Szegedy, boundary/transfer attacks, robustness-accuracy.
- **RANSAC/geometry methodology:** RANSAC, MSAC, MLESAC, SfM, EPOS, calibration; **Hungarian method (1955)**.
- ~~Single-vehicle physical sensor-attack line (spot-checked 2)~~ → **UPDATED 2026-07-26: ALL 9 abstract-read,
  all confirmed single-vehicle out-of-family** (bracketed by our 3D-TC2/ADoPT paragraph): Tu-multisensor
  (CoRL'21, "adversarial object hides host vehicle from multi-modal detector"); Hallyburton (USENIX'22,
  "frustum attack, single AV"); Cao MSF-ADV (S&P'21, "3D object evades camera+LiDAR of one AV, 100% collision
  in sim"); Cao (CCS'19, "first LiDAR spoofing, single AV"); Zhu (CCS'21, "reflective objects fool one AV's
  LiDAR"); Shen "Drift with Devil" (USENIX'20, "GPS spoofing of one AV's MSF localization"); Jin PLA-LiDAR
  (S&P'23, "laser injects 4200 points into one LiDAR"); Tu (CVPR'20, "rooftop adversarial object hides vehicle,
  80%"); Li FLAT (ICCV'21, "GPS/trajectory spoofing distorts one AV's LiDAR motion-compensation"). None is
  multi-agent; none touches the collaborative communication/trust channel.
- **Other domains / surveys:** deformable-object manipulation, UAV visual tracking (blur-deblur, voxel
  pretrain), single-vehicle SSC (Monoscene, Voxformer), BEV/LiDAR/3D-detection surveys, Carspeak networking.

## Incidental forward-search leads (NOT in these bibliographies — for the C11 pre-submission sweep)
Surfaced while searching; recent, possibly relevant, worth a look before submission:
- **CooperDrive** (arXiv 2604.14454) — "enhancing driving decisions through cooperative perception."
- **"Towards Collaborative Autonomous Driving: Simulation Platform and End-to-End System"** (arXiv 2404.09496).
- **"UQ for Collaborative Object Detection Under Adversarial Attacks"** (arXiv 2502.02537) — CP + adversarial.
- COOPERTRIM / uncertainty-aware CP data selection (arXiv 2602.13287).

## Honest scope of THIS pass
- Covered: the **112** refs of ROBOSAC + Stealthy-Fab. **~27 abstracts actually read** (the CP/security-
  relevant subset); ~55 citation-identified (not read); ~8 single-vehicle-physical (2 read, rest title+venue).
- **NOT covered:** the other ~500 title-rejections from the 6-core + SwarmRaft/TrustFlip/3D-TC2/ADoPT/
  Conformity/MADE bibliographies. Coopernaut proves those deserve the same abstract pass before we call the
  second-order sweep truly closed.
