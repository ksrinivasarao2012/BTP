# MANUAL REFERENCE VERIFICATION GUIDE

How to verify every reference in the manuscript yourself. For each paper you check **two things**:

- **(A) Metadata** — open the link, compare title / authors / year / venue against our `manuscript/refs.bib`
  entry. Every word of the title and every author surname must match.
- **(B) Our claim** — read the sentence(s) WE wrote about that paper (quoted below from the manuscript),
  then read THEIR abstract (and intro if needed) and ask: *"is what we say about this paper true?"*

**Method for (B):** open the arXiv page → read the abstract slowly → for each phrase of our claim, find the
supporting sentence in their abstract. If you cannot find support, mark it ❓ and tell Claude — either the
claim gets fixed or we find the support deeper in the paper.

**Red flags to watch for (any of these = report it):**
1. A word in our claim that their abstract does not support (e.g., we say "requires X" but they never say X).
2. Our claim describes their MOTIVATION as if it were their METHOD (or vice versa).
3. We say the paper "does not do Y" — hardest to verify; search their PDF (Ctrl+F) for Y's keywords.
4. Venue/year mismatch with refs.bib.

Tick each box when done. All claims below are quoted from `manuscript/sections/related.tex` (r) and
`methods.tex` (m) as of 2026-07-09.

---

## Group A — Collaborative-perception security (read these most carefully)

### [ ] 1. CAD — zhang2024cad
- **Link:** https://arxiv.org/abs/2309.12955 · **bib says:** Zhang, Jin, Zhu, Sun, Zhang, Chen, Mao; USENIX Security 2024.
- **Our claim (r6):** "demonstrate practical data-fabrication attacks on vehicular collaborative perception
  and propose CAD, a detector in which benign vehicles jointly reveal malicious fabrication through
  cross-vehicle occupancy agreement; the approach therefore relies on benign vehicles positioned to observe
  the attacked region."
- **Check in their abstract:** (1) do they present fabrication ATTACKS? (2) is their defense based on benign
  vehicles jointly revealing fabrication / occupancy consistency? (3) does the defense need a benign vehicle
  that can see the attacked region? — the word "jointly" and the benign-observer dependence are the critical
  bits; we softened this claim once already, so confirm the current wording is fully supported.

### [ ] 2. TruPercept — trupercept2020
- **Link:** https://arxiv.org/abs/1909.07867 · **bib says:** Hurl, Cohen, Czarnecki, Waslander; IEEE IV 2020, pp. 341–347.
- **Our claim (r18):** "Trust-modulated fusion appears in TruPercept … which weigh[s] deep feature
  contributions rather than verify geometric claims."
- **Check:** (1) is it about trust modelling for cooperative perception? (2) ⚠ the phrase "deep feature
  contributions" — TruPercept weights DETECTIONS by trust; if their abstract talks about detections
  (not features), our sentence needs a tweak. Verify which it is. Also confirm pp. 341–347 on the IEEE page
  (or delete the page numbers if unverifiable).

### [ ] 3. CoDynTrust — codyntrust2025
- **Link:** https://arxiv.org/abs/2502.08169 · **bib says:** Xu, Li, Wang, Yang, Wu, Chen, Wang; arXiv 2025.
- **Our claim (r19):** "for asynchronous settings … weigh deep feature contributions rather than verify
  geometric claims."
