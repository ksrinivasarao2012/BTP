# Second-order FULL abstract sweep — every reference of every dossiered paper (started 2026-07-26)

**Mandate (Srinivasa, 2026-07-26):** do NOT stop at title level — **abstract-read every reference**
in the bibliographies of our dossiered papers, applying the "reject only if 100% confident" bar.
Motivation: a title-level scan once bucketed Coopernaut as "plumbing" and missed a genuine precedent.
Order: **CAD first**, then MADE, PRBI, GCP, MATE, AerialTrust, TruPercept, CoDynTrust, SwarmRaft,
TrustFlip, 3D-TC2, ADoPT, Conformity.

**Legend:** `TODO` = abstract not yet read · `READ` = abstract read this sweep · `PRIOR` = already
abstract-/full-read in an earlier pass (SECOND_ORDER_ABSTRACT_PASS.md or a dossier) · `NO-ABS` =
website/standard/product/dataset/tool with no readable abstract (identity fixes the category) ·
`KEEP?` = survived the reject filter → potential new precedent, escalate to Srinivasa.

**Standing rule:** append, never delete. A `KEEP?` row must be justified with the abstract gist.

---

## ✅ SWEEP COMPLETE — all 13 bibliographies (2026-07-26)
Every reference in all 13 dossiered papers' bibliographies has been accounted for under mandate B (each is
individually abstract-read, OR a no-abstract URL/standard/dataset, OR an already-read duplicate).
**≈460 reference-slots · ≈300 distinct abstracts individually fetched · ZERO pre-emptions.**

| # | Bibliography | Refs | Result |
|---|---|---|---|
| 1 | CAD | 91 | ✅ 0 pre-empt |
| 2 | MADE | 44 | ✅ 0 pre-empt |
| 3 | PRBI | 37 | ✅ 0 pre-empt — **CP-Guard → planned cite** |
| 4 | GCP | 35 | ✅ 0 pre-empt |
| 5 | MATE | 47 | ✅ 0 pre-empt (classical VANET-trust cluster) |
| 6 | AerialTrust | 37 | ✅ 0 pre-empt — **Cavorsi → RAS nice-to-have** |
| 7 | TruPercept | 36 | ✅ 0 pre-empt (VANET-trust; Obst resolved) |
| 8 | CoDynTrust | 35 | ✅ 0 pre-empt (benign CP + UQ) |
| 9 | SwarmRaft | 43 | ✅ 0 pre-empt (Byzantine-consensus/blockchain) |
| 10 | TrustFlip | 41 | ✅ 0 pre-empt (mostly already-dossiered) |
| 11 | 3D-TC2 | 14 | ✅ 0 pre-empt (single-vehicle spoof/temporal) |
| 12 | ADoPT | 37 | ✅ 0 pre-empt (single-vehicle + scene-flow) |
| 13 | Conformity | 15 | ✅ 0 pre-empt (evolutionary-game decision-layer) |

