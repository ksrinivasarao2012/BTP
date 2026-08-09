"""
BiasedNoisyByzantineEnv — assumption-(vi) stress-test subclass.

Adds a PER-AGENT SYSTEMATIC SENSOR BIAS on top of the pristine NoisyByzantineEnv, WITHOUT touching
that (camera-ready) file. Every honest agent j gets a persistent offset b_j, drawn once per episode
(fixed direction, magnitude = `sensor_bias` metres), added to EVERY obstacle it senses on EVERY
frame — i.e. a miscalibrated-but-honest sensor.

Why this matters: the temporal filter assumes honest offsets are ZERO-MEAN. Under bias the honest
pairwise offset d = (b_j - b_i) + (eps_j - eps_i) has mean (b_j - b_i) != 0, so a naive temporal
test could flag an honest neighbour. This env lets us MEASURE that (Stage 1) and, later, test a
per-neighbour global-offset fix (Stage 2). The bias is UNIFORM across all of an agent's tracks —
the signature that separates miscalibration from a localized camouflage lie.

`sensor_bias=0.0` (default) reproduces the parent env exactly (no bias drawn, nothing added).
Only the dedicated bias study (`eval_bias_sweep.py`) ever instantiates this class; every existing
/ camera-ready evaluation keeps using the pristine `NoisyByzantineEnv`.
"""
import numpy as np
from env_noisy_byzantine import NoisyByzantineEnv


class BiasedNoisyByzantineEnv(NoisyByzantineEnv):
    def __init__(self, *args, sensor_bias=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensor_bias = float(sensor_bias)                       # per-agent constant offset (m)
        self._agent_bias = np.zeros((self.n_drones, 2), dtype=np.float32)

    def reset(self, *args, **kwargs):
        out = super().reset(*args, **kwargs)
        # draw b_j once per episode: fixed random direction, magnitude = sensor_bias. Draws AFTER
        # super().reset seeded np.random, so it is reproducible for a given episode seed.
        if self.sensor_bias > 0.0:
            ang = np.random.uniform(0.0, 2.0 * np.pi, size=self.n_drones)
            self._agent_bias = (self.sensor_bias *
                                np.stack([np.cos(ang), np.sin(ang)], axis=1)).astype(np.float32)
        else:
            self._agent_bias = np.zeros((self.n_drones, 2), dtype=np.float32)
        return out

    def _sample_sensing(self):
        prev = self._sense_step
        super()._sample_sensing()                                  # parent computes truth + noise
        # add the per-agent bias ONLY on a freshly-sampled frame (parent guards repeat calls via
        # _sense_step); never double-add within a step.
        if self.sensor_bias > 0.0 and self._sense_step != prev and self._sensed.shape[1]:
            self._sensed = (self._sensed + self._agent_bias[:, None, :]).astype(np.float32)