- **Check:** (1) is asynchrony their setting? (2) is their trust applied at FEATURE level? ("dynamic feature
  trust modulus" in their title suggests yes — confirm in abstract). (3) Check whether it has been accepted
  at a venue since (search the arXiv page for a journal/conference note) — if yes, update refs.bib.

### [ ] 4. PRBI — prbi2026  ⭐ MOST IMPORTANT CHECK IN THE WHOLE LIST
- **Link:** https://arxiv.org/abs/2603.08498 · **bib says:** Yu, Wu, Zhang, Qiu, Huo, Feng; CVPR 2026.
- **Our claim (r21):** "exploits frame-to-frame perceptual consistency to identify lying vehicles in fully
  untrusted cooperative detection. It differs from our setting in three ways…: it optimizes a
  detection-accuracy metric on feature-level fusion rather than a closed-loop navigation objective; it does
  not model ranging noise, and so does not confront the honest-disagreement regime…; and it does not
  consider an adaptive attacker."
- **Check:** the positive part (frame-to-frame consistency, fully untrusted) from the abstract. Then the
  THREE "does not" claims — these need the PDF: Ctrl+F for "noise" (do they model sensor/ranging noise
  anywhere?), "adaptive" (do they test an adaptive/defense-aware attacker?), and check their metrics section
  (AP / detection accuracy vs navigation success). If ANY of the three fails, tell Claude immediately —
  this is our novelty differentiation and it must be bulletproof.

### [ ] 5. TrustFlip — trustflip2026
- **Link:** https://arxiv.org/abs/2605.22122 · **bib says:** Liu, Wang, Li, Zhang; arXiv 2026.
- **Our claim (r29):** "shows that consistency-based trust can itself be weaponized: physically induced
  disagreements cause defenses to expel honest vehicles."
- **Check:** (1) attack on trust systems (not on perception directly)? (2) mechanism = physical adversarial
  objects creating REAL but conflicting observations? (3) outcome = honest vehicles excluded? All three
  should be in the abstract.

## Group B — Temporal spoof detection (single vehicle)

### [ ] 6. 3D-TC2 — tc2_2021  ⚠ title was WRONG once already — double-check
- **Link:** https://arxiv.org/abs/2106.07833 · **bib says:** "Temporal Consistency Checks to Detect LiDAR
  Spoofing Attacks on Autonomous Vehicle Perception"; You, Hau, Demetriou; MAISP 2021 workshop.
- **Our claim (r39):** "detects LiDAR spoofing against a single vehicle by exploiting temporal structure in
  its own sensor stream, e.g. motion-induced consistency."
- **Check:** (1) exact title matches bib (word for word). (2) single-vehicle setting (not cooperative).
  (3) uses motion prediction / temporal consistency. (4) venue = MAISP workshop 2021.

### [ ] 7. ADoPT — adopt2023
- **Link:** https://arxiv.org/abs/2310.14504 · **bib says:** Cho, Cao, Zhou, Mao; BMVC 2023.
- **Our claim (r40):** "point-level temporal consistency," single vehicle, own sensor stream.
- **Check:** title says "Point-Level Temporal Consistency" — confirm; confirm BMVC 2023; confirm
  single-vehicle (not V2X/cooperative).

## Group C — Byzantine multi-robot / swarm

### [ ] 8. Byzantine Generals — lamport1982byzantine
- **Link:** search "The Byzantine Generals Problem Lamport 1982" (ACM DL).
- **bib says:** Lamport, Shostak, Pease; ACM TOPLAS 4(3):382–401, 1982.
- **Our claim (r52):** "Byzantine fault tolerance originates in distributed computing" — foundational cite only.
- **Check:** metadata only (volume 4, issue 3, pages 382–401). No claim to verify.

### [ ] 9. SwarmRaft — swarmraft2025  ⚠ we deliberately do NOT call it Byzantine — verify our caution
- **Link:** https://arxiv.org/abs/2508.00622 · **bib says:** Dev, Madhwal, Shevelo, Osinenko, Yanovich; arXiv 2025.
- **Our claim (r54):** "Consensus-based coordination such as SwarmRaft fuses peer measurements to maintain
  agreement on state (e.g. position and heading) under degraded conditions."
- **Check:** (1) Raft consensus on position/heading state in GNSS-degraded swarms — abstract. (2) confirm we
  are right NOT to call it Byzantine-tolerant: Ctrl+F their PDF for "Byzantine" — if they DO claim Byzantine
  tolerance somewhere, tell Claude (we'd soften differently).

### [ ] 10. Conformity game — conformity2026
- **Link:** https://arxiv.org/abs/2606.21206 · **bib says:** Ren, Zhao, Fang; arXiv 2026.
- **Our claim (r56):** "evolutionary-game analyses model how deceptive strategies propagate through
  conformity dynamics under Byzantine influence."
- **Check:** abstract should contain: evolutionary game, local conformity, UAV swarm, Byzantine. Also
  confirm it is about CONSENSUS/decision layer (not perception) — that's our differentiation.

## Group D — RL/MARL foundations (metadata-only checks, claims are standard)

### [ ] 11. MAPPO — yu2022mappo
- **Link:** https://arxiv.org/abs/2103.01955 · **bib says:** Yu, Velu, Vinitsky, Gao, Wang, Bayen, Wu;
  NeurIPS 2022 Datasets & Benchmarks Track.
- **Our claim (m33, r67):** our training follows "the MAPPO recipe" under CTDE. Standard; verify metadata +
  that the paper indeed introduces/evaluates multi-agent PPO (MAPPO).

### [ ] 12. PPO — schulman2017ppo
- **Link:** https://arxiv.org/abs/1707.06347 · Schulman, Wolski, Dhariwal, Radford, Klimov; 2017.
- **Claim:** "built on PPO" — foundational. Metadata only.

### [ ] 13. Stable-Baselines3 — raffin2021sb3
- **Link:** https://jmlr.org/papers/v22/20-1364.html · Raffin, Hill, Gleave, Kanervisto, Ernestus, Dormann;
  JMLR 22(268):1–8, 2021.
- **Claim:** "in implementation, on Stable-Baselines3" — true by construction (it IS our library). Verify
  volume/number/pages on the JMLR page.

### [ ] 14. MADDPG — lowe2017maddpg
- **Link:** https://arxiv.org/abs/1706.02275 · Lowe, Wu, Tamar, Harb, Abbeel, Mordatch; NeurIPS 2017.
- **Our claim (r70):** "CTDE itself traces to multi-agent actor-critic formulations such as MADDPG."
- **Check:** abstract confirms centralized critic + decentralized actors. Metadata.

---

## After you finish
1. Tick all boxes; report every ❓ / red flag to Claude with the paper number.
2. Anything that fails gets fixed in `refs.bib` (metadata) or the section prose (claims) BEFORE submission.
3. When all 14 pass, mark section C in `PAPER_TODO.md` as human-verified (not just Claude-verified).
