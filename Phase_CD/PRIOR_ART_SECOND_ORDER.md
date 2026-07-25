# Second-order prior-art sweep (2026-07-17)

**What this is:** a systematic sweep of the related-work/background sections of every paper we
have fully audited (TruPercept, MATE, AerialTrust, GCP, PRBI, CAD), looking for works THEY cite
that could (a) pre-empt one of OUR novelty claims ("no prior work…", "none of this line…") or
(b) be a citation a reviewer from that community would expect. Wording-accuracy audits only
apply to papers WE cite; this sweep is novelty defense.

**Triage rule:** a second-order paper matters only if it touches our claimed novelties —
closed-loop navigation metric, destructive-filter-under-noise, camouflage-within-noise-
tolerance, cross-agent temporal offset-bias test, no-honest-majority operation, stealth/harm
bind. Feature-fusion CP defenses scored by AP do not pre-empt these; they at most deserve a
survey line.

---

## TRIAGE RESULTS — 8 arXiv-visible second-order papers (2026-07-19)

Method: each paper fetched, mechanism-grep run **unconditionally** (temporal / cross-agent
offset-bias / pairwise-per-neighbour-trust / running-mean / zero-mean-cancellation) + honest-
majority test + closed-loop-navigation test + ranging-noise test. Defense-cluster members also
had their method described. Evidence (verbatim quotes) captured in session transcript. **Two
papers (LUCIA, Pretend Benign) are bot-blocked (USENIX/CVF/ResearchGate all 403 the fetcher) —
body-grep NOT performed; classified from abstract only; body-grep owed to a manual PDF pull.**
IDs: ROBOSAC 2303.09495 · Stealthy-Fab 2605.01301 · CP-Guard 2412.12000 · CP-Guard+ 2502.07807 ·
LUCIA=USENIX-Sec-2025 (wang-chenyi) · Tu 2101.06560 · Pretend-Benign ICCV-2025 (Lin) ·
Hallyburton 2403.16956.

