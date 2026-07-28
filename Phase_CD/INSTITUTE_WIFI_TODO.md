# INSTITUTE WIFI TODO — everything that needs campus / IEEE Xplore access

**Created 2026-07-27 (Monday). Srinivasa gets institute wifi ≈ 2026-08-03.**
**Reminder set: every Sunday until this file is done.**

Why this file exists: IEEE-published papers (ITSC / IV / VNC / COMST / T-RO) are paywalled.
Claude cannot fetch them. They can only be downloaded from the institute network.
Everything below is blocked on that one session.

**Save every PDF to `D:\Swarm\BTP\Phase_CD\Research paper\` with the exact filename given.**
Then tell Claude "PDFs are in" and it will full-read each one.

---

## ⭐ PRIORITY 1 — blocks the prior-art audit (do these first)

These two are the closest classical ancestors of our method. Both are Tier-1 rows in the
second-order sweep audit and Srinivasa already ran the 3-question check on their abstracts.

- [ ] **Obst et al. (VNC 2014)** — *"Multi-sensor data fusion for checking plausibility of V2V
      communications by vision-based multiple-object tracking"*
      → save as `Obst2014.pdf`
      IEEE: https://ieeexplore.ieee.org/document/7013333/
      Free mirror (try first, may work off-campus):
      https://scholar.archive.org/work/42krthh6erhebnwff3ayqzgtvi/access/wayback/http://www.autonet2030.eu/wp-content/uploads/2014/12/VNC-2014-Sensor-Fusion-Obst.pdf
      **Why:** same *premise* as us (check peer claim vs my own sensing). Need to confirm it does
      NOT do navigation and does NOT accumulate per-neighbour evidence over frames.

- [ ] **Allig et al. (VNC 2019)** — *"Trustworthiness Estimation of Entities within Collective Perception"*
      → save as `Allig2019.pdf`
      IEEE: https://ieeexplore.ieee.org/document/9062796/
      Free mirror (try first): http://leinmueller.de/lib/exe/fetch.php/publications/allig2019trust_cpm.pdf
      **Why:** nearest classical ancestor. ⚠ **Srinivasa's own check found it DOES handle sensor
      noise** (uncertainty in fusion) — Claude's abstract read said it did not. So we must NOT write
      "they ignore sensor noise" as our differentiator. Full read must establish the correct wording.

---

## 🚨 PRIORITY 0 — RLCVP: THE ONLY UNVERIFIED MUST-CITE (added 2026-07-28)

**Do this one first. It is the single highest-value download on this entire page.**

- [ ] 🚨 **Lin, Xiao, Chen, Lv — "Collaborative Perception Against Data Fabrication Attacks in Vehicular
      Networks"** (IEEE **Transactions on Mobile Computing**, Oct 2025, doc **11006384**)
      → save as `RLCVP.pdf`
      https://ieeexplore.ieee.org/abstract/document/11006384/

      **Why this one matters more than anything else here:**
      - It is a **Level-1 must-cite** — it gets its own differentiator paragraph in our related work.
      - Its title reads almost exactly like our paper: *RL + collaborative perception + data-fabrication defense*.
      - Our differentiator sentence — *"their RL selects which CAV to collaborate with, not a driving policy"* —
        currently rests on **abstract-level evidence only**. It is **not verbatim-verified**.
      - Every other quoted paper has now been verified word-for-word via the curl→Read path. **RLCVP is the only
        gap**, and it is not on arXiv, so Claude cannot reach it.
      - ⚠️ The CATS incident (2026-07-28) proved exactly this risk: an abstract-level differentiator turned out
        to be **wrong** when the real text was read. RLCVP is the last claim standing on that footing.

      **What to check once the PDF is on disk** (Claude will do this — just get the file):
      1. Is the RL policy selecting **collaborators**, or is it driving/controlling the vehicle?
      2. Is the consistency check **spatial only**, or does it accumulate per-neighbour evidence over frames?
      3. Does it model **honest sensor noise** causing benign disagreement?
      4. What is the evaluation metric — detection rates, or a driving/navigation outcome?

---

## ⭐ PRIORITY 1b — FORWARD-SWEEP papers Claude could NOT reach (added 2026-07-28)

These surfaced in the **forward-citation sweep** (who cites CAD / ROBOSAC / TruPercept / Coopernaut).
Claude read every reachable one's abstract **and** conclusion. **These 6 were blocked** — paywall, bot
protection, or no full text online. Claude has title + venue + (sometimes) a partial abstract only.

- [ ] ⚠️ **Ben-Jemaa / Zhang et al. — "Cooperative Trust Based Detection Mechanism for Fake Objects in
      Collective Perception Messages"** (Springer LNCS, 2025; DOI 10.1007/978-3-031-87775-9_16)
      → save as `FakeObjectsCPM_Trust.pdf`  · **HIGHEST PRIORITY OF THIS GROUP**
      Springer login-walled (redirects to idp.springer.com).
      **Why it matters:** *"focuses on the fake objects attack, where the attacker sends non-existent objects
      in its CPMs"* + *"verification and tagging process and the trust calculation process"* — this is the
      **same attack class as ours (fabricated objects) with a per-neighbour trust score**. Need to confirm it
      is message-layer only, with **no learned navigation, no ranging-noise regime, and no cross-agent
      temporal offset statistic**.

- [ ] ⚠️ **Zhang, Jiahao — PhD thesis, "Misbehavior Detection for Collective Perception"** (2024, IRT SystemX /
      Inria) → save as `Zhang2024_MDS_CP_thesis.pdf`
      HAL is behind Anubis bot-protection (`theses.hal.science/tel-05113104`).
      **Why:** a whole thesis on CPM misbehaviour detection — the single best map of that sub-field. Likely
      cites/contains the entire European CPM-MDS lineage we only partly know.

- [ ] **Same author — "A cooperative trust model against CAM- and CPM-based attacks"** (HAL hal-04453209)
      → `CoopTrustModel_CAM_CPM.pdf` · also Anubis-blocked.

- [ ] **"Security in Collaborative Driving: A Survey of Threats, Defenses, and Emerging Trends"**
      (MDPI *Electronics* 15(11):2389, 2026) → `SecurityCollabDriving_Survey.pdf`
      MDPI returned 403 to the fetcher (it IS open-access — should download fine from any browser).
      **Why:** the newest survey of exactly our field. Best single check that we have not missed a defense family.

- [ ] **Calipari et al. — "CIAK-CP: Camera feed Injection AttacK in Collaborative Perception"**
      (ACM SAC 2026) → `CIAK_CP.pdf` · ACM DL paywall. (Also on Zenodo record 17804455 — try that first.)
      Attack-only, camera modality → expected group-cite, low risk.

- [ ] **Liu, Guoxi et al. — "ALADCP: Attention-Based Late-Fusion Anomaly Detection for V2V Collaborative
      Perception"** (2026) → `ALADCP.pdf` · no accessible full text found.
      **Why it matters:** **late-fusion = object level, like ours** (most rivals are feature-level). Need to
      confirm it is per-frame and detection-scored.

- [ ] **"Sieve: Computationally Efficient Hierarchical Adversarial Feature Detection in Multi-Agent
      Perception"** (2026) → `Sieve.pdf` · no abstract located anywhere online; feature-level per its title.

**⚠ CONCLUSIONS OWED — 6 papers where Claude has the abstract but the conclusion is paywalled** (chased on
2026-07-28 through every free route: IEEE returned HTTP 418, ScienceDirect/Springer subscription-walled, HAL
Anubis-blocked, Semantic Scholar 429). Abstracts are rich enough to classify all as **group-cite except RLCVP**,
but the conclusions must be read before the related-work paragraph is final:
FNO-Guard (ScienceDirect) · "Robust Collaborative Perception: Adversarial Training + Consensus" (IEEE 11097632) ·
"Adversarial Collaborative Perception in Autonomous Driving" (IEEE 11185995) · **RLCVP / "Collaborative
Perception Against Data Fabrication Attacks in Vehicular Networks"** (IEEE TMC 11006384 — confirm its RL selects
*collaborators*, not a driving policy) · "Trust Management Framework for Misbehavior Detection in Collective
Perception Services" (ICARCV'22, IEEE 10004259) · US Patent **US20240323657A1** *"Misbehavior detection using
data consistency checks for collective perception messages"* (Google Patents — free, but read it: a patent in
our exact space is worth knowing about).

---

## PRIORITY 2 — the paired skim (flagged since 2026-07-17, PRIOR_ART_SECOND_ORDER §2 and §4)

Decide cite / no-cite for this pair together — both are early members of the
object-claim-verification family our survey enters at TruPercept.

- [ ] **MDS — Ambrosin et al. (IEEE ITSC 2019)** — misbehaviour detection, occupancy-map consistency
      + majority voting across CAVs → save as `MDS.pdf`
      **Why:** predates TruPercept; a reviewer could say our "closer line" survey misses its earliest
      member. CAD already reports its majority vote is defeated by victim-targeted lying → no
      pre-emption, at most a mention.

- [ ] **MISO-V — Liu et al. (IEEE IV 2021)** — *"Misbehavior detection for collective perception
      services in vehicular communications"* → save as `MISO_V.pdf`
      **Why:** same family/decision as MDS. Object-level claim checking on CPMs.

---

## PRIORITY 3 — the IEEE Xplore SEARCH SESSION (the blind-spot fix)

**This is the important one and is not just a download — it is a search session.**
Flagged by Srinivasa 2026-07-17 (`PRIOR_ART_SECOND_ORDER.md` §"Paywalled-literature blind spot").

**The problem:** every 2025–26 competitor was found by keyword search (arXiv is public). But every
pre-2022 family member (Obst'14, MDS'19, Allig'19, MISO-V'21) was found ONLY because some paper we
already had happened to cite it. That older VANET/V2X shelf lives in IEEE conferences from before
the preprint norm — invisible to Claude's searches. So there may be family members nobody cited.

**Do this in Xplore (search titles + abstracts), copy the result lists, paste to Claude for triage:**

- [ ] `"misbehavior detection" AND "collective perception"`
- [ ] `trust AND "cooperative perception"`
- [ ] `plausibility AND V2X`
- [ ] `"false object" AND V2X`
- [ ] `trust AND "multi-robot"`   ← the T-RO / ICRA robotics side
- [ ] Open **"Cited by"** in Xplore for: **MDS**, **MISO-V**, **Obst** — forward citations inside
      IEEE reveal the non-arXiv members of the family.

**Risk if skipped:** bounded, not zero. Any 2025–26 near-neighbour would be on arXiv and we would
have caught it; the IEEE-only shelf is older work that mostly earns survey citations. But
"bounded ≠ zero" → this session is **REQUIRED before submission**.

---

## PRIORITY 4 — optional, grab if the session has time left

All are nice-to-have citations, none is a novelty threat. Zero risk if skipped.

- [ ] **Van der Heijden et al.** — *"Survey on Misbehavior Detection in Cooperative ITS"* (IEEE COMST)
      → `VanDerHeijden_MDS_Survey.pdf`
      **Best value of this group:** citing this ONE survey covers every classical misbehaviour-detection
      paper a reviewer could name (Golle'04, Bißmeyer'12, REPLACE, REDEM, …) in a single stroke.
- [ ] **Cavorsi et al. (T-RO 2024)** — *"Exploiting Trust for Resilient Hypothesis Testing with
      Malicious Robots"* → `Cavorsi2024.pdf`
      **Why:** nearest Robotics-community work; RAS reviewers may come from this group.
- [ ] **Hallyburton & Pajic (CDC 2024)** — Bayesian trust in collaborative multi-agent autonomy
      → `Hallyburton_CDC2024.pdf` — the theory paper MATE + AerialTrust both build on.
- [ ] **Tsukada et al. (CCNC 2022)** — CPM-based misbehaviour detection → `Tsukada2022.pdf`
- [ ] **Cheng et al. (IEEE IV 2021)** — trust-aware control for ITS → `Cheng2021.pdf`

---

## NOT blocked by wifi (Claude can do these anytime — do not waste campus time on them)

- CP-Guard (AAAI'25) — free on arXiv: https://arxiv.org/abs/2412.12000
- Pretend-Benign (ICCV'25) — free on CVF Open Access
- LUCIA/SOMBRA (USENIX Sec'25) — free on usenix.org
- Forward-citation sweep via Google Scholar (public)

---

## After the session — hand back to Claude

1. Confirm PDFs are in `Phase_CD/Research paper/`.
2. Paste the Xplore search result lists (titles are enough) into the chat.
3. Claude will: full-read Obst + Allig, fix the Allig differentiator wording, triage the Xplore
   lists against the novelty claims, and update `AUDIT_PENDING.md`.

_Nothing here is closed until Srinivasa personally signs off (standing audit rule)._