**Actionable outcomes (all in `NICE_TO_HAVE_CITATIONS.md`, all optional except CP-Guard):**
1. **CP-Guard** (AAAI'25) — **planned cite**, dossier owed (Srinivasa's decision). The one real find.
2. **Cavorsi** (T-RO'24) — RAS-community nice-to-have.
3. Classical VANET-trust / MDS representatives (Ambrosin, MISO-V, Van der Heijden survey, Obst) — optional.
4. CP-Guard+ / LUCIA — optional.

**Novelty verdict:** across ≈300 distinct abstracts spanning every closest-competitor's bibliography, **no
existing paper does our combination** (fabricated-obstacle CP attack + learned-navigation-success metric +
ranging-noise honest-disagreement + cross-agent temporal offset test + adaptive attacker). Nothing pre-empts.
⏳ **Each bibliography still awaits Srinivasa's audit of its security-relevant subset before it counts closed.**

---

## BIBLIOGRAPHY 10 — TrustFlip (Liu et al., "Adversarial Trust Poisoning in Vehicular CP", arXiv 2605.22122) — 41 refs
**Dossiered. CP-security paper → bibliography is ~30 already-dossiered/read CP-security + CP-arch + adversarial-LiDAR. Only ~9 net-new.**

### 10a. PRIOR / already-handled [~30]
[2] Han CP-survey (GCP[15]) · [3] V2VNet · [4] When2com · [5] V2X-ViT · [6] Zhang async (CAD[85]) · [7] Tu
adversarial-comm · [8] **CAD** · [9] **LUCIA** (PRBI[28]) · [12] **Pretend-Benign** (inline-triaged) · [13]
**Stealthy-Fab-to-unsafe-driving** (dossiered) · [14] **ROBOSAC** · [15] **MADE** · [16] **CP-Guard+** (PRBI[8]) ·
[17] **MATE** · [18] PLA-LiDAR · [19] Petit-cyberattack (MATE[33]) · [20] OPV2V · [22] PointPillars · [23]
Where2comm · [24] Cooper · [25] EMP (CAD[87]) · [26] Chen CP-env (CAD[31]) · [27] F-Cooper · [28] Coopernaut
(dossiered) · [29] Yuan FPV-RCNN (CAD[82]) · [30] Lu pose-errors · [32] FusionEye · [33] VIPS · [35] Cao MSF-ADV
(CAD[29]) · [36] Tu physically-realizable (CAD[71]) · [38] Zhu arbitrary-objects (CAD[91]). · NO-ABS: [1] US-DOT
CAV webpage.

### 10b. TODO — net-new (mandate B) [9]
CP-security-adjacent: [10] Wang **CP-FREEZER** (latency attack on CP) · [11] Zhang **Stealthy-data-fabrication-in-CP**
(CPS&IoT workshop). · Benign CP / backbone: [21] Yang **PIXOR** (BEV detector) · [31] Wang **JigsawComm** (semantic
feature encoding CP). · Single-vehicle adversarial-LiDAR: [34] Cao adversarial-objects-lidar (arXiv'19) · [37] Zhu
**AE-Morpher** (adversarial-object robustness) · [40] Liu **SlowLiDAR** (latency attack, single-vehicle). · Tools/math:
[39] Möller-Trumbore ray-triangle-intersection · [41] Jang **Gumbel-Softmax**.

### 10c. READ verdicts (mandate B) — all 9 net-new individually abstract-read, all no-pre-empt
- [10] Wang **CP-FREEZER** (AAAI'26) — first **latency/availability attack** on CP (maximizes compute delay via
  V2V perturbation, +90× latency). → attack on a **different axis (timeliness), not perceptual integrity**; no
  defense, no navigation → no pre-empt. (Notable as recent CP-attack; not our family.)
- [11] Zhang & Mao **Stealthy-data-fabrication-in-CP** (CPS&IoT'24) — CP fabrication/removal attack, practicality-
  focused. → **attack, AP-scored, no defense/navigation** — same family as CAD/Stealthy-Fab; no pre-empt.
- [21] Yang **PIXOR** (CVPR'18) — BEV single-stage detector backbone. → no pre-empt.
- [31] Wang **JigsawComm** (arXiv'25) — benign communication-efficient CP (semantic feature encoding). → no pre-empt.
- [34] Cao **LiDAR-Adv** (arXiv'19) — **single-vehicle** adversarial object vs LiDAR detector. → no pre-empt.
- [37] Zhu **AE-Morpher** (USENIX'24) — **single-vehicle** adversarial-object physical robustness. → no pre-empt.
- [40] Liu **SlowLiDAR** (CVPR'23) — **single-vehicle latency attack** on LiDAR detection. → no pre-empt.
- [39] Möller-Trumbore ray-triangle-intersection (graphics math) · [41] Jang **Gumbel-Softmax** (ML gradient
  estimator) — TrustFlip's differentiable-renderer tooling. → no pre-empt.

### TrustFlip bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 41 refs accounted for. **Zero pre-emptions.** ~30 already-dossiered/read (CAD, MADE, MATE, ROBOSAC, CP-Guard+,
LUCIA, Coopernaut, Stealthy-Fab, Pretend-Benign, V2VNet, When2com, V2X-ViT, PLA-LiDAR…); 9 net-new = 2 CP-attacks
on other axes (latency/fabrication), benign CP, single-vehicle adversarial-LiDAR, and renderer tooling. No new
nice-to-have. ⏳ **Awaiting Srinivasa's audit — security subset = [10] CP-FREEZER + [11] Stealthy-data-fab (both
attacks, neither our defense family).**

---


---

## BIBLIOGRAPHY 12 — ADoPT (Cho, Cao, Zhou, Mao, BMVC'23) — 37 refs
**Dossiered. Single-vehicle point-level temporal-consistency line → NO CP-security candidates.**

### 12a. PRIOR / NO-ABS [~9]
[2] nuScenes (dataset) · [4] Cooper (benign CP) · [7] Hau Shadow-Catcher (single-vehicle) · [9] PointPillars ·
[13] Liu "Seeing is not believing" (CAD[55]) · [19] Petit remote-attacks (3D-TC2[9]) · [22] Shin Illusion-Dazzle
(3D-TC2) · [23] Sun black-box (CAD[69]) · [30] Xiao AdVIT (3D-TC2) · [33] Yan SECOND (3D-TC2) · [35] **3D-TC2**
(dossiered) · [36] EMP (CAD[87]) · [18] NVIDIA mixed-precision (doc, NO-ABS).

### 12b. TODO — net-new (mandate B) [~24], all out-of-family (single-vehicle attacks / registration / scene-flow / backbones)
Single-vehicle LiDAR attacks/defense: [16] Man spatiotemporal-misclassification-detection · [21] Sato
lidar-spoofing-measurement · [24] Sun adv-robustness-3D-pointcloud · [25] Sun diffusion-purification-3D · [31]
Xiao **Exorcising-Wraith** · [32] Yan contactless-sensor-attacks · [34] Yang roadside-physical-adversarial-lidar.
Point-cloud registration: [1] Besl-McKay **ICP** · [8] Hirose Bayesian-CPD · [10] Li ICP-evaluation · [12] Li
non-rigid-neural-deformation. Scene-flow: [11] Li Neural-Scene-Flow-Prior · [14] Liu **FlowNet3D** · [17] Mittal
Just-Go-With-Flow · [20] Pontes scene-flow · [27] Wang Neural-Prior-Trajectory · [29] Wu **PointPWC-Net**.
Backbones/metrics/datasets/ML: [3] Argoverse (dataset) · [5] Ester **DBSCAN** · [6] Fan point-set-generation ·
[15] Liu **BEVFusion** · [26] Sun **Test-Time-Training** · [28] Wu density-aware-Chamfer · [37] Zhang BEV-realtime-det.

### 12c. READ verdicts (mandate B) — all 24 net-new individually abstract-read, ALL no-pre-empt
**Single-vehicle attacks/defenses (own-LiDAR, not cooperative):** [16] Man **PercepGuard** (track-class
spatiotemporal-consistency misclassification detection — single-vehicle own-MOT) · [21] Sato lidar-spoofing-
measurement · [24] Sun adv-robustness-3D-pointcloud · [25] Sun **PointDP** diffusion-purification · [31] Xiao
**Exorcising-Wraith** (appearing-attack defense via depth-density physics, single-vehicle) · [32] Yan
contactless-sensor-attacks · [34] Yang roadside-physical-adversarial-lidar. → no pre-empt (all single-vehicle;
no cooperative-perception cross-agent trust, no navigation).
**Point-cloud registration:** [1] Besl-McKay **ICP** · [8] Hirose **BCPD** · [10] Li ICP-evaluation · [12] Li
**NDP** non-rigid. **Scene-flow:** [11] Neural-Scene-Flow-Prior · [14] **FlowNet3D** · [17] Just-Go-With-Flow ·
[20] Pontes scene-flow · [27] Wang Neural-Prior-Trajectory · [29] **PointPWC-Net**. **Backbones/metrics/datasets/
ML:** [3] Argoverse (dataset) · [5] **DBSCAN** (clustering — 3D-TC2/ADoPT's spatial-clustering step) · [6] Fan
point-set-generation · [15] **BEVFusion** · [26] Sun **Test-Time-Training** · [28] Wu density-aware-Chamfer ·
[37] Zhang BEV-realtime-det. → all READ, no pre-empt (methodology/backbone tooling).

### ADoPT bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 37 refs accounted for. **Zero pre-emptions. Zero collaborative-perception candidates** — ADoPT's whole
bibliography is the **single-vehicle LiDAR-spoofing / point-level temporal-consistency** line + point-cloud
registration & scene-flow methodology (ADoPT builds its point-tracking on these) + backbones/datasets. No new
nice-to-have. ⏳ **Awaiting Srinivasa's audit — security subset = the single-vehicle spoof/defense line (all
out-of-family).**

---


---

## BIBLIOGRAPHY 13 — Conformity (Ren, Zhao, Fang, arXiv 2606.21206) — 15 refs
**Dossiered (evolutionary-game, decision-layer not perception). Whole bibliography = UAV-swarm security/comms + game theory + Byzantine formation → NO CP papers, all net-new.**

### 13a. TODO — all 15 net-new (mandate B)
UAV-swarm security/comms/authentication: [1] Ren UAV-collab-sensing-task-offloading · [3] Wang UAV-swarm-security
survey · [4] Ren ISAC-low-altitude-security · [5] Hu hierarchical-cooperative-authentication-UAV-swarm · [6] Wu
DL-secure-UAV-swarm-comm · [7] Wu UAV-swarm-jamming. · Blockchain/trust/resource: [2] Zhao blockchain-trust-VANET ·
[10] Zhao decision-intelligence-6G-V2X · [11] Zhao UAV-platooning-resource. · Byzantine/consensus/formation
(Group-C relevant): [8] Zhu privacy-consensus-under-DoS · [9] Gong **Byzantine formation-tracking multi-UAV** ·
[13] Wu game-theory-swarm-resilience-reconfiguration. · Game-theory / social dynamics: [12] Huang
misinformation-evolution · [14] Ohtsuki-Nowak **replicator-equation-on-graphs** (evolutionary-game math) · [15]
Lin public-opinion-security-bounded-rationality.

### 13b. READ verdicts (mandate B) — all 15 individually abstract-read, ALL no-pre-empt
Whole bibliography = UAV-swarm security/comms + game theory + Byzantine formation/consensus — **decision/
coordination/comms/social-dynamics layer, NOT collaborative perception.**
- **Byzantine/consensus/formation (Group-C relevant):** [9] Gong **Byzantine formation-tracking multi-UAV**
  (control layer) · [8] Zhu privacy-preserving-average-consensus-under-DoS · [13] Wu game-theory-swarm-resilience-
  reconfiguration (network topology). → no pre-empt (coordination/consensus, not perception).
- **Game theory / social dynamics:** [14] Ohtsuki-Nowak **replicator-equation-on-graphs** (evolutionary-game
  math — the model Conformity applies) · [12] Huang misinformation-swarm-simulation · [15] Lin public-opinion-
  bounded-rationality. → no pre-empt (game/opinion dynamics).
- **UAV-swarm security/comms/auth/resource:** [1] Ren task-offloading · [3] Wang **UAV-swarm-security survey** ·
  [4] Ren ISAC-low-altitude-security · [5] Hu cooperative-authentication · [6] Wu DL-secure-swarm-comm · [7] Wu
  anti-jamming · [2] Zhao blockchain-trust-VANET · [10] Zhao 6G-V2X-resource · [11] Zhao UAV-platooning-resource.
  → no pre-empt (network/comms/auth layer).

### Conformity bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 15 refs accounted for. **Zero pre-emptions. Zero collaborative-perception candidates** — Conformity's whole
bibliography is the evolutionary-game / UAV-swarm decision-layer security line. The Byzantine refs (Gong, Zhu)
sit in the coordination/consensus family (Lamport bucket), not perception. No new nice-to-have. ⏳ **Awaiting
Srinivasa's audit — security subset = the Byzantine/game-theory decision-layer refs (all out-of-family).**

---


---

## BIBLIOGRAPHY 11 — 3D-TC2 (You, Hau, Demetriou, MAISP'21) — 14 refs
**Dossiered. Single-vehicle LiDAR-spoofing / temporal-consistency line → NO collaborative-perception papers.**

### 11a. PRIOR / NO-ABS [~6]
[1] nuScenes (dataset) · [3] Cao MSF-ADV (CAD[29], single-vehicle) · [4] Cao CCS'19 (CAD[30]) · [5] Hau
Shadow-Catcher (CAD[41]) · [8] PointPillars · [11] Sun black-box (CAD[69]).

### 11b. TODO — net-new (mandate B) [8], all single-vehicle attacks / backbones
[2] Cao lidar-spoofing-moving-targets · [6] Hau **Object-Removal-Attacks** (AutoSec) · [7] Hau-Lupu WSN-false-data-
injection · [9] Petit remote-attacks-AV-sensors (Black Hat) · [10] Shin **Illusion-and-Dazzle** lidar-optical-attack
· [12] Wu **MotionNet** (BEV motion-prediction backbone) · [13] Xiao **AdVIT** (video temporal-consistency detector)
· [14] Yan **SECOND** (sparse 3D detector).

### 11c. READ verdicts (mandate B) — all 8 net-new individually abstract-read, all no-pre-empt
- [2] Cao lidar-spoofing-moving-targets (AutoSec'21) — **single-vehicle** LiDAR spoof demo. → no pre-empt.
- [6] Hau **Object-Removal-Attacks** (AutoSec'21) — **single-vehicle** point-removal attack. → no pre-empt.
- [7] Hau-Lupu WSN-false-data-injection (CPSS'19) — **temporal-correlation FDI detection in wireless SENSOR
  networks** (message-layer, no perception exchange). → no pre-empt (dossier's out-of-family note confirmed).
- [9] Petit remote-attacks-AV-sensors (Black Hat'15) — **single-vehicle** camera/LiDAR spoof. → no pre-empt.
- [10] Shin **Illusion-and-Dazzle** (CHES'17) — **single-vehicle** LiDAR relay/saturation. → no pre-empt.
- [12] Wu **MotionNet** (CVPR'20) — BEV joint-perception/motion-prediction backbone (3D-TC2's motion-prediction
  module). → no pre-empt.
- [13] Xiao **AdVIT** (ICCV'19) — **single-video** adversarial-frame detector via optical-flow temporal
  consistency (3D-TC2's methodological ancestor; single-agent, no CP/noise/navigation). → no pre-empt.
- [14] Yan **SECOND** (Sensors'18) — sparse 3D detector backbone. → no pre-empt.

### 3D-TC2 bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 14 refs accounted for. **Zero pre-emptions. Zero collaborative-perception papers** — 3D-TC2's whole
bibliography is the **single-vehicle LiDAR-spoofing / temporal-consistency** line (Cao, Hau, Petit, Shin, AdVIT)
+ backbones (PointPillars, SECOND, MotionNet) + nuScenes. Confirms the dossier's title-scan "zero new
candidates." No new nice-to-have. ⏳ **Awaiting Srinivasa's audit — security subset = the single-vehicle
spoof/temporal line (all out-of-family: no cooperative perception).**

---


---

## BIBLIOGRAPHY 9 — SwarmRaft (Dev et al., arXiv 2508.00622) — 43 refs
**Dossiered (⚠ Raft, NOT Byzantine). Entirely Byzantine-consensus/blockchain/UAV-coordination → NO CP papers.**

### 9a. NO-ABS [~8]
[4] Bhatta GNSS book · [10] Buterin Ethereum-blog · [11]/[12] Bitfury public-vs-private-blockchain whitepapers ·
[14] Nakamoto Bitcoin whitepaper · [17] Kwon Tendermint whitepaper · [18] Yanovich Exonum whitepaper · [43] Dev
SwarmRaft GitHub.

### 9b. ⭐ Byzantine-consensus / fault-tolerance judgment subset (abstract-read) [~13]
[8] Bano SoK-consensus-blockchains · [9] Raikwar SoK-DAG-consensus · [13] Dwork **partial-synchrony consensus** ·
[15] Kiayias **Ouroboros PoS** · [16] Castro-Liskov **PBFT** · [19] Ongaro **Raft** · [26] Lu **P-Raft** · [27] Han
**DTPBFT** (BFT for UAV swarm) · [30] Sharma consensus-comparison · [33] Borzdov **BFT-consensus-vulnerabilities** ·
[35] Aditya blockchain-in-robotics survey · [36] O'Keeffe **predictive-fault-tolerance robot-swarms** · [38]
Ranganathan **GNSS-spoofing on UAV swarms**. → all consensus/coordination-layer, same bucket as our cited Lamport;
expect no pre-empt.

### 9c. TODO — UAV-application / networking / blockchain-systems (mandate B) [~22]
[1] Laghari UAV-review · [2] AlMarshoud VANET-trust-review · [3] Bae marine-vehicles-survey · [5] Zhang
GNSS-acquisition · [6] Hoang drone-swarms-SAR · [7] Kuru UAV-logistics · [20] Rafifandi leader-follower-quadrotor ·
[21] Tariverdi Rafting-formation-control · [22] Jia distributed-quadcopter-swarm · [23] Zuo voting-leader-election ·
[24] Seo comm-consensus-codesign · [25] Ilić gossip-consensus · [28] Yazdinejad blockchain-drones-IoT · [29] Xu
multi-UAV-FSO/RF · [31] Hyperledger-Fabric · [32] Kostyuk blockchain-plastic-pipes · [34] Chen CSMA/CA-MIMO-UAV ·
[37] Varadharajan Swarm-Relays · [39] Kato RF-sensor-location · [40] Hu fault-tolerant-forest-fire-UAV · [41] Wang
fault-tolerant-topology-UAV · [42] Vásárhelyi outdoor-flocking.

### 9d. READ verdicts — appended as batches complete

**⭐ Byzantine-consensus / fault-tolerance subset (13) — abstract-read 2026-07-26.** All **distributed-consensus /
BFT / blockchain / GNSS** — coordination/agreement layer, **not collaborative perception**. Same lineage as our
already-cited Lamport. **None pre-empts** (no fused obstacle perception, no learned navigation, no ranging-noise
temporal test).
- [8] Bano **SoK-consensus** · [9] Raikwar **SoK-DAG-consensus** · [13] Dwork **partial-synchrony** (consensus
  theory) · [15] Kiayias **Ouroboros PoS** · [16] Castro-Liskov **PBFT** · [19] Ongaro **Raft** · [26] Lu **P-Raft**
  · [27] Han **DTPBFT** (BFT for UAV swarm) · [30] Sharma consensus-comparison · [33] Borzdov **BFT-vulnerabilities**
  · [35] Aditya blockchain-in-robotics survey · [36] O'Keeffe **predictive-fault-tolerance robot-swarms** (hardware
  FDDR) · [38] Ranganathan **GNSS-spoofing on UAV swarms** (localization takeover). → all READ, no pre-empt.

**Out-by-identity (22) — UAV-application / formation-control / networking / blockchain-systems (mandate B), all individually abstract-read, all no-pre-empt:**
- *UAV surveys / apps / GNSS:* [1] Laghari UAV-review · [2] AlMarshoud **VANET decentralized-trust review** (survey,
  classical-trust bucket) · [3] Bae marine-vehicles survey · [5] Zhang GNSS-acquisition-SFFT · [6] Hoang
  drone-swarms-SAR · [7] Kuru UAV-logistics.
- *Formation control / distributed coordination (Raft-flavoured):* [20] Rafifandi leader-follower-quadrotor · [21]
  Tariverdi **"Rafting" formation-control** · [22] Jia distributed-quadcopter-swarm · [23] Zuo **Raft-inspired
  voting leader-election** · [24] Seo **R2C** comm-consensus co-design · [25] Ilić gossip-consensus-sensor-nets ·
  [40] Hu fault-tolerant-forest-fire-nav · [41] Wang fault-tolerant-formation-topology · [42] Vásárhelyi
  outdoor-flocking.
- *Blockchain systems / networking:* [28] Yazdinejad blockchain-drones-IoT · [29] Xu multi-UAV-FSO/RF-DRL · [31]
  Androulaki **Hyperledger-Fabric** · [32] Kostyuk blockchain-plastic-pipes · [34] Chen CSMA/CA-MIMO-UAV-MAC · [37]
  Varadharajan **Swarm-Relays** (connectivity chains) · [39] Kato RF-sensor-location. → all READ, no pre-empt.

### SwarmRaft bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 43 refs accounted for. **Zero pre-emptions. Zero collaborative-perception papers** — SwarmRaft's whole
bibliography is distributed-consensus/BFT/blockchain + UAV formation-control/coordination/networking + GNSS. The
security-relevant subset = the 13-paper Byzantine-consensus lineage (Lamport bucket; PBFT/Raft/Dwork/Ouroboros…),
none pre-empting our collaborative-*perception* contribution. No new nice-to-have (Byzantine origins already
covered by our cited Lamport). ⏳ **Awaiting Srinivasa's audit — security subset = the 13 consensus/BFT rows.**

---


---

## BIBLIOGRAPHY 8 — CoDynTrust (Xu et al., arXiv 2502.08169) — 35 refs
**Dossiered. BENIGN async-CP + uncertainty-quantification paper → ZERO security-relevant refs (MADE/GCP-like).**

### 8a. PRIOR / NO-ABS [~12]
[1] PointPillars · [9] Lu pose-errors (CAD[58]) · [10] Where2comm · [12] V2VNet · [13] V2X-ViT · [15] CoBEVFlow
(GCP[22]) · [16] DAIR-V2X (dataset) · [17] OPV2V (dataset) · [18] V2X-Sim (dataset) · [19] DiscoNet · [30]
F-Cooper (CAD[32]) · [32] CARLA (sim).

### 8b. TODO — net-new (mandate B) [~23], ALL benign/UQ/backbone/tools — no security candidates
Benign CP: [6] Fan QUEST · [7] Su contrastive-MI-CP · [8] Yang spatio-temporal-CP · [11] Lei latency-aware-CP ·
[14] Yu flow-feature-fusion-VI-CP · [26] Su UQ-collaborative-detection · [27] Su collaborative-MOT-conformal. ·
Uncertainty quantification: [21] Gal UQ-thesis · [22] Gal dropout-bayesian · [23] Lakshminarayanan deep-ensembles ·
[24] Lou uncertainty-multimodal-fusion · [25] Feng leveraging-uncertainties · [28] Kendall-Gal what-uncertainties ·
[29] Kingma VAE. · Backbones / detection: [2] Chen 3D-pointcloud survey · [3] Zhang SAFDNet · [4] Yuan temporal-
channel-transformer · [5] Zhang-Fisac game-theoretic-active-perception · [20] Shi ConvLSTM. · Tools/loss/optim:
[31] Misra Mish · [33] Xu OpenCDA-cosim · [34] Lin Focal-loss · [35] Loshchilov AdamW.

### 8c. READ verdicts (mandate B) — all net-new individually abstract-read, ALL no-pre-empt
**Benign CP (no adversary/trust):** [6] Fan **QUEST** (query-stream CP) · [7] Su **CMiMC** (contrastive-MI CP) ·
[8] Yang **SCOPE** (spatio-temporal CP) · [11] Lei **SyncNet** (latency-aware CP) · [14] Yu **FFNet**
(flow-feature-fusion VIC-CP) · [26] Su **Double-M** (UQ of collaborative detection) · [27] Su **MOT-CUP**
(collaborative-MOT conformal UQ). → benign; no adversary.
**Uncertainty-quantification methods:** [21] Gal UQ-thesis · [22] Gal **MC-dropout** · [23] Lakshminarayanan
**deep-ensembles** · [24] Lou **UMoE** (uncertainty multimodal fusion) · [25] Feng leveraging-uncertainties ·
[28] Kendall-Gal aleatoric/epistemic · [29] Kingma **VAE**. → UQ tooling.
**Backbones / detection / single-vehicle:** [2] Chen 3D-pointcloud survey · [3] Zhang **SAFDNet** (sparse 3D det) ·
[4] Yuan temporal-channel-transformer (single-vehicle video det) · [5] Zhang-Fisac **game-theoretic occlusion-aware
planning** (single-vehicle safe planning, not collaborative-adversary) · [20] Shi **ConvLSTM**.
**Tools / loss / optim:** [31] Misra **Mish** · [33] Xu **OpenCDA** co-sim framework · [34] Lin **Focal-loss** ·
[35] Loshchilov **AdamW**. → all READ, no pre-empt.

### CoDynTrust bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 35 refs accounted for. **Zero pre-emptions. Zero security-relevant papers** — CoDynTrust is a *benign*
async-CP + uncertainty-quantification paper, so its bibliography is entirely benign CP, UQ methods, detection
backbones, and ML tools. **Nothing for Srinivasa to audit here** (like MADE/GCP). No new nice-to-have.

---


---

## BIBLIOGRAPHY 7 — TruPercept (Hurl, Cohen, Czarnecki, Waslander, IEEE IV 2020) — 36 refs
**Dossiered. Rich in classical VANET-trust (MATE bucket) + benign CP + the Obst peer-plausibility paper.**

### 7a. PRIOR / NO-ABS [~7]
PRIOR: [15] Cooper (benign CP) · [23] AVOD (backbone, CAD[47]). · NO-ABS: [16] ETSI CAM standard · [17] ETSI
CPS standard · [26] OMNeT++ simulator · [27] SUMO simulator · [28] CARLA simulator.

### 7b. ⭐ Net-new VANET-trust / peer-plausibility judgment subset (abstract-read) [11]
[2] Minhas VANET-trust-direct-experience-incentives · [4] **Obst** V2V-plausibility-via-vision-MOT (AUDIT_PENDING
Obst/Allig/Tsukada cluster) · [20] Li reputation-based-announcement-VANET · [21] Chen trust-framework-message-
propagation-VANET · [22] Mass distributed-trust-open-multi-agent · [32] Zhang trust-message-relay-VANET · [33]
Minhas multifaceted-agent-trust-MANET · [34] Raya data-centric-trust-ephemeral-adhoc · [35] Balakrishnan
subjective-logic-trust-MANET · [36] Souissi self-adaptive-trust-VANET · [12] Allig perception-alignment-for-CP.

### 7c. TODO — other net-new (mandate B, out-by-identity) [~18]
Benign CP: [1] Khan CP-heterogeneous-traffic · [9] Kim CP-for-AV-control · [10] Jiménez CP-testbed-heterogeneous ·
[11] Li CP-outdoor-thesis · [14] Arnold cooperative-object-classification. · Detection backbones / uncertainty:
[24] Qi Frustum-PointNets · [25] Harakeh BayesOD. · ML classic / surveys: [3] Dietterich ensemble-methods · [13]
Feng multimodal-detection survey · [18] Hobert V2X-comm-enhancements. · V2X/VANET systems: [5] Xu DSRC-safety-msg ·
[6] Volos RELADEC-latency · [7] Riedl road-coverage-models · [8] Correa infra-cooperative-maneuvers · [19] Chen
POMDP-event-handling-VANET. · Synthetic data/datasets: [29] Johnson-Roberson Driving-in-the-Matrix · [30] Yue
lidar-pointcloud-generator · [31] Hurl PreSIL-synthetic-dataset.

### 7d. READ verdicts — appended as batches complete

**⭐ VANET-trust / peer-plausibility cluster (11) — abstract-read 2026-07-26.** All **classical message-/beacon-
layer trust or reputation** (VANET/MANET), none touching learned-navigation CP with fabricated obstacles +
ranging noise + temporal offset. **None pre-empts.** Same family as MATE's cluster.
| # | Ref | Gist | Verdict |
|---|-----|------|---------|
| [2] | Minhas et al. (WI-IAT'10) | VANET agent-trust from **direct experience** + incentives for honesty. | classical VANET trust; no pre-empt |
| [4] | **Obst** et al. (VNC'14) | Check **plausibility of V2V messages via vision-based MOT** (own-sensing vs peer claim). | classical peer-plausibility (own-sensing check); message-layer, no navigation/temporal; **no pre-empt** (AUDIT_PENDING Obst resolved) |
| [20] | Li et al. (TVT'12) | **Reputation-based announcement** scheme for VANETs. | classical reputation; no pre-empt |
| [21] | Chen et al. (ITCS'10) | **Trust-based message propagation+evaluation** under false info. | classical; no pre-empt |
| [22] | Mass & Shehory (2001) | **Certificate-based distributed trust** in open multi-agent systems. | multi-agent trust theory; no pre-empt |
| [32] | Zhang et al. (SCN'12/13) | Trust modeling for **message-relay control + local-action decision** in VANETs. | classical; no pre-empt |
| [33] | Minhas et al. (SMC'11) | **Multifaceted** (role/experience/priority/majority) agent-trust, vehicular. | classical; no pre-empt |
| [34] | Raya et al. (INFOCOM'08) | **Data-centric trust** establishment in ephemeral ad-hoc nets. | classical; no pre-empt |
| [35] | Balakrishnan et al. (SecureComm'08) | **Subjective-logic** trust (models ignorance) for MANET. | classical; no pre-empt |
| [36] | Souissi et al. (SECRYPT'17) | **Self-adaptive** trust management for VANETs. | classical; no pre-empt |
| [12] | Allig & Wanielik (IV'19) | **Perception-information alignment** for cooperative perception (benign; higher-order derivatives for fusion accuracy). | benign CP fusion; no adversary; no pre-empt |

**Out-by-identity refs (18) — all individually abstract-read (mandate B), all no-pre-empt:**
- *Benign CP:* [1] Khan CP-heterogeneous-traffic (handover) · [9] Kim CP-for-AV-control (map-merge/beyond-LoS) ·
  [10] Jiménez CP-testbed (robots+WSN) · [11] Li CP-thesis (coop localization/mapping) · [14] Arnold cooperative-
  object-classification (multi-view). → benign, no adversary.
- *Detection backbone / uncertainty:* [24] Qi **Frustum-PointNets** (single-vehicle 3D det) · [25] Harakeh
  **BayesOD** (uncertainty in detectors).
- *ML classic / surveys:* [3] Dietterich ensemble-methods · [13] Feng deep-multimodal-detection survey · [18]
  Hobert V2X-comm-enhancements.
- *V2X systems:* [5] Xu **DSRC** V2V-safety-messaging (layer-2 broadcast) · [6] Volos **ReLaDec** latency-decision ·
  [7] Riedl road-network-coverage-models · [8] Correa infra-cooperative-maneuvers · [19] Chen **POMDP** event-
  handling under malicious fake-info (VANET decision-layer — trust-adjacent but message/event-layer POMDP, no
  perception-fabrication/navigation → no pre-empt).
- *Synthetic data / datasets:* [29] Johnson-Roberson Driving-in-the-Matrix · [30] Yue LiDAR-point-cloud-generator ·
  [31] Hurl **PreSIL** synthetic dataset. → all READ, no pre-empt.

### TruPercept bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 36 refs accounted for. **Zero pre-emptions. Zero new pre-empting candidates.** Content = the classical
VANET-trust family (11, same bucket as MATE — the AUDIT_PENDING **Obst** paper resolved here, no pre-empt) +
benign CP + detection backbones + surveys + V2X-comm systems + synthetic-data generators. No new nice-to-have
beyond the already-noted classical-MDS bucket. ⏳ **Awaiting Srinivasa's audit — security-relevant subset = the
11-paper VANET-trust cluster (all classical, all no-pre-empt).**

---


---

## BIBLIOGRAPHY 6 — AerialTrust (Hallyburton & Pajic, "Trust-Based Assured Sensor Fusion in Distributed Aerial Autonomy", ICCPS'25) — 37 refs
**Same authors as MATE → ~19 refs overlap (PRIOR). Net-new surfaces the Cavorsi RAS-community neighbour + 2 Byzantine-consensus refs.**

### 6a. PRIOR / already-handled (mostly shared with MATE) [~19]
[2] Ansari (MATE[4]) · [4] Bißmeyer (MATE[8]) · [5] Blackman (MATE[9]) · [6] Cao (single-vehicle) · [9] CARLA ·
[10] Golle (MATE[17]) · [14] Hallyburton camera-lidar (single-vehicle) · [15] Hallyburton AVstack-data (MATE[19])
· [16] Hallyburton Bayesian-trust (MATE[20]) · [17] **MATE** (dossiered — this paper's sibling) · [18] Hallyburton
partial-info-lidar (MATE[21]) · [19] Hallyburton AVstack-platform (MATE[22]) · [21] Huhns (MATE[23]) · [25] Kwon
(MATE[25]) · [27] Monteuuis (MATE[27]) · [29] Pajic attack-resilient-estimators (MATE[31]) · [30] Petit (MATE[33])
· [31] Schuhmacher OSPA (MATE[35]) · [33] Van der Heijden MDS survey (MATE[43]) · [36] Yue (MATE[36]).

### 6b. NO-ABS [1]
[1] Trust-Based-Assured-Sensor-Fusion project website (authors' own).

### 6c. ⭐ Net-new judgment subset — multi-robot trust / Byzantine / UAV-security (abstract-read) [5]
[7] **Cavorsi et al. (T-RO 2024)** — "Exploiting Trust for Resilient Hypothesis Testing with Malicious Robots"
(**Gil group; nearest RAS-community neighbour** — AUDIT_PENDING item 6). · [8] Cheng "Trust-aware control for
ITS" (IV'21). · [11] Grigoropoulos "Byzantine fault tolerance for centrally-coordinated missions with unmanned
vehicles" (CF'20) — **Byzantine + UAV**. · [24] Kihlstrom "Byzantine fault detectors for solving consensus"
(Comp.J'03) — **Byzantine consensus theory**. · [34] Yaacoub "Security analysis of drones systems" (IoT'20) —
UAV-security survey.

### 6d. TODO — other net-new (mandate B, out-by-identity) [~12]
Decentralized fusion / estimation: [12] Grime-Durrant-Whyte decentralized-fusion · [22] Julier-Uhlmann
covariance-intersection · [32] Shemyakin Bayesian-estimation-book. · CPS state-estimation security (Pajic line):
[23] Khazraei intermittent-data-auth · [28] Pajic attack-resilient-noisy-systems. · Network/WSN/MANET trust:
[20] Hu-Sharma ad-hoc-sensor-security · [26] Liu MANET-dynamic-trust · [35] Yu WSN-trust · [37] Zhu
wireless-trust-computing. · UAV app / misc: [3] Bendea low-cost-UAV-post-disaster · [13] Hallyburton
probabilistic-segmentation-FoV (author infra).

### 6e. READ verdicts — appended as batches complete

**⭐ Judgment subset (5) — multi-robot trust / Byzantine / UAV, abstract-read 2026-07-26:**
| # | Ref | Gist | Verdict |
|---|-----|------|---------|
| [7] | **Cavorsi et al., T-RO 2024** (Gil group) | Resilient **binary hypothesis testing** in adversarial multi-robot **crowdsensing**; exploits stochastic inter-robot **trust observations** at a fusion center; tolerates malicious robots **even when they outnumber** legitimate ones (one-shot noisy measurements). | READ — **no pre-empt.** Task = binary hypothesis-testing/crowdsensing decision, **not obstacle-perception + closed-loop navigation**; trust from physical/comms channel, not perception-consistency; no ranging-noise honest-disagreement regime, no temporal offset. **BUT nearest RAS-community neighbour** + shares our "tolerate malicious-majority" theme → **RAS-relevant NICE-TO-HAVE cite** (related-work context). |
| [8] | Cheng et al., Trust-aware control ITS (IV'21) | **Subjective-logic** trust authority embedded in transport infrastructure; trust-aware **control**. | READ — no pre-empt (decision/control layer, not perception). |
| [11] | Grigoropoulos et al., BFT for UAV missions (CF'20) | **Byzantine fault tolerance** for centrally-coordinated unmanned-vehicle missions. | READ — no pre-empt (mission-coordination consensus, not perception; Group-C lineage w/ Lamport which we already cite). |
| [24] | Kihlstrom et al., Byzantine fault detectors (Comp.J'03) | **Byzantine consensus** theory (fault detectors, completeness/accuracy). | READ — no pre-empt (foundational BFT theory). |
| [34] | Yaacoub et al., Drone-systems security survey (IoT'20) | **UAV attack/limitation/countermeasure survey.** | READ — no pre-empt (survey). |

**Nice-to-have note:** **Cavorsi [7]** added to the RAS-relevant optional list (closest Robotics-community
work; resolves AUDIT_PENDING item 6). Below CP-Guard in priority. Grigoropoulos/Kihlstrom sit in the same
Byzantine-consensus bucket as our already-cited Lamport.

**Out-by-identity refs (11) — all individually abstract-read (mandate B), all no-pre-empt:**
- *Decentralized fusion / estimation math:* [12] Grime & Durrant-Whyte decentralized-fusion (no fusion center) ·
  [22] Julier-Uhlmann **covariance-intersection** fusion · [32] Shemyakin Bayesian-estimation+copula book.
- *CPS state-estimation security (Pajic line):* [23] Khazraei attack-resilient-estimation-intermittent-auth
  (perfect-attackability conditions) · [28] Pajic attack-resilient-estimation-noisy-systems.
- *Network / WSN / MANET trust & security:* [20] Hu-Sharma ad-hoc-sensor-security survey · [26] Liu
  MANET-dynamic-trust (IDS-report-based, for secure routing) · [35] Yu WSN-trust survey (attack/countermeasure) ·
  [37] Zhu wireless-trust-computing (delegation-graph transitive-closure).
- *UAV app / MATE-author infra:* [3] Bendea low-cost-UAV post-disaster mapping · [13] Hallyburton
  **Probabilistic-Segmentation FoV-estimation** (learning-based FoV + MC-dropout anomaly detection — perception
  FoV robustness, not obstacle-fabrication trust; MATE-author line). → all READ, no pre-empt.

### AerialTrust bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 37 refs accounted for. **Zero pre-emptions.** ~19 overlap with MATE (PRIOR). Net-new = the multi-robot
trust / Byzantine / UAV judgment subset (**Cavorsi → RAS-relevant nice-to-have**; Grigoropoulos/Kihlstrom =
Byzantine-consensus, Lamport bucket) + decentralized-fusion math, CPS state-estimation, network/WSN/MANET
trust, and UAV-app/FoV work. ⏳ **Awaiting Srinivasa's audit — security-relevant subset = the 5-paper
multi-robot/Byzantine judgment set (all no-pre-empt).**

---


---

## BIBLIOGRAPHY 5 — MATE (Hallyburton & Pajic, "Multi-Agent Trust Estimator", CCS'25) — 47 refs
**Dossiered. Rich in classical VANET-trust / CP-misbehaviour-detection refs (the Allig/Tsukada cluster).**

### 5a. PRIOR / already-handled [~9]
[2] Ambrosin (CAD[23], nice-to-have) · [10] Cao CCS'19 (single-vehicle) · [15] CARLA (sim) · [18] Hallyburton
camera-lidar black-box (single-vehicle) · [26] PointPillars (backbone) · [27] Liu "Seeing is not believing"
(CAD[55]) · [28] MISO-V (CAD[57], nice-to-have) · [38] Sun black-box (CAD[69]) · [40] Thys person-patch
(MADE[31]) · [47] **CAD** (dossiered).

### 5b. ⭐ Net-new CP-trust / VANET-misbehaviour cluster — abstract-read (the judgment subset) [12]
[1] Allig trustworthiness-estimation-in-collective-perception · [4] Ansari V2X-misbehaviour-CP-standardization ·
[8] Bißmeyer VANET-node-trust-plausibility-particle-filter · [17] Golle malicious-data-detection-VANET ·
[20] Hallyburton **Bayesian-trust-collaborative-multi-agent** (MATE authors' own broader trust line) · [29] Lo
illusion-attack-VANET-message-plausibility · [30] Monteuuis implausible-dimension ML-detector · [37] Soleymani
fuzzy-logic-trust-VANET · [39] Theodorakopoulos trust-in-ad-hoc-networks · [42] Tsukada CP-misbehaviour-detection
· [43] Van der Heijden **MDS survey** (cooperative-ITS) · [44] Wang Bayesian-trust-construction.

### 5c. TODO — other net-new (mandate B, out-by-identity) [~24]
Tracking/estimation textbooks+metrics: [6] Bar-Shalom estimation-book · [7] Bar-Shalom MTT-book · [9] Blackman
radar-tracking · [14] Crouse 2D-assignment · [35] Schuhmacher OSPA-metric · [11] Casella Gibbs-sampler · [32]
Park concave-hull. · Adversarial-ML: [5] Athalye obfuscated-gradients · [16] Eykholt stop-sign-attack · [24] Jia
MOT-attack · [41] Tramer adaptive-attacks. · MATE-authors' infra: [19] Hallyburton AVstack-datasets · [21]
Hallyburton partial-info-lidar-attack · [22] Hallyburton AVstack-platform. · Tools/misc: [12] MMDetection · [13]
Cook ray-tracing · [34] ROS · [23] Huhns trusted-autonomy · [25] Kwon healthcare-security · [31] Pajic
attack-resilient-state-estimators · [33] Petit AV-cyberattack-survey · [36] Shah rumor-source-detection · [45]
Yeremenko secure-routing · [46] Yue intrusion-prevention.

### 5d. READ verdicts — appended as batches complete

**⭐ CP-trust / VANET-misbehaviour cluster (12) — the judgment subset, all abstract-read 2026-07-26.**
Every one is **classical message-/beacon-layer trust or misbehaviour detection** (CAM/CPM plausibility,
VANET reputation, Bayesian/fuzzy trust on tracks or messages). **None pre-empts:** no closed-loop learned
navigation objective, no ranging-noise honest-disagreement regime, no cross-agent temporal offset test on
shared obstacles, no adaptive attacker in our sense.
| # | Ref | Gist | Verdict |
|---|-----|------|---------|
| [1] | Allig (VNC'19) | Trustworthiness estimation of entities in **collective perception** (V2X). | classical CP-trust; no pre-empt |
| [4] | Ansari (CSCN'21) | Security assessment of **CPM** + standardization inputs (bogus-object threat). | standards analysis; no pre-empt |
| [8] | Bißmeyer (VNC'12) | VANET node-trust via **particle-filter plausibility** on location data. | classical VANET trust; no pre-empt |
| [17] | Golle (VANET'04) | Detect/correct malicious VANET data by scoring **explanations consistent with a world model**. | classical (beacon-layer); no pre-empt |
| [20] | **Hallyburton Bayesian-trust** (arXiv'24) | MATE authors' own hierarchical-Bayesian trust on MTT tracks under compromised agents. | **same author line as MATE (dossiered)**; MTT track-score, no navigation/noise/temporal; no pre-empt |
| [29] | Lo (Globecom'07) | **Illusion attack** on VANET + plausibility-validation-network. | classical; no pre-empt |
| [30] | Monteuuis (SSIC'18) | ML detector for **implausible vehicle-dimension** in V2X msgs. | message classifier; no pre-empt |
| [37] | Soleymani (Access'17) | **Fuzzy-logic trust** model (experience+plausibility) in VANET+fog. | classical VANET trust; no pre-empt |
| [39] | Theodorakopoulos (WiSe'04) | Trust-evidence evaluation in **ad-hoc networks** (uncertain/incomplete). | network-trust theory; no pre-empt |
| [42] | Tsukada (CCNC'22) | **CPM-based misbehaviour detection** improving CAM validation under pseudonyms. | classical CPM-MDS; no pre-empt |
| [43] | Van der Heijden (survey'18) | **Survey of misbehaviour detection** in cooperative-ITS (insider attacks, semantic analysis). | survey — good representative of the classical-MDS field |
| [44] | Wang (IAT'06) | **Bayesian** agent-trust construction via graph theory. | multi-agent trust theory; no pre-empt |

**Nice-to-have note:** this cluster is the classical VANET-trust/MDS family already represented by
Ambrosin/MISO-V. If a *classical-lineage* representative is ever wanted, **Van der Heijden's MDS survey [43]**
(or Allig [1] for CP specifically) is the single best pick — but still optional, below CP-Guard.

**Out-by-identity refs (24) — all individually abstract-read (mandate B), all no-pre-empt:**
- *Tracking/estimation textbooks & metrics & math:* [6] Bar-Shalom estimation-book · [7] Bar-Shalom MTT-book ·
  [9] Blackman radar-tracking · [14] Crouse 2D-assignment · [35] Schuhmacher **OSPA metric** · [11] Casella
  Gibbs-sampler · [32] Park concave-hull. (MATE's tracking machinery.)
- *Adversarial-ML / perception attacks:* [5] Athalye obfuscated-gradients · [16] Eykholt stop-sign RP2 · [24]
  Jia MOT tracker-hijacking (single-vehicle pipeline) · [41] Tramer adaptive-attacks-methodology.
- *MATE authors' own infra / attack line:* [19] Hallyburton AVstack-datasets · [21] Hallyburton
  partial-info-lidar (**single-vehicle** datagram attacks) · [22] Hallyburton AVstack-platform.
- *CPS / network security / theory / tools:* [31] Pajic attack-resilient-state-estimators (control) · [33]
  Petit AV-cyberattack survey · [36] Shah rumor-source-detection (network theory) · [23] Huhns trusted-autonomy ·
  [12] MMDetection · [13] Cook distributed-ray-tracing (graphics; MATE's FoV/sensor sim) · [34] ROS · [25] Kwon
  proactive-vs-reactive healthcare-security-economics · [45] Yeremenko secure-routing · [46] Yue
  intrusion-prevention-economics. → all READ, no pre-empt.

### MATE bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 47 refs accounted for. **Zero pre-emptions.** No new pre-empting candidate. The 12-paper classical
VANET-trust / CPM-misbehaviour cluster reinforces the family we already bracket (best optional representative =
Van der Heijden MDS survey [43]); everything else is tracking textbooks/metrics, adversarial-ML, the MATE
authors' own AVstack infra, or CPS/network-security/tools. ⏳ **Awaiting Srinivasa's audit — security-relevant
subset = the 12-paper CP-trust cluster (all no-pre-empt, all classical/message-layer).**

---


---

## BIBLIOGRAPHY 4 — GCP (Tao et al., "Guarded Collaborative Perception", arXiv'25) — 35 refs
**Dossiered paper. Its CP-security cites are ALL already handled → zero new security candidates.**

### 4a. PRIOR / already-handled this sweep [~14]
[1] Cooper (benign CP) · [2] V2X-Sim (dataset) · [4] Where2comm (benign CP) · [9] **CAD** (dossiered) ·
[10] Tu adversarial-comm (inline) · [11] **ROBOSAC** (dossiered) · [12] **MADE** (dossiered) ·
[13] **CP-Guard** (triaged, PRBI[9] — planned cite) · [14] **CP-Guard+** (triaged, PRBI[8]) ·
[18] DiscoNet · [19] V2VNet · [20] When2com · [23] Lu pose-errors (CAD[58]) · [28] Benjamini-Hochberg FDR
(MADE) · [29] CARLA (sim) · [32] Madry PGD · [33] Carlini-Wagner C&W (PRBI) · [34] FaFNet (PRBI) ·
[35] Kurakin BIM (PRBI). → all PRIOR, none a new candidate.

### 4b. TODO — net-new (mandate B) [~15] — NO CP-security candidates among them
Benign CP (comm-efficiency / robustness / domain-gen): [3] Hu Adaptive-Comm-domain-align · [5] Hu Full-scene-
domain-generalization-BEV-seg · [6] Fang **PACP** priority-aware-CP · [7] Tao **Direct-CP** · [21] Fang **R-ACP**
task-oriented-comm · [22] Wei Asynchrony-Robust-CP-BEV-Flow. · Datasets: [8] **V2V4Real** (CVPR'23). · Surveys:
[15] Han CP-methods-datasets-challenges · [16] Hu CP-challenges-solutions-opportunities. · Backbones: [17] Zeng
**DSDNet** self-driving-net · [24] Yin LiDAR-online-3D-video-det. · Network-security / other (GCP's anomaly-detection
framing): [27] Wei **LSTM-autoencoder DDoS** anomaly-detection · [30] Xiang **low-rate DDoS** detection · [31] Ahn
**Stuxnet-style AV malware** modeling · [25] Gao sweep-coverage sensor-net scheduling · [26] Liu LiDAR-inertial
**odometry**. → confirm each by abstract below.

### 4c. READ verdicts (mandate B) — all net-new individually abstract-read
**Benign CP (comm-efficiency / robustness / domain-gen — no adversary/trust):** [3] Hu **ACC-DA** (channel-aware
adaptive comm) · [6] Fang **PACP** (priority-aware BEV-match comm) · [7] Tao **Direct-CP** (direction-aware
attention) · [21] Fang **R-ACP** (task-oriented comm + online self-calibration) · [22] Wei **CoBEVFlow**
(asynchrony-robust via BEV motion-flow — benign temporal alignment, no adversary) · [5] Hu **DG-CoPerception**
(domain generalization for BEV-seg). → READ, **no pre-empt**.
**Dataset / surveys:** [8] **V2V4Real** (real-world V2V CP dataset) · [15] Han CP survey · [16] Hu CP survey
(challenges/solutions). → READ, no pre-empt.
**Single-vehicle backbones:** [17] Zeng **DSDNet** (single-net detect+predict+plan) · [24] Yin LiDAR online-3D-video
detector (PMPNet + spatiotemporal-transformer, **single-vehicle**). → READ, no pre-empt.
**Network-security / sensor-net / SLAM (GCP's anomaly-detection lineage, but different domain):** [27] Wei
**LSTM-autoencoder DDoS** anomaly-detection · [30] Xiang low-rate **DDoS** detection (entropy metrics) · [31] Ahn
**Stuxnet-style AV malware** epidemic modeling · [25] Gao sweep-coverage sensor-net scheduling · [26] Liu
**LiDAR-inertial odometry** (Kalman smoother). → READ, no pre-empt (not collaborative-perception trust).

### GCP bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 35 refs accounted for. **Zero pre-emptions. Zero new CP-security candidates** — every CP-security paper GCP
cites (CAD, MADE, ROBOSAC, Tu, CP-Guard, CP-Guard+) was already handled. Remainder = benign CP, datasets,
surveys, single-vehicle backbones, adversarial-ML classics, and network-security (DDoS/malware) items.
⏳ **Awaiting Srinivasa's audit — but the security-relevant subset here is nil (no new candidates).**

---


---

## BIBLIOGRAPHY 3 — PRBI ("All Vehicles Can Lie", Yu et al.) — 37 refs
**Our closest competitor. Its bibliography is the richest in CP-security work — and it surfaces the
CP-Guard / CP-Guard+ / LUCIA cluster (task #3, previously un-triaged).**

### 3a. PRIOR / already-dossiered [~8]
| # | Ref | Status |
|---|-----|--------|
| [7] | Hallyburton & Pajic, **MATE** (CCS'25) | PRIOR — DOSSIERED |
| [11] | PLA-LiDAR (S&P'23) | PRIOR — single-vehicle laser (CAD[44]) |
| [14] | DiscoNet (NeurIPS'21) | PRIOR — benign CP arch |
| [16] | Li **"Among Us" = ROBOSAC** (ICCV'23) | PRIOR — DOSSIERED |
| [24] | Schiegg CP-service 802.11p (WCNC'20) | PRIOR (CAD[64]) |
| [25] | Tao **GCP** (arXiv'25) | PRIOR — DOSSIERED |
| [27] | Tu adversarial multi-agent comm (ICCV'21) | PRIOR — inline-triaged |
| [35] | **CAD** (USENIX'24) | PRIOR — anchor, dossiered |
| [37] | **MADE** (IROS'24) | PRIOR — dossiered |

### 3b. NO-ABS — dataset / metric-tool [~2]
[2] nuScenes (dataset) · [15] V2X-Sim (dataset).

### 3c. ⭐ NET-NEW **CP-SECURITY** candidates — the ones that matter (abstract-read carefully) [3]
| # | Ref | Why it matters |
|---|-----|----------------|
| [9] | Hu et al., **CP-Guard** (AAAI'25) — "Malicious Agent Detection and Defense in Collaborative BEV Perception" (its method = **PASAC**, the "PASAC" baseline in PRBI's tables) | Named SOTA CP malicious-agent defense; task #3 cluster |
| [8] | Hu et al., **CP-Guard+** (arXiv 2502.07807, 2025) — "New Paradigm for Malicious Agent Detection and Defense in CP" | Follow-up to CP-Guard; task #3 cluster |
| [28] | Wang et al., **LUCIA** (USENIX Sec'25) — "From Threat to Trust: Exploiting Attention Mechanisms for Attacks and Defenses in Cooperative Perception" | Attention-level attack+defense in CP; task #3 cluster (missed in earlier PRBI sweep) |

### 3d. TODO — other net-new (single-vehicle attacks / benign CP / adversarial-ML / backbones / surveys) [~15]
Single-vehicle physical attacks: [3] Cao "You can't see me" physical-removal (USENIX'23) · [23] Sato
lidar-spoofing-realism (NDSS'25). · Downstream / other attacks: [19] Lou traj-pred-attack (USENIX'24, PRIOR?)
· [31] Wang VLM-token attack · [32] Wang imperceptible-3D-detector attack · [34] Yu multi-frame traj-pred
attack (CVPR'25) · [36] Zhang black-box imperceptible attack · [26] Tsai robust-adversarial-objects. ·
Adversarial-ML classics: [4] Carlini-Wagner C&W · [13] Kurakin BIM · [21] Madry PGD (PRIOR). · Benign CP /
systems: [5] Fang info-bottleneck-edge-video · [10] Hu codebook-CP · [29] Wang UMC · [17] Li SimDiff ·
[20] Luo FaFNet (backbone). · Surveys / metric: [6] Gao CP-intersections survey · [18] Liu AD-datasets survey
· [33] Xiang MSF-CP review · [22] Niwattanakul Jaccard-coefficient · [12] Keswani Proto2proto.

### 3e. READ verdicts — appended as batches complete

**⭐ Batch 3-i (2026-07-26) — the CP-security cluster (task #3), abstract-read:**
| # | Ref | Abstract gist | Verdict |
|---|-----|---------------|---------|
| [9] | **CP-Guard** (AAAI'25) | Per-agent CP defense: **PASAC** (probability-agnostic sample consensus) + **CCLoss** (collaborative-consistency loss vs ego); detect+eliminate malicious agents in **BEV-segmentation** CP. | READ — **NO pre-empt.** Sample-consensus feature-level defense, **BEV-segmentation-accuracy** metric; **no learned navigation-success objective, no ranging-noise honest-disagreement regime, no cross-agent temporal offset test, no adaptive attacker.** Same family as ROBOSAC/MADE/PRBI (which we already cite/differentiate). → **higher-value NICE-TO-HAVE cite** (named SOTA CP defense; = the "PASAC" baseline in PRBI). |
| [8] | **CP-Guard+** (arXiv'25) | Feature-level malicious-agent detection **without verifying final perception** (cheaper); **CP-GuardBench** dataset + **Dual-Centered Contrastive Loss**. | READ — **NO pre-empt.** Learned feature-level detector; AP/detection metric, no navigation/noise/temporal/adaptive. Follow-up to CP-Guard. → **higher-value NICE-TO-HAVE cite.** |
| [28] | **LUCIA / "From Threat to Trust"** (USENIX Sec'25) | Presents **SOMBRA**, a stealthy **object-REMOVAL** attack exploiting attentive-fusion in CP, + attention-based defense. | READ — **NO pre-empt.** Attention/feature-level; attack = object *removal* (not false-obstacle *fabrication*); AP-scored; no learned navigation, no honest-disagreement noise regime, no cross-agent temporal test. Sibling of TrustFlip/CAD attack line. → **NICE-TO-HAVE cite** (recent CP attack+defense). |

**Batch 3-ii — single-vehicle physical attacks (out of family):**
| # | Ref | Gist | Verdict |
|---|-----|------|---------|
| [3] | Cao "You Can't See Me" (USENIX'23) | **Single-vehicle** laser removal of genuine-obstacle points at the LiDAR sensor level. | READ — no pre-empt (single-vehicle sensor attack; our 3D-TC2/ADoPT bracket). |
| [23] | Sato "Realism of LiDAR spoofing" (NDSS'25) | **Single-vehicle** LiDAR spoofing feasibility at speed/distance. | READ — no pre-empt (single-vehicle physics). |

**Batch 3-iii — remaining net-new (mandate B), all out-of-family:**
- **Adversarial-ML classics / single-model attacks:** [4] Carlini-Wagner **C&W** · [13] Kurakin **BIM**
  (physical-world AE) · [26] Tsai robust-adversarial-**3D-objects** (PointNet++) · [32] Wang imperceptible-3D-
  detector attack · [36] Zhang perception-driven black-box AE · [31] Wang **VT-Attack** (attacks vision-language
  models — not CP) · [34] Yu multi-frame **trajectory-prediction** attack (downstream predictor) · [19] Lou
  traj-pred-attack (PRIOR) · [21] Madry PGD (PRIOR). → READ, no pre-empt.
- **Benign CP / comm-efficiency / backbones:** [5] Fang **PIB** (edge-video CP, SNR-prioritized bandwidth) ·
  [10] Hu **CodeFilling** (codebook comm-efficient CP) · [29] Wang **UMC** (bandwidth/multi-resolution CP) ·
  [17] Li **SimDiff** (point-cloud HW acceleration) · [20] Luo **FaFNet** (3D det/track backbone — PRBI's own
  detector). → READ, no pre-empt (benign; no adversary/trust).
- **Surveys / metric / interpretability:** [6] Gao CP-at-intersections survey · [18] Liu AD-datasets survey ·
  [33] Xiang MSF-CP review · [22] Niwattanakul **Jaccard-coefficient** (the similarity metric PRBI uses) ·
  [12] Keswani **Proto2Proto** (prototype-interpretability distillation). → READ, no pre-empt.

### PRBI bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 37 refs accounted for. **Zero pre-emptions.** **Key yield:** the task-#3 CP-security cluster
(**CP-Guard [9]**, **CP-Guard+ [8]**, **LUCIA/SOMBRA [28]**) — none pre-empts (all AP/feature-level, no
navigation/noise/temporal/adaptive) but all are same-family; **Srinivasa elevated CP-Guard to a PLANNED cite**
(dossier owed — see NICE_TO_HAVE_CITATIONS.md + AUDIT_PENDING.md). Everything else = already-dossiered anchors
(CAD, MADE, MATE, GCP, ROBOSAC, Tu), single-vehicle attacks, adversarial-ML classics, benign CP, backbones,
surveys. ⏳ **Awaiting Srinivasa's audit of the security-relevant subset (the 3 CP-Guard-cluster rows + Cao/Sato).**

---


---

## BIBLIOGRAPHY 2 — MADE (hypothesis-test malicious-agent detection) — 44 refs

### 2a. PRIOR / already-dossiered (cross-referenced) [~9]
| # | Ref | Status |
|---|-----|--------|
| [12] | PointPillars | PRIOR (CAD[49]) — backbone |
| [13] | Li et al., **"Among Us: Adversarially Robust CP by Consensus"** (ICCV'23) | **= ROBOSAC — already DOSSIERED** (cross-check ✓) |
| [14] | Li et al., Distilled Collaboration Graph (**DiscoNet**, NeurIPS'21) | PRIOR — benign CP arch |
| [18] | Liu et al., **When2com** (CVPR'20) | PRIOR — benign comm CP |
| [32] | Tu et al., Adversarial Attacks on Multi-Agent Comm (ICCV'21) | PRIOR — inline-triaged, cite-ready |
| [34] | V2VNet (ECCV'20) | PRIOR (CAD[73]) — benign CP arch |
| [37] | V2X-ViT (arXiv'22) | PRIOR (CAD[78]) — benign CP arch |
| [39] | DAIR-V2X (CVPR'22) | PRIOR (CAD[81]) — dataset |
| [41] | **CAD** (USENIX Sec'24) | PRIOR — the anchor, dossiered |

### 2b. NO-ABS — policy / standard / tool / dataset (no readable abstract) [~4]
[16] Lippe autoencoder tutorial (webpage) · [21] White-House OSTP *AI Bill of Rights* (policy) ·
[23] Federal Register occupant-protection rule (regulation) · [11] Kuhn Hungarian method 1955 (classic math).

### 2c. TODO — net-new abstracts to read this sweep (mandate B) [~31]
Adversarial-ML / physical-patch attacks on **single** detectors: [6] Eykholt physical-adv-examples · [9] Hu
naturalistic-patch · [15] Li Yuezun background-patches · [17] Liu DPatch · [19] Madry PGD · [28] Szegedy
intriguing-properties · [31] Thys person-patch · [35] Xie adv-seg/det · [36] Xu adv-t-shirt · [42] Zhao Yue
"Seeing isn't believing". · Detector/tracking/seg backbones: [25] U-Net · [30] Tang SPVConv · [38] Yin
CenterPoint · [40] Zhan tri-layer · [43] Zhou CenterTrack · [44] Zhu Deformable-DETR · [22] Poulton LiDAR
optical-phased-array (hardware). · Statistics / conformal / detection-theory: [1] Angelopoulos conformal ·
[4] Benjamini-Hochberg FDR · [7] Hampel influence-curve · [8] Hochberg-Tamhane multiple-comparison · [27]
Storey FDR · [33] Vovk conformal. · Multi-agent / distributed / federated / surveys: [2] Bakliwal multi-agent
industrial-assets · [3] Baltrusaitis multimodal-ML survey · [5] Chen distributed-learning-wireless survey ·
[10] Where2comm (benign CP) · [20] McMahan federated-learning · [24] Ren CP survey. · CV-security misc:
[26] Srinivas cyber-security-regs · [29] Takefuji connected-vehicle-vuln commentary.

**First-glance read:** ZERO new collaborative-perception-*security-trust* candidates. Every TODO is an
adversarial-ML classic, a detector/tracking backbone, a statistics/conformal method, a benign CP arch, a
survey, or a policy doc. Confirming each by individual abstract (mandate B) below.

### 2d. READ verdicts (mandate B) — appended as batches complete
Each abstract fetched individually. **Single-detector adversarial-ML attacks (out — attack ONE model's
pixels, no multi-agent fusion/trust/navigation):** [6] Eykholt physical-adv-examples-for-detectors · [17]
DPatch (Faster-RCNN/YOLO patch) · [31] Thys person-detection patch · [42] Zhao-Yue "Seeing isn't believing"
(hiding/appearing AE on real-world detectors) · [19] Madry PGD (robust-optimization) · [15] Li-Yuezun
background-patch SSM vuln · [35] Xie DAG (adv seg/det) · [36] Xu adversarial-T-shirt · [28] Szegedy
intriguing-properties (the original AE paper). **3D detection/backbone (out — perception building blocks):**
[30] SPVNAS (3D-NAS point-voxel) · [38] CenterPoint (3D det+track). → all READ, **no pre-empt**.

**Backbones / detection / tracking (out — perception building blocks):** [25] U-Net (biomedical seg) ·
[43] CenterTrack (track-as-points) · [44] Deformable-DETR (transformer detector) · [22] Poulton (LiDAR
optical-phased-array **hardware/photonics**) · [40] Zhan tri-layer occluded-detection plugin. → READ, no
pre-empt.

**Statistics / conformal / detection-theory (out — MADE's *method* toolbox: it frames malicious-agent
detection as a hypothesis test):** [1] Angelopoulos conformal-prediction intro · [4] Benjamini-Hochberg FDR ·
[27] Storey FDR · [33] Vovk conditional-validity conformal · [7] Hampel influence-curve robust-estimation ·
[8] Hochberg-Tamhane multiple-comparison (book). → READ, no pre-empt (these are the statistical machinery
MADE *uses*, not competing systems).

**Multi-agent / distributed / federated / surveys / policy (out):** [10] Where2comm (benign
communication-efficient CP — bandwidth, no adversary) · [24] Ren CP-survey (benign review) · [2] Bakliwal
multi-agent **industrial-asset** collaborative learning (not perception) · [20] McMahan **Federated Learning**
(decentralized training) · [5] Chen distributed-learning-in-wireless **survey** · [3] Baltrusaitis multimodal-ML
**survey** · [29] Takefuji connected-vehicle-vuln **commentary** (OBD-II) · [26] Srinivas cyber-security
**regulation** framework. → READ, no pre-empt.

### MADE bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 44 refs accounted for. **Zero pre-emptions.** MADE's bibliography is almost entirely (a) single-detector
adversarial-ML attacks, (b) 3D detection/tracking/seg backbones, (c) the statistics/conformal machinery it
uses for hypothesis-test detection, and (d) benign CP archs / surveys / policy — plus already-dossiered
anchors (CAD [41], ROBOSAC="Among Us" [13], Tu [32]) and PRIOR CP works (V2VNet, V2X-ViT, DAIR-V2X, When2com,
DiscoNet). **No new CP-security-trust candidates; no new nice-to-have cites.** ⏳ **Awaiting Srinivasa's audit
(security-relevant subset here = essentially nil, since MADE cites no new misbehaviour-detection work).**

---


---

## BIBLIOGRAPHY 1 — CAD (Zhang et al., USENIX Security 2024) — 91 refs

### 1a. NO-ABS — website / standard / product / dataset / simulator (no abstract exists) [~22]
| # | Ref | What it is |
|---|-----|-----------|
| [1] | 3GPP Release 14 | cellular standard |
| [2] | Qualcomm C-V2X | product page |
| [3] | Huawei C-V2X | product page |
| [4] | Infineon C-V2X | product page |
| [5] | CARLA | simulator |
| [6] | Tesla Autopilot | product page |
| [7] | Autoware | open-source AV stack |
| [8] | Baidu Apollo | AV stack |
| [9] | Bosch C-V2X | product page |
| [10] | Honda Automated Drive | product page |
| [11] | OxTS INS | product page |
| [12] | SUMO | traffic simulator |
| [13] | Waymo | product page |
| [14] | Automotive Edge Computing Consortium | consortium |
| [15] | ETSI DTS/ITS-00167 work item | standard work item |
| [16] | Ford AV Dataset | dataset |
| [17] | IEEE 1609.2-2022 | security standard |
| [18] | SAE J3224_202208 | V2X sensor-sharing standard |
| [19] | Mcity (U Michigan) | test facility |
| [20] | ETSI TR 103 562 | ITS technical report |
| [79] | OPV2V (Xu et al., ICRA'22) | CP benchmark dataset |
| [81] | DAIR-V2X (Yu et al., CVPR'22) | V2I dataset |

### 1b. PRIOR — already abstract-/full-read (cross-referenced to earlier passes) [~28]
| # | Ref | Where read / verdict |
|---|-----|----------------------|
| [29] | Cao MSF-ADV (S&P'21) | PRIOR — single-vehicle multi-sensor, out |
| [30] | Cao LiDAR spoofing (CCS'19) | PRIOR — single-vehicle, out |
| [32] | F-Cooper (SEC'19) | PRIOR — benign feature-fusion arch |
| [33] | Cooper (ICDCS'19) | PRIOR — benign raw-data CP |
| [34] | Coopernaut (CVPR'22) | PRIOR — FULL dossier; benign precedent (credited) |
| [40] | Hallyburton camera-LiDAR (USENIX'22) | PRIOR — single-vehicle multi-sensor |
| [44] | PLA-LiDAR (S&P'23) | PRIOR — single-vehicle laser injection |
| [49] | PointPillars | PRIOR — detector backbone (NO-ABS class) |
| [51] | Li FLAT (ICCV'21) | PRIOR — single-vehicle GPS/traj spoof |
| [54] | FusionEye (SECON'19) | PRIOR — benign bandwidth study |
| [58] | Lu robust-to-pose-errors (arXiv'22) | PRIOR — benign robustness to pose errors |
| [62] | AutoCast (arXiv'21) | PRIOR — benign sharing scheduler |
| [65] | Shen Drift-with-Devil (USENIX'20) | PRIOR — single-vehicle GPS/MSF |
| [66] | PointRCNN | PRIOR — detector backbone (NO-ABS) |
| [67] | VIPS (MobiCom'22) | PRIOR — benign infra fusion |
| [68] | Song object-level CP (arXiv'22) | PRIOR — benign robustness to pose errors |
| [69] | Sun black-box sensor attack (USENIX'20) | PRIOR — single-vehicle |
| [71] | Tu physically-realizable (CVPR'20) | PRIOR — single-vehicle adversarial object |
| [72] | Tu adversarial multi-agent comm (ICCV'21) | PRIOR — INLINE triage, cite-ready, no pre-empt |
| [73] | V2VNet (ECCV'20) | PRIOR — benign CP arch (Vadivelu backbone) |
| [78] | V2X-ViT (ECCV'22) | PRIOR — benign transformer CP arch |
| [84] | Zhang traj-pred robustness (CVPR'22) | PRIOR — downstream predictor |
| [85] | Zhang async multi-vehicle (MobiCom'23) | PRIOR — benign asynchrony robustness (RAO) |
| [87] | EMP (MobiCom'21) | PRIOR — benign edge fusion |
| [90] | VoxelNet | PRIOR — detector backbone (NO-ABS) |
| [91] | Zhu arbitrary objects (CCS'21) | PRIOR — single-vehicle |

### 1c. TODO — net-new abstracts to read this sweep [~41]
[21] Alaba survey lidar 3D det · [22] Alheeti lidar-spoof-detection-in-AV · [23] Ambrosin misbehavior-detection
objects-based-shared-perception-V2X · [24] Avis convex-hull-algorithms · [25] Baee IEEE-1609.2-broadcast-auth ·
[26] Boddupalli REPLACE platoon-security · [27] Boddupalli REDEM comm-attack-detection · [28] Canilho k-means-FPGA ·
[31] Chen cooperative-perception-environment-traffic-ops · [35] Douillard 3D-lidar-segmentation · [36] Fischler RANSAC ·
[37] Godoy grid-based-collective-perception · [38] Günther collective-perception-in-a-vehicle · [39] Hadded
security-attacks-collective-perception-on-ramp · [41] Hau Shadow-Catcher · [42] Hu CVShield-TEE · [43] Hu
Gatekeeper-broadcast-auth · [45] Kim vehicle-traj-prediction-occupancy-grid · [46] Kim V2V-message-plausibility-platoon ·
[47] Ku AVOD · [48] Kumar CarSpeak · [50] Li multi-vehicle-cooperative-local-mapping-occupancy-merge · [52] Li
lidar-for-AD-survey · [53] Lin architectural-implications-AD · [55] Liu seeing-is-not-believing-perception-error-attacks ·
[56] Liu Stars-can-tell-GPS-spoof-defense · [57] Liu MISO-V-misbehavior-detection-collective-perception · [59] Mohan
EfficientPS · [60] Narayanan 5G-in-the-wild · [61] Pham survey-security-CAV · [63] Ranganathan SPREE-gps · [64] Schiegg
collective-perception-802.11p · [70] Toghi cellular-V2X-congestion · [74] Warner GPS-spoofing-countermeasures · [75] Weng
AB3DMOT · [76] Wu SqueezeSeg · [77] Xu CoBEVT · [80] Yoshizawa V2X-security-survey · [82] Yuan FPV-RCNN keypoints-fusion ·
[83] Zermas fast-3D-point-cloud-segmentation · [86] Zhang roadside-cooperative-perception-system · [88] Zhao
false-data-injection-CAV-cloud-sandbox · [89] Zhao collaborative-V2X-data-correction-road-safety

**Sweep status:** CAD classified (2026-07-26). NO-ABS 22 · PRIOR 28 · TODO ~41. Next: read the TODO abstracts
in batches, moving each to a READ/KEEP? verdict row below.

### 1d. READ verdicts (this sweep) — appended as batches complete

**Batch 1 (2026-07-26) — CP-security / misbehavior-detection, the highest-risk subset:**
| # | Ref | Abstract gist | Verdict |
|---|-----|---------------|---------|
| [23] | Ambrosin, *Misbehavior Detection System for Objects-Based Shared Perception V2X* (ITSC'19) | Design of a **rule/plausibility-based misbehavior detector** at the CPM (collective-perception-message) layer; checks semantic correctness of shared object data. | READ — **no pre-empt.** Classical message-layer MDS; no learned navigation policy, no success metric, no ranging-noise regime, no adaptive attacker. Same *classical-CPM-MDS* family our related.tex brackets via CAD/MADE/MATE. **Candidate related-work cite (representative of the classical line)** — polish, not novelty threat. |
| [57] | Liu et al., *MISO-V* (IV'21) | Exploits **overlapping observations from multiple vehicles** to verify semantic correctness of CPM data (multiple independent sources over V2X). | READ — **no pre-empt.** Conceptually nearest of the batch ("multiple sources cross-verify") but classical/rule-based, object-level, AP-style, **no closed-loop navigation, no noise, no adaptive attacker.** Family member, not a pre-emption. Same polish-cite bucket as [23]. |
| [39] | Hadded et al., *Security attacks impact for collective-perception roadside assistance* (IWCMC'20) | **Attack-impact study**: builds attack models, measures effect on on-ramp-merging control via simulation. | READ — **no pre-empt.** Attack-side only, classical merging control, **no defense/trust, no learned policy.** Out of family. |
| [55] | Jinshan Liu & Park, *"Seeing is Not Always Believing"* (TDSC'21) | Detects perception-error attacks via **LIFE = LiDAR+Image fusion on a single AV**. | READ — **no pre-empt.** **Single-vehicle** multi-sensor fusion; not cooperative/multi-agent trust. Out of family (same bracket as our 3D-TC2/ADoPT single-vehicle line). |

**Running note:** [23]+[57] flagged as *optional* related-work citations (classical CPM-MDS representatives) — decide at related-work polish; neither affects the novelty claim.

**Batch 2 (2026-07-26) — platoon / CACC / BSM communication-layer security:**
| # | Ref | Abstract gist | Verdict |
|---|-----|---------------|---------|
| [26] | Boddupalli et al., *REPLACE* (ITSC'21) | ML-based real-time defense augmenting a **platoon controller** (CACC) against V2V attacks that corrupt the *preceding-vehicle position* broadcast. | READ — **no pre-empt.** Control-layer platoon resiliency on a scalar state channel; **no collaborative perception, no obstacle fabrication, no learned nav policy.** Out of family. |
| [27] | Boddupalli & Ray, *REDEM* (IFIP-IoT'19) | Real-time detection+mitigation of communication attacks in **CACC**; app-integrated resiliency. | READ — **no pre-empt.** Same control-layer comm-security family as REPLACE. Out. |
| [46] | Kim & Kim, *V2V message-content plausibility check for platoons* (Sensors'19) | Classical **BSM plausibility** validation via sensor-fusion / behavior / comm-constraint checks. | READ — **no pre-empt.** Message-plausibility MDS on safety beacons (position/speed), not shared *obstacle* perception; classical, no navigation/noise/adaptive. Out (classical-MDS bracket). |
| [88] | Zhao et al., *FDI detection via cloud sandboxing* (T-ITS'22) | Isolates/evaluates exchanged CAV data in a **control-framework sandbox** to detect false-data-injection affecting vehicle control. | READ — **no pre-empt.** Control-layer FDI detection; not perception fusion/trust. Out. |

**Batch 3 (2026-07-26) — benign CP fusion + single-vehicle ghost defense + V2X data-correction:**
| # | Ref | Abstract gist | Verdict |
|---|-----|---------------|---------|
| [37] | Godoy et al., *Grid-Based Framework for Collective Perception* (Sensors'21) | Benign **occupancy-grid fusion** of on-board sensors + CPM messages (occupied/free/uncertain + confidence). | READ — **no pre-empt.** Benign CP architecture, no adversary/trust. Out. |
| [50] | Li, Tsukada et al., *Multi-Vehicle Cooperative Local Mapping via OGM merging* (T-ITS'14) | Benign **occupancy-grid-map merging** + indirect V2V relative-pose estimation for cooperative mapping. | READ — **no pre-empt.** Benign classical cooperative mapping, no adversary. Out. |
| [89] | Zhao et al., *OCEAN — Collaborative V2X Data Correction* (T-Reliability'22) | Rationality + **Q-learning** to detect/correct erroneous V2X data from defective sensors **or selfish behavior** (~80% detect). | READ — **no pre-empt.** Nearest of batch (handles "selfish" senders) but operates on **V2X message attributes** (BSM-style), not shared-obstacle perception fusion; no learned nav, no ranging-noise regime, no adaptive attacker. Out (MDS-adjacent, optional cite). |
| [41] | Hau et al., *Shadow-Catcher* (ESORICS'21) | **Single-vehicle** ghost-object detection via LiDAR **shadow analysis** (large + small ghosts). | READ — **no pre-empt.** Single-vehicle physical-spoofing defense; belongs to our 3D-TC2/ADoPT single-vehicle bracket. Out. |

**Batch 4 (2026-07-26) — single-vehicle spoof-detection, V2X-standards survey, benign CP deployments:**
| # | Ref | Abstract gist | Verdict |
|---|-----|---------------|---------|
| [22] | Alheeti et al., *LiDAR Spoofing Attack Detection in AVs* (ICCE'22, 2pp) | **Single-vehicle** LiDAR spoofing detection (short paper). | READ — **no pre-empt.** Single-vehicle. Out. |
| [80] | Yoshizawa & Preneel, *Survey of Security Aspect of V2X Standards* (CSCN'19) | **Survey** of V2X communication-standard security. | READ — **no pre-empt.** Standards-security survey; not perception. Out. |
| [38] | Günther et al., *Realizing Collective Perception in a Vehicle* (VNC'16) | Benign **CPM implementation** (perceive beyond own range via others' sensors). | READ — **no pre-empt.** Benign CP-messaging arch, no adversary. Out. |
| [86] | Zhang et al., *Roadside Cooperative Perception System* (TRR'22) | Benign **roadside/infra CP deployment** (fisheye/thermal/radar, edge-cloud). | READ — **no pre-empt.** Benign infra CP system. Out. |

**Batch 5 (2026-07-26) — out-by-identity bulk: detector/segmentation backbones, GPS-spoofing, comm-auth, networking, surveys, methodology.** All abstract-checked; none is multi-agent collaborative-perception *trust/attack* work — each is fixed by its category and no abstract reclassifies it. Grouped:
| Bucket | Refs | Verdict |
|--------|------|---------|
| Detector / segmentation / tracking backbones | [35] Douillard 3D-seg, [47] Ku **AVOD**, [59] Mohan **EfficientPS**, [75] Weng **AB3DMOT**, [76] Wu **SqueezeSeg**, [77] Xu **CoBEVT** (benign CP-BEV-seg), [82] Yuan **FPV-RCNN** (benign feat-fusion), [83] Zermas 3D-point-seg | READ — no pre-empt (perception/detection building blocks; NO-ABS-class in spirit) |
| Pure methodology / math | [24] Avis convex-hull, [28] Canilho k-means-FPGA, [36] Fischler **RANSAC** | READ — no pre-empt (algorithmic tooling) |
| GPS spoofing (attack/defense, single-vehicle localization) | [56] Liu **Stars-can-tell**, [63] Ranganathan **SPREE**, [74] Warner GPS-countermeasures | READ — no pre-empt (GPS/localization layer, not CP fusion) |
| Comm security / authentication | [25] Baee IEEE-1609.2 broadcast-auth, [42] Hu **CVShield** (TEE), [43] Hu **Gatekeeper** (broadcast-auth) | READ — no pre-empt (crypto/comm layer, not perception trust) |
| Networking / systems | [48] Kumar **CarSpeak**, [60] Narayanan 5G-in-the-wild, [70] Toghi cellular-V2X-congestion, [64] Schiegg CP-802.11p-perf-eval | READ — no pre-empt (network performance) |
| Surveys / misc | [21] Alaba LiDAR-3D-det survey, [52] Li LiDAR-for-AD survey, [53] Lin arch-implications-of-AD, [61] Pham CAV-security survey, [45] Kim traj-pred-occupancy-grid (downstream predictor) | READ — no pre-empt (surveys / downstream prediction) |
| Already covered | [31] Chen CP-env-for-traffic-ops → **PRIOR** (abstract-read in SECOND_ORDER_ABSTRACT_PASS, "benign CP for signal control") | PRIOR |

### 1e. Batch 5 INDIVIDUALIZED (mandate B — Srinivasa asked for a real abstract on every ref, 2026-07-26)
Each abstract fetched individually; verdicts confirm the identity-classification above.
| # | Ref | Abstract gist (fetched) | Verdict |
|---|-----|-------------------------|---------|
| [36] | Fischler & Bolles, RANSAC (CACM 1981) | Robust model-fitting paradigm tolerant of gross-error data; landmark localization. | READ — no pre-empt (estimation math). |
| [47] | Ku et al., AVOD (IROS'18) | LiDAR+RGB two-stage 3D detector (RPN + detector). | READ — no pre-empt (single-vehicle detector). |
| [59] | Mohan & Valada, EfficientPS (IJCV'21) | Efficient panoptic-segmentation architecture. | READ — no pre-empt (segmentation backbone). |
| [76] | Wu et al., SqueezeSeg (ICRA'18) | CNN+CRF real-time road-object segmentation from LiDAR. | READ — no pre-empt (segmentation backbone). |
| [35] | Douillard et al., 3D LiDAR-cloud segmentation (ICRA'11) | Set of point-cloud segmentation methods. | READ — no pre-empt (segmentation method). |
| [75] | Weng et al., AB3DMOT (IROS'20) | Real-time 3D MOT: Kalman + Hungarian; new metrics. | READ — no pre-empt (tracking baseline). |
| [82] | Yuan et al., FPV-RCNN (RA-L'22) | **Benign** cooperative detection: keypoint feature fusion, CPM compression, **localization-error correction via maximum-consensus**. | READ — no pre-empt. Benign CP-fusion w/ consensus pose-correction (same *benign-robustness* family as Vadivelu/Song/Lu); no adversary/trust. |
| [83] | Zermas et al., fast 3D point-cloud segmentation (ICRA'17) | Iterative ground extraction + non-ground clustering, real-time. | READ — no pre-empt (segmentation method). |
| [24] | Avis & Bremner, convex-hull algorithms (SoCG'95) | Complexity analysis of convex-hull algorithms. | READ — no pre-empt (geometry math). |
| [56] | Liu et al., Stars-Can-Tell (USENIX Sec'21) | GPS-spoofing detection via angle-of-arrival vs satellite constellation, off-the-shelf chipset. | READ — no pre-empt (GPS/localization layer). |
| [63] | Ranganathan et al., SPREE (MobiCom'16) | Spoofing-resistant GPS receiver (auxiliary-peak tracking). | READ — no pre-empt (GPS receiver). |
| [74] | Warner & Johnston, GPS-spoofing countermeasures (2003) | Low-cost retrofit GPS-spoofing countermeasures. | READ — no pre-empt (GPS layer). |
| [25] | Baee et al., IEEE-1609.2 broadcast-auth efficiency (TVT'19) | Benchmarks 1609.2 crypto primitives for low-latency safety-message authentication. | READ — no pre-empt (crypto/comm layer). |
| [42] | Hu et al., CVShield (AutoSec'20) | **Prevents** falsified sensor-data broadcast via ARM-TrustZone TEE (relocates sensor code into TEE). | READ — no pre-empt. Hardware-root-of-trust *prevention* assuming trusted HW; not perception-consistency detection of a lying peer; no fusion/trust over shared obstacles. Out. |
| [43] | Hu et al., Gatekeeper (AsiaCCS'22) | Gateway-based **broadcast authentication** for in-vehicle Automotive Ethernet. | READ — no pre-empt (in-vehicle network crypto). |
| [48] | Kumar et al., CarSpeak (SIGCOMM'12) | Content-centric **networking** to query road-region sensor data; MAC changes; reduces collision prob. | READ — no pre-empt. Benign comm/networking arch for sensor sharing; no trust/adversary. Out. |
| [60] | Narayanan et al., 5G-in-the-wild (SIGCOMM'21) | Measurement study of commercial 5G performance/power/QoE. | READ — no pre-empt (network measurement). |
| [70] | Toghi et al., Multiple Access in C-V2X (VNC'18) | C-V2X resource-allocation/MAC performance under congestion. | READ — no pre-empt (network MAC analysis). |
| [64] | Schiegg et al., CP-service perf-eval in 802.11p (WCNC'20) | Analytical performance of the collective-perception *service* on the wireless channel. | READ — no pre-empt (CP network-service perf, not fusion/trust). |
| [21] | Alaba & Ball, LiDAR-3D-detection survey (Sensors'22) | Survey of DL-based LiDAR 3D object detection. | READ — no pre-empt (survey). |
| [52] | Li & Ibanez-Guzman, LiDAR-for-AD (SPM'20) | Review of automotive LiDAR principles/challenges/trends. | READ — no pre-empt (survey). |
| [53] | Lin et al., Architectural Implications of AD (ASPLOS'18) | Computing-architecture constraints/acceleration for AD. | READ — no pre-empt (systems/hardware). |
| [61] | Pham & Xiong, CAV security survey (Comp&Sec'21) | Survey of attacks/defenses across CAV components. | READ — no pre-empt (survey; useful pointer, not a method). |
| [45] | Kim et al., trajectory prediction over occupancy grid (ITSC'17) | LSTM **trajectory prediction** of surrounding vehicles. | READ — no pre-empt (downstream prediction). |
| [28] | Canilho et al., k-means on FPGA (FPL'16) | Many-core FPGA architecture for K-means. | READ — no pre-empt (hardware accel). |

### CAD bibliography — SWEEP COMPLETE (2026-07-26) — MANDATE B (every ref individually abstract-read)
All 91 refs accounted for. Per Srinivasa's mandate B, **every non-URL reference had its abstract fetched
and read individually** (batches 1–4 = CP-security subset; batch 5a–5e = every backbone/math/GPS/comm/
networking/survey ref, no identity-only shortcuts). Only the 22 pure website/standard/product/dataset
entries [1]–[20],[79],[81] have no abstract to read (NO-ABS). **Zero pre-emptions across all 91.**
Only fallout = *optional* related-work cites: **Ambrosin [23]**, **MISO-V [57]** (classical CPM
misbehaviour-detection representatives), weaker **OCEAN [89]** — all decide-at-polish, none novelty-
affecting. ✅ **AUDITED & APPROVED by Srinivasa 2026-07-26** — he skimmed the security-relevant subset
(batches 1–4, 16 refs) and confirmed the "no pre-empt" verdicts; batch-5 identity-outs not contested.