| # | paper | verdict | why / grep result |
|---|---|---|---|
| A | **ROBOSAC** (ICCV'23) | **CITE → full dossier owed** | Consensus sampling, feature-level, AP-scored, no noise model. GREP: HAS a temporal variant but it compares *"the current output with the previous output"* (scene vs its OWN PAST = PRBI/3D-TC2 reference signal, NOT cross-agent offset) → no pre-emption of our cross-agent test. Requires an attacker-free subset (*"maximum number of attacker-free collaborators…"*) → **reinforces our no-honest-majority contrast.** Already approved to cite. |
| B | **Stealthy-Fab→Unsafe-Driving** (2605.01301) | **CITE-CANDIDATE → full dossier owed; novelty claim SURVIVES** | Attack (PosePert) + defense (PoseGuard). Measures *"detection errors"* + scripted *"hard braking, in up to 50% of scenarios"* on a **hand-designed modular stack (AB3DMOT + GRIP++), single-ego, NOT a learned end-to-end policy, no swarm.** PoseGuard = spatial object-level L1 between agents; GREP temporal/offset/pairwise = NONE. **Closest challenger to our "closed-loop learned navigation, success-not-detection" claim yet** → cite + tighten wording to make "learned policy / success metric" explicit vs their "modular pipeline + hard-braking case study." |
| C | **CP-Guard** (2412.12000) | **NO-CITE (survey-line optional)** | Feature-level consensus (PASAC/CCLoss), mIoU-scored, no noise, GREP temporal/offset/running-mean = NONE. Same family as MADE/GCP (already cited). No pre-emption. |
| D | **CP-Guard+** (2502.07807) | **NO-CITE (survey-line optional)** | Feature-level contrastive (DCCLoss); residual F_i−F_j is a FEATURE difference (not geometric, single-frame); AP/TPR-scored, no noise. No pre-emption. |
| E | **LUCIA / "From Threat to Trust"** (USENIX Sec'25) | **CITE-CANDIDATE (reviewer-expected); ⚠ body-grep OWED (403)** | SOMBRA = 99% object-removal attack; LUCIA = *"trustworthiness-aware attention mechanism"* = **attention/feature-level** (structurally cannot hold our geometric cross-agent temporal-offset test). Same family as ROBOSAC/CP-Guard/MADE. Recent high-profile USENIX; already one of TrustFlip's 4 SOTA defenses (we cite TrustFlip). Recommend citing in the defense-family sentence. **Body inaccessible via WebFetch → Srinivasa to pull `usenixsecurity25-wang-chenyi.pdf` for the confirming grep before we rely on it.** |
| F | **Tu et al.** (ICCV'21, 2101.06560) | **CITE (one-line, no dossier)** | Seminal feature-level CP attack + adversarial-training defense. Quote for our benign-count contrast: *"as the number of benign agents increase, attacks become significantly weaker."* Named by CAD+GCP+MADE → a CP-security reviewer expects the origin cite in our attack paragraph. AP-scored, no navigation. No pre-emption. |
| G | **Pretend Benign** (ICCV'25, Lin) | **NO-CITE / cite-optional near TrustFlip; ⚠ body-grep OWED (403)** | Feature-level stealthy **defense-aware** attack; evades consensus by *maintaining* consensus (MAPG); AP-scored on OPV2V/V2XSet, no navigation, no defense of its own. Same neighbourhood as TrustFlip (already cited). No pre-emption. Body inaccessible via WebFetch → optional manual pull. |
| H | **Hallyburton & Pajic** (CDC'24, 2403.16956) | **CITE-OPTIONAL (MATE-line lineage anchor)** | Track/object-level Bayesian trust (*"mapping sensor measurements to trust pseudomeasurements"*); the **theory paper underlying MATE**, which we already cite. GREP cross-agent-offset/pairwise = none surfaced (abstract-level). Adding it = thoroughness for the MATE line; decide at polish. |

**Net novelty check: NONE of the 8 pre-empts a novelty claim.** All feature-level/AP-scored or
attack-only or single-ego modular-stack; none models the ranging-noise-vs-tolerance regime, none
runs a closed-loop LEARNED navigation success metric, none formalizes the cross-agent temporal
offset-bias statistic. Two structural reinforcements found FOR us: ROBOSAC needs an attacker-free
subset, Tu et al. shows attack weakens with more benign agents — both feed our no-honest-majority
contrast.

**Decisions needing Srinivasa (manuscript edits — not made yet):**
1. Add **ROBOSAC** (full dossier first) + **LUCIA** to the feature-fusion / defense-family sentence.
2. Add **Tu et al.** one-line to the attack paragraph (currently enters at CAD).
3. Cite **Stealthy-Fab** + tighten the "closed-loop learned navigation task" wording (§ combination claim, related.tex ~155-162).
4. Optional: **Hallyburton** on the MATE-line cite; **Pretend Benign** near TrustFlip.

**Owed follow-ups:** ROBOSAC full dossier · Stealthy-Fab full dossier · LUCIA + Pretend-Benign
body-grep from manual PDF pulls (WebFetch 403-blocked). Bibliography scans of ROBOSAC & Stealthy-Fab
still to run (per the standing per-audit scan rule).

---

## ACTION ITEMS

### 1. MADE — ✅ **RESOLVED 2026-07-17: cited + fully audited**
"Malicious Agent Detection for Robust Multi-Agent Collaborative Perception" (arXiv:2310.11901).
Was the missing must-cite (named by GCP §II.C, attacked by TrustFlip, = PRBI's [37]). Done:
full 8-page read → `made2024` added to refs.bib (venue TODO-VERIFY via arXiv Comments) →
cited in the feature-fusion sentence + the On-baseline-comparison list of related.tex →
dossier `REFERENCE_EVIDENCE_MADE.md` (awaiting Srinivasa) → full 44-ref scan below.
⚠ Wording rule learned from the read: MADE is EGO-REFERENCED per-agent inspection (no
majority, no voting) — never use it as a majority-agreement counter-example; our remaining
separations are threat class (feature perturbation vs geometric fabrication), learned+
data-hungry vs hand-designed closed-form, no noise regime, no navigation loop.

### 2. MDS (Ambrosin et al., ITSC 2019) — **MEDIUM: skim to decide cite/no-cite**
Found in CAD §6.4.4: *"each CAV evaluates the consistency between the local occupancy map and
final perception results, and also merges anomaly detection results from multiple CAVs by
majority voting."* Object-sharing V2X + verify-against-own-sensing + majority voting — the
closest second-order neighbour to our family, and it PREdates TruPercept's arXiv v1 (2019).
Risk if ignored: a reviewer says our "second, closer line" survey (TruPercept→MATE→aerial)
misses its earliest member. Mitigation: CAD reports MDS's majority voting is defeated by
victim-targeted lying and its spatial check is local-map-only (TPR 9–15% below CAD) — so it
does not pre-empt anything we claim; at most it earns a mention. IEEE ITSC paper, likely
paywalled — Srinivasa to pull via institute access → `Research paper/MDS.pdf`.

### 3. ROBOSAC (ICCV 2023) / CP-Guard / CP-Guard+ — **LOW-MEDIUM: decide during CoDynTrust audit**
Named by GCP §II.C; PRBI's numbered clusters RESOLVED 2026-07-17 and are exactly this family:
PRBI [16] = ROBOSAC (Li et al., *"Among Us: Adversarially Robust Collaborative Perception by
Consensus"*, ICCV 2023), [9] = CP-Guard, [8] = CP-Guard+, [37] = MADE, [25] = GCP, [35] = CAD —
so PRBI's related work adds NOTHING beyond GCP's list. Our sentence "Other defenses for
feature-fusion collaborative perception include CoDynTrust… and GCP…" says *include*
(non-exhaustive), so nothing is inaccurate. But ROBOSAC is the best-known of that family;
consider adding it to that one sentence when the CoDynTrust audit touches it anyway. Bonus if
cited: ROBOSAC's consensus sampling NEEDS a benign majority — one more datapoint for our
no-honest-majority contrast. No pre-emption risk (feature-level, AP-scored, no noise regime,
no navigation).

### 4. MISO-V (Liu et al., IEEE IV 2021) — **MEDIUM: same skim bucket as MDS**
Surfaced when MATE's numbered refs were resolved (MATE [28]): *"MISO-V: Misbehavior detection
for collective perception services in vehicular communications"* — misbehavior detection on
Collective Perception Messages, i.e. OBJECT-level claims, same Intel-adjacent line as MDS
(MATE cites both [2]=MDS and [28]=MISO-V as occupancy-grid/object consistency checking; CAD
cites it as [57] "cross-validation with local sensor"). Same risk/mitigation as MDS: early
member of the object-claim-verification family our survey enters at TruPercept. Skim with MDS
and make one decision for the pair. IEEE IV 2021, likely paywalled → institute access →
`Research paper/MISO_V.pdf`.

### 5. Judgment-call one-liners (LOW — none pre-empt, all are reviewer-expectation calls)
- **van der Heijden et al., "Survey on Misbehavior Detection in Cooperative Intelligent
  Transportation Systems"** (IEEE COMST) — MATE [43], its anchor for the whole VANET-MBD
  lineage. Citing this ONE survey would cover every classical MBD a reviewer could list
  (Golle'04, Bißmeyer'12, REPLACE/REDEM/…) in a single stroke. Cheap insurance; decide at
  final related-work polish.
- **Hallyburton & Pajic, "Bayesian Methods for Trust in Collaborative Multi-Agent Autonomy"
  (CDC 2024)** — AerialTrust [16], the same authors' theory paper both MATE and AerialTrust
  build on ("as we previously proposed in [16]"). We cite "the MATE line" with two refs; adding
  the lineage anchor is optional thoroughness. Decide at polish.
- **Tu et al., "Adversarial Attacks on Multi-Agent Communication" (ICCV 2021)** — named by BOTH
  CAD (§2, first attack on intermediate-fusion CP) and GCP (§II.B) as the attack-side seminal
  work. Our attack paragraph currently enters at CAD; a CP-security reviewer may expect the
  Tu et al. origin. One-line candidate for the same sentence that cites CAD's attacks.

---

## FULL-BIBLIOGRAPHY TITLE SCAN (302 refs across all 6 papers, 2026-07-17)
Srinivasa challenged the prose-level sweep ("are you sure?") — correctly. A keyword scan over
every reference entry in all six bibliographies surfaced these ADDITIONAL candidates the
related-work prose had hidden:

### 6. Cavorsi et al., "Exploiting Trust for Resilient Hypothesis Testing with Malicious
Robots" (IEEE T-RO 2024) — **MEDIUM-HIGH: the Gil-line multi-robot trust work**
Found in AerialTrust [7]. This is the Stephanie Gil group's trust-in-multi-robot-systems line —
**the nearest community to our RAS submission**, and our "Byzantine resilience in multi-robot
systems" paragraph currently cites only SwarmRaft + conformity games. A robotics reviewer may
well expect this line. Differentiation is clean once cited: their trust values originate from
the PHYSICAL WIRELESS CHANNEL (fingerprints/observations feeding hypothesis tests on malicious
robots), not from verifying perception content against own sensing — orthogonal mechanism, no
pre-emption. Action: skim + likely add 1–2 lines to the Byzantine-robots paragraph.

### 7. Obst et al., "Multi-sensor data fusion for checking plausibility of V2V communications
by vision-based multiple-object tracking" (IEEE VNC 2014) — **MEDIUM**
Found in TruPercept [4] (TruPercept builds on it directly). Arguably the EARLIEST
"verify-a-peer's-V2V-claims-against-own-sensing" work — the primitive our family survey
attributes to TruPercept (2019) onward. If a reviewer knows it, our "second, closer line"
opening looks late by five years. Skim bucket with MDS/MISO-V.

### 8. Allig et al., "Trustworthiness estimation of entities within collective perception"
(IEEE VNC 2019) + Tsukada et al., "Misbehavior detection using collective perception under
privacy considerations" (IEEE CCNC 2022) — **LOW-MEDIUM**
Found in MATE [1] and [42]. Both are object-level collective-perception trust/misbehavior
works — same bucket as MDS/MISO-V. Decide as a group after the MDS/MISO-V skim: either the
survey line covers the whole CPM-misbehavior cluster, or one representative gets named.

### 9. LUCIA (Wang et al., "From Threat to Trust: Exploiting Attention Mechanisms for
Attacks and Defenses in Cooperative Perception") — **MEDIUM: promote from the item-3 cluster**
Found in TrustFlip's bibliography (2026-07-17), where it is treated as one of the FOUR SOTA
defenses TrustFlip is evaluated against (CAD, MATE, LUCIA, MADE). ⚠ **Process miss disclosed:**
this same paper was PRBI's ref [28] and sat unpromoted in the PRBI keyword-hit list — my
triage error, corrected here. Mechanism: attention-level trust modulation inside feature-fusion
CP → same family as ROBOSAC/CP-Guard/MADE (item 3), same differentiation (feature-level,
AP-scored, no noise regime, no navigation). Action: fold into the item-3 decision — if that
family gets a named example beyond GCP, LUCIA and ROBOSAC are the two candidates.

### 10. "Pretend Benign" (Lin et al.) — **LOW-MEDIUM: abstract triage only**
Found in TrustFlip's bibliography: a stealthy attack exploiting vulnerabilities in CP
defenses — i.e. a DEFENSE-AWARE attacker, like TrustFlip. Check the abstract for overlap with
our adaptive-attacker framing (our stealth/harm bind). Expected outcome: feature-level attack
on vehicular CP, no navigation loop, no noise regime → cite-optional in the TrustFlip
sentence's neighbourhood, no pre-emption.

### 11. "From Stealthy Data Fabrication to Unsafe Driving: Realistic Scenario Attacks on
Collaborative Perception" (Zhang, Zhang & Mao, arXiv) — **MEDIUM: verify it does not weaken
our closed-loop phrasing**
Found in TrustFlip's bibliography; CAD-author line (attack side). The title suggests
DRIVING-LEVEL attack outcomes — must check it against our claim "no prior work evaluates
fabricated-obstacle attacks on collaborative perception *inside a closed-loop learned
navigation task* (success, not detection accuracy, as the end metric)". Expected outcome
(verify from abstract): attack-only case studies on a driving stack (like CAD's Apollo
demos) — attack demonstrations with driving consequences are NOT a defense evaluated by a
closed-loop success metric, so the claim survives, but the wording "to our knowledge no
prior work evaluates … inside a closed-loop learned navigation task" should be re-read
against it before submission.

### Scanned and NOT promoted (title-level, with reasons)
- Grigoropoulos 2020 (BFT for centrally coordinated UAV missions) — consensus-layer BFT,
  covered by our SwarmRaft framing; central coordinator, unlike our infrastructure-free claim.
- Cheng 2021 (trust-aware control for ITS) — trust values assumed/oracle-fed into control, not
  generated from perception verification; no fabrication threat model.
- Raya 2008 (data-centric trust, INFOCOM) / Lo & Tsai 2007 (illusion attack) / Monteuuis 2018
  (implausible-dimension detector) — classical VANET message-level line, wholesale-covered by
  the van der Heijden survey one-liner (item 5).
- Hadded 2020 (attack-impact study on collective perception roadside assistance) — impact
  study on late-fusion CPM, no defense, no navigation loop.
- Jia et al. (attack on MOT), Hau et al. Shadow-Catcher, PLA-LiDAR, Cao/Sun physical LiDAR
  spoofing cluster — single-vehicle sensor attacks; our 3D-TC2/ADoPT paragraph is the entry
  point for that literature.
- Pajic-group attack-resilient state estimation (Automatica/TCNS) — control-theoretic state
  estimation under sensor attack; different layer (state, not perception content); the
  consensus paragraph's scope statement already draws this boundary.
- Everything else hit by the keyword scan = adversarial-ML classics (PGD/C&W/BIM), DDoS
  detection, GPS spoofing, V2X standards/PKI, WSN trust surveys — out of family.

## REVIEWED AND NOT NEEDED (with reasons)

| SwarmRaft (full 43-ref title scan, 2026-07-17) | blockchain-consensus classics (PBFT, Tendermint, Exonum, Ouroboros, Raft, SoKs); DTPBFT (consensus-layer blockchain trust for UAV swarms); VANET security/trust-management review; GNSS-spoofing impact study; benign fault-tolerance (predictive, self-healing, cooperative navigation) | NO new candidates — all consensus/blockchain/message-layer or benign faults; our "protect state agreement or collective decision-making" boundary covers the cluster. VANET trust review niche already covered by the van der Heijden judgment call (item 5) |

| TrustFlip (full 58-ref title scan, 2026-07-17) | CP architectures/datasets/backbones; physical adversarial-object line (Cao/Tu/Zhu — single-vehicle); CP-FREEZER (latency/availability attack); CAD-author fabrication follow-ups; differentiable-rendering utilities | **THREE promoted → items 9–11** (LUCIA; "Pretend Benign"; "From Stealthy Data Fabrication to Unsafe Driving"); everything else out of family |

| 3D-TC2 (full 14-ref title scan, 2026-07-17) | LiDAR spoofing attacks (Petit/Shin/Cao/Sun); single-vehicle ghost defenses (Shadow-Catcher, ORA, MSF-ADV, CARLO/SVF); WSN false-data injection; AdVIT video temporal consistency; detectors/datasets | NO new candidates — all single-vehicle sensor-attack line, bracketed by our 3D-TC2/ADoPT paragraph |

| ADoPT (full 37-ref title scan, 2026-07-17) | single-vehicle attack/defense line (CARLO, Shadow-Catcher, LOP/"Wraith", PercepGuard, AdvIT, Liu&Park TDSC'21); scene-flow/registration methodology; detectors/datasets; Cooper + EMP (benign CP architectures) | NO new candidates — single-vehicle or benign-CP plumbing; no trust/defense family members |

| Conformity (full 15-ref title scan, 2026-07-17) | authors' own IoV/6G papers; blockchain VANET trust mgmt; UAV-swarm security survey (ACM CSUR 2024 — optional background, LOW); authentication/anti-jamming/DoS-consensus; Byzantine formation-tracking (control layer); replicator-equation classic | NO new candidates — comm/control/consensus layers, covered by our boundary sentence |

| MADE (full 44-ref title scan, 2026-07-17) | ROBOSAC [13] = item 3; CAD [41] = already cited; Tu et al. 2021 [32] = item 5 (now named by CAD+GCP+MADE — three namings strengthen the one-line-cite case); CP architectures (Where2comm, DiscoNet, V2VNet, V2X-ViT, When2com); datasets; adversarial-ML classics (PGD, patches); statistics classics (BH, conformal p-values, MAD, Hungarian); U-Net; policy pointers | NO new candidates — everything family-relevant already tracked |

| Source paper | Works its related-work names | Verdict |
|---|---|---|
| CAD §2 | CARLO (free-space plausibility, single vehicle), LIFE (camera-LiDAR temporal match) | NO — single-vehicle physical-spoofing defenses; our manuscript's temporal-spoofing paragraph already uses 3D-TC2/ADoPT as that line's representatives, and CAD itself shows both are bypassed by physics-conforming fabrication |
| CAD §2 | REPLACE / REDEM / MISO-V / Kim&Kim (V2V message plausibility) | NO — GPS/OBU message-level checks, not perception content; CAD: *"existing works assume the systems to share simple GPS/OBU data"* |
| GCP §II.B | CoBEVFlow, CoAlign | NO — asynchrony/pose-error robustness (benign faults), not adversarial |
| PRBI §2 | sampling-based [9,16,35] / classifier-based [8,25,37] defenses | Same family as ROBOSAC/CP-Guard above — covered by item 3 |
| TruPercept §II | [21] Chen et al. 2010 (VANET message-propagation trust); [22] Mass & Shehory (distributed trust in open MAS) — RESOLVED 2026-07-17 | NO — classical message-level / agent-society trust, no perception content; TruPercept itself is our cited representative of the step from messages to perception content |
| MATE §2 | RESOLVED 2026-07-17: [44] Wang et al. 2006 (Bayesian trust construction, agent tech); [17] Golle et al. 2004 (detecting malicious data in VANETs — the ur-paper, parsimony/minimal-colluding-set); [8] Bißmeyer et al. 2012 (plausibility checks + particle filters); [2] = MDS (action item 2!); [28] = MISO-V (action item 4!); [47] = CAD (already cited) | NO for [44,17,8] individually — the VANET-MBD lineage MATE positions itself against (*"MBDs require that ownship data is absolutely trusted"*); covered wholesale by the [43] survey one-liner (item 5) if we want it. [2] and [28] promoted to action items. |
| AerialTrust §2 | WSN trust surveys; oracle-provided-trust decision frameworks | NO — trust values assumed given (no generation from sensor data), or classical MTT integrity; AerialTrust itself states the gap we inherit from them. Its [16] RESOLVED = the authors' CDC 2024 lineage paper → promoted to item 5. |

**None of the above pre-empts our novelty claims** — all operate on detection/track/message
metrics, none models the ranging-noise-vs-tolerance regime, none measures navigation, none
formalizes camouflage-within-noise or the temporal offset-bias statistic.

## Negative result: non-keyword title review (2026-07-17)
To close the "bland title" blind spot, every reference NOT hit by the keyword scan (~150 of
302) was reviewed by title manually. Result: **no additional family members.** The non-hits
are CP architectures (Where2comm/When2com/DiscoNet/V2VNet/CoBEVT…), datasets (OPV2V, V2X-Sim,
DAIR-V2X, nuScenes), detection backbones (PointPillars/VoxelNet/PointRCNN), MTT/DDF classics
(Bar-Shalom, Blackman, covariance intersection), simulators/tools (CARLA, SUMO, ROS, AVstack),
V2X standards/industry pages, and method utilities (RANSAC, convex hulls, Jaccard, FDR).
Borderline calls, rejected with reasons: TruPercept [20] (reputation-based announcement scheme
— message-level reputation, survey-covered); TruPercept [9] (CP for vehicle control — benign
CP, no adversary); CAD [89] (V2X data correction — benign network errors); GCP [31]
(Stuxnet-style AV malware propagation model — malware spread, not perception trust);
MATE [36] (rumor-source identification — DDF double-counting context).

## Paywalled-literature blind spot (Srinivasa's catch, 2026-07-17) — IEEE Xplore session REQUIRED
Observation: every 2025–26 family member was found by keyword search (arXiv-visible full
text); every pre-2022 family member (Obst'14, MDS'19, Allig'19, MISO-V'21) was found ONLY via
bibliography mining — none surfaced in keyword sweeps. Cause: the VANET/V2X
misbehavior-detection shelf lives in IEEE conferences (ITSC/IV/VNC/CCNC) predating the
preprint norm — abstract-only visibility ⇒ under-sampled by our sweeps. Bibliography mining
compensates only for what our six audited papers chose to cite.
**Action (Srinivasa, from college network, one session):**
1. IEEE Xplore searches (titles/abstracts): "misbehavior detection"+"collective perception" ·
   trust+"cooperative perception" · plausibility+V2X · "false object"+V2X · trust+"multi-robot"
   (T-RO/ICRA side).
2. In Xplore, open "Cited by" for MDS, MISO-V, Obst — forward citations within IEEE reveal
   the non-arXiv members of the family.
3. Paste result lists to Claude for triage against our novelty claims (same protocol as this
   log).
Risk assessment: bounded — 2025–26 near-neighbours would be on arXiv (current norm); the
IEEE-only shelf is older work that can add survey citations but was checked (via the audited
family) not to measure navigation, noise-vs-lie regimes, or temporal offset statistics.
Bounded ≠ zero ⇒ run the session before submission, alongside the Scholar forward sweep.

## Honest limits of this sweep (what "are we sure?" still cannot cover)
1. **Backward-looking only.** Bibliographies cannot contain work published AFTER these six
   papers (mid-2025 onward). Our 2025–2026 must-cites (CoDynTrust, PRBI, TrustFlip, GCP…)
   came from fresh searches, not bibliographies. ⇒ A **final forward sweep** (Google Scholar
   "cited by" on TruPercept/MATE/CAD/GCP + keyword search) is REQUIRED shortly before
   submission; the 2026-06-26 re-sweep (PAPER_MASTER_PLAN §10.1) covers up to that date only.
2. **Corpus = the 6 audited papers.** The 6 pending audits (CoDynTrust, SwarmRaft, TrustFlip,
   3D-TC2, ADoPT, Conformity) each add a bibliography — the per-audit scan rule below covers
   this, and 3D-TC2/ADoPT will open the single-vehicle temporal-defense reference network we
   have not yet swept.
3. Keyword+manual title triage can still miss a family paper whose title AND our keywords both
   fail to signal it (judged low risk after the manual pass, but not zero).

## Follow-ups this sweep does NOT cover
- The 6 not-yet-audited cited papers (CoDynTrust, SwarmRaft, TrustFlip, 3D-TC2, ADoPT,
  Conformity): each full audit should end by scanning ITS related work and appending to this
  file (add a row or an action item).
- ~~PRBI dossier owed~~ → DONE 2026-07-17: `REFERENCE_EVIDENCE_PRBI.md` (full read, catch #23
  found+fixed, awaiting Srinivasa's review).
