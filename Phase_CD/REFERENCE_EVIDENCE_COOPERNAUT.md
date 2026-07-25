# Reference evidence — COOPERNAUT (full-PDF read, 2026-07-26)

**Verdict: CITE + NOVELTY-WORDING SAFEGUARD. Does NOT pre-empt our security contribution.**
It is the *benign paradigm* our combination-novelty sentence leans on (closed-loop LEARNED cooperative-
perception policy scored by task success), so we must credit it for the paradigm and claim novelty on the
**attack + trust-defense layer**, not on the paradigm itself. This is the exact precedent the earlier
title-level scan mis-bucketed as "plumbing."

---

## What it is (verbatim, with page pointers)
- **Full cite:** Jiaxun Cui, Hang Qiu, Dian Chen, Peter Stone, Yuke Zhu. "COOPERNAUT: End-to-End Driving with
  Cooperative Perception for Networked Vehicles." **CVPR 2022.** arXiv:2205.02222. Project:
  ut-austin-rpl.github.io/Coopernaut.
- **Core (abstract, p.1):** *"an end-to-end learning model that uses cross-vehicle perception for vision-based
  cooperative driving… encodes LiDAR information into compact point-based representations that can be
  transmitted as messages between vehicles via realistic wireless channels… a 40% improvement in average
  success rate over egocentric driving models… a 5× smaller bandwidth requirement than prior work V2VNet."*
- **Model (p.3–4):** Point Encoder (3 Point-Transformer blocks) per neighbour → compact keypoint messages
  `M_j = {(p_jk, R_pjk)}` → Representation Aggregator (spatial transform to ego frame + voxel max-pool +
  Point-Transformer) → Control Module (throttle/brake/steer). Receives messages from **3 randomly chosen V2V
  vehicles** (p.4, "For bandwidth control…").
- **Training (p.4–5):** imitation learning — behavior cloning warm-start then **DAgger**, imitating an
  **oracle expert with privileged information** (A* planner, p.6 §4.3). *"permitting control supervision…
  to flow back to the perception stack"* (p.2).
- **Sim + task (p.5 §4):** AUTOCASTSIM on CARLA; **3 accident-prone NHTSA scenarios** — Overtaking, Left
  Turn, Red Light Violation — all designed so ego line-of-sight cannot see the collider.
- **Metrics (p.6 §5.1):** **Success Rate**, Collision Rate, Success-weighted-by-Completion-Time. Headline
  Table 2 (p.7): COOPERNAUT SR **90.5 / 80.7 / 80.7** vs **No V2V Sharing 45.3 / 40.3 / 47.3** across the
  three scenarios; density sweep Fig.4 (p.8) holds the CP advantage across traffic density.

## Why it does NOT pre-empt us (the differentiation to put in related.tex)
| Axis | Coopernaut | Ours |
|---|---|---|
| **Adversary** | **None.** All vehicles honest. No attack, no traitor, no trust, no defense. Robust only to 5% *random* packet loss + slight *benign* pose error (p.8 §5.4). | Byzantine drones broadcast **persistent fabricated obstacles**; core contribution is attack **+ temporal offset-bias trust defense**. |
| **Contribution class** | Shows CP **helps** benign driving; a perception/fusion + policy-learning paper. | Shows CP is a **security surface** and closes it; a trust/robustness paper. |
| **Domain** | On-road networked cars, V2V driving. | Aerial drone swarm, shared-goal navigation. |
| **Fusion** | Learned Point-Transformer representation fusion. | Geometric slot/MIN fusion into the LiDAR channel + pairwise geometric trust gate. |
| **Trust** | Absent (assumes accurate localization, honest peers). | The whole paper. |
| **SHARED (must credit)** | **Closed-loop LEARNED CP policy scored by task success rate.** | Same paradigm — we build the attack/defense layer *inside* it. |

## The precision trap (do NOT overclaim)
- Coopernaut **already owns** "closed-loop learned cooperative perception evaluated by navigation success."
  So we must NOT write "we are the first to evaluate cooperative perception inside a closed-loop learned
  navigation task by end success." We ARE first (in this family) to **attack that loop with fabricated
  obstacles and defend it with a temporal trust test** — that is the safe claim.
- Coopernaut also has a **privileged oracle expert** (A* planner) driving imitation — structurally the same
  kind of privileged-planner concession as our Dijkstra goal-heading. Do NOT wield "they use a privileged
  planner" as a differentiator; we have the analogous crutch (disclosed in discussion.tex assumption (i)).
- It is **benign** — never imply Coopernaut studied adversarial robustness. Its only robustness claims are to
  *random* packet loss and *slight* localization error (p.8), explicitly not adversarial.

## Exact novelty-wording safeguard for related.tex
Wherever the manuscript claims novelty on the "closed-loop learned navigation, success as the end metric"
paradigm, insert a credit clause, e.g.:
> "Closed-loop learned cooperative perception evaluated by end-task success was established for benign
> networked driving (Coopernaut~\cite{coopernaut2022}); our contribution is not that paradigm but the
> adversarial layer within it — a fabricated-obstacle Byzantine attack on the shared channel and a temporal
> trust defense that neutralizes it."

## refs.bib entry (needed if cited)
```bibtex
@inproceedings{coopernaut2022,
  title={{COOPERNAUT}: End-to-End Driving with Cooperative Perception for Networked Vehicles},
  author={Cui, Jiaxun and Qiu, Hang and Chen, Dian and Stone, Peter and Zhu, Yuke},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  pages={17252--17262},
  year={2022}
}
```
(Verify page numbers against the CVF open-access proceedings before final submission.)

## Novelty / publication impact
**No damage.** Coopernaut strengthens our framing rather than threatening it: it is the citable evidence that
"CP improves navigation success in a closed-loop learned policy" is an established, respectable paradigm — so
our attack+defense on that paradigm is a natural, well-motivated next step, not a toy. The single required
change is a one-clause credit in related.tex (above). It affects **wording only**, not the contribution.
