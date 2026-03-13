# Trick Challenge: The Physical Goal Deadlock

## The Problem
After fixing the "Ghost Drone Bug" (where completed drones remained invisible walls), the success rate remained firmly capped at **88%** to **89%**. 

Diagnostic logs tracking exactly where the final $11\%$ of crashes were occurring revealed a surprising pattern: *Every single crash was happening right on top of the goal pixel.*

## Diagnosing the Issue
The training environment required a drone's $(X, Y)$ coordinate to mathematically cross the `0.5m` radius of the goal in order to be declared successful. However, the physical drones themselves had a collision radius of `0.25m` (a visual footprint of `0.5m`).

When 10 drones arrived at the goal at roughly the exact same time, basic geometry dictated that **10 physical objects with a 0.5m footprint cannot occupy a 0.5m hole simultaneously.**

Because they all wanted the $+100$ success reward, they all rushed the goal. The first 3 or 4 drones would successfully "squeeze" in and terminate, but the remaining 6 drones would end up aggressively colliding with each other as they funneled into the choke-point, instantly failing the simulation right at the finish line.

## The Solution
We changed the mathematics of the `finish line` to account for the physical size of 10 drones arriving as a swarm.

We relaxed the mathematical goal acceptance radius from `0.5` strictly to `0.75`. By expanding the finish line's surface area, it allowed drones to correctly trigger the "Success" condition from just outside the choke-point without having to physically overlap with the drones arriving immediately next to them.
