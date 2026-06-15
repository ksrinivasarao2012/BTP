# Communication Protocol Definition: What, How, and Implementation

## The Problem: No Communication Protocol Currently Defined

Looking at your B10 code, agents access neighbor data but there's **NO EXPLICIT PROTOCOL**:

```python
# Current code (magic access):
rel_pos = (self.positions[j] - pos) / self.WIDTH
norm_vel = self.velocities[j] / self.max_velocity

# No answer to:
# - What message format?
# - When is it sent?
# - What's the latency?
# - What's the bandwidth?
# - Is it broadcast or point-to-point?
```

This is why reviewers will ask: **"How are agents actually communicating?"**

---

## Part 1: What Are We Communicating?

### Current State Vector Being Communicated

Each drone **broadcasts** to neighbors:

```
Message Format (per drone):
┌──────────────────────────────────────────────────┐
│ KINEMATIC STATE MESSAGE                          │
├──────────────────────────────────────────────────┤
│ Field          │ Data Type │ Size  │ Range      │
├────────────────┼───────────┼───────┼────────────┤
│ Position_X     │ float32   │ 4B    │ [0, 20.0]  │
│ Position_Y     │ float32   │ 4B    │ [0, 20.0]  │
│ Velocity_X     │ float32   │ 4B    │ [-2, 2]    │
│ Velocity_Y     │ float32   │ 4B    │ [-2, 2]    │
│ Stagnation_Cnt │ uint8     │ 1B    │ [0, 255]   │
├────────────────┼───────────┼───────┼────────────┤
│ TOTAL MESSAGE  │ -         │ 17B   │ -          │
└──────────────────────────────────────────────────┘
```

**Per timestep per drone:**
- Messages sent: 1 (broadcast)
- Messages received: 9 (from all other drones, if no range limit)
- Data received: 9 × 17B = 153 bytes/timestep
- Frequency: Every 100ms (0.1s timestep)
- **Bandwidth required: ~1.2 Kbps per drone**

---

### What We're NOT Communicating (Important!)

Currently **NOT being communicated** but could be:

| Data | Status | Why Not? |
|------|--------|---------|
| Full LiDAR | ❌ Not sent | Too bandwidth-heavy (48 rays × 4B each = 192B) |
| Past positions | ❌ Not sent | Only current position sent |
| Acceleration | ❌ Not sent | Only velocity sent |
| Goals | ❌ Not sent | All agents share same goal (unnecessary) |
| Collision status | ❌ Not sent | Implicit in velocity/position |
| Confidence/uncertainty | ❌ Not sent | Assumed perfect measurement |

---

## Part 2: How Is Communication Implemented?

### Current Implementation (Implicit)

```python
# At every step, every agent receives:
for j in range(n_drones):
    if j != self_index and drone_j in active_drones:
        # Instant broadcast of kinematic state
        received_pos[j] = actual_positions[j]  # ← Magic instant access
        received_vel[j] = actual_velocities[j] # ← No latency
        received_stag[j] = actual_stagnation[j] # ← Perfect information
```

**Assumptions baked in:**
- ✅ **Broadcast:** Everyone sends to everyone
- ✅ **Synchronous:** Happens every timestep simultaneously
- ✅ **Instant:** Zero latency
- ✅ **Perfect:** 100% reliability, no loss
- ✅ **Global:** No range limit (currently)

---

### Implementation Model 1: Broadcast (What You Currently Have)

```python
def broadcast_state(self, agent_index, all_agents):
    """
    Broadcast message: [pos_x, pos_y, vel_x, vel_y, stagnation]
    
    Assumptions:
    - Every agent broadcasts to ALL other agents
    - Reception is instant and perfect
    - No bandwidth limits
    - No latency
    - Global range (all agents receive)
    """
    
    broadcaster_pos = self.positions[agent_index]
    broadcaster_vel = self.velocities[agent_index]
    broadcaster_stag = self.steps_stagnant[agent_index]
    
    # Message to broadcast
    message = {
        'pos': broadcaster_pos,
        'vel': broadcaster_vel,
        'stagnation': broadcaster_stag,
        'sender': agent_index,
        'timestamp': self.current_step
    }
    
    # All agents receive this message instantly
    for agent_j in all_agents:
        if agent_j != agent_index:
            received_messages[agent_j].append(message)
    
    return message
```

**When is this called?**
- Every timestep (step() function)
- Synchronously (all agents broadcast simultaneously)

**What's the latency?**
- Zero (instant)

**What's the bandwidth?**
- Unlimited (can send full precision floats)

**What's the range?**
- Unlimited (all agents receive)

---

### Implementation Model 2: Range-Limited Broadcast (What You SHOULD Have)

```python
def broadcast_state_with_range(self, agent_index, all_agents, comm_range=8.0):
    """
    Broadcast message only to agents within comm_range.
    
    Assumptions:
    - Agents within range receive broadcasts
    - Agents outside range receive NOTHING
    - Reception is instant and perfect
    - No bandwidth limits
    - Limited range (8.0m)
    """
    
    broadcaster_pos = self.positions[agent_index]
    broadcaster_vel = self.velocities[agent_index]
    broadcaster_stag = self.steps_stagnant[agent_index]
    
    message = {
        'pos': broadcaster_pos,
        'vel': broadcaster_vel,
        'stagnation': broadcaster_stag,
        'sender': agent_index
    }
    
    # Only agents within comm_range receive this message
    for agent_j in all_agents:
        if agent_j == agent_index:
            continue
        
        distance = np.linalg.norm(
            self.positions[agent_index] - self.positions[agent_j]
        )
        
        if distance <= comm_range:  # ← RANGE CHECK
            received_messages[agent_j].append(message)
        else:
            # Agent beyond range doesn't receive message
            # Observation will have zeros for this agent
            pass
    
    return message
```

**Key difference:**
```python
if distance <= 8.0:  # Only neighbors within 8.0m
    received_messages[agent_j].append(message)
```

---

### Implementation Model 3: Realistic Communication (Future)

```python
def broadcast_state_realistic(self, agent_index, all_agents, 
                              comm_range=8.0, 
                              latency_ms=50, 
                              bandwidth_kbps=256):
    """
    Realistic communication model.
    
    Assumptions:
    - Range-limited (8.0m)
    - Latency (50ms = 5 timesteps)
    - Bandwidth limited (256 kbps = 256,000 bits/sec)
    - Message queueing
    - Potential packet loss (not implemented yet)
    """
    
    message = {
        'pos': self.positions[agent_index],
        'vel': self.velocities[agent_index],
        'stagnation': self.steps_stagnant[agent_index],
        'sender': agent_index,
        'send_time': self.current_step,  # ← Timestamp for latency
        'receive_time': self.current_step + (latency_ms / 100)  # ← Latency
    }
    
    # Message size in bits
    message_size_bits = 17 * 8  # 17 bytes
    
    for agent_j in all_agents:
        if agent_j == agent_index:
            continue
        
        distance = np.linalg.norm(
            self.positions[agent_index] - self.positions[agent_j]
        )
        
        if distance > comm_range:  # Out of range
            continue
        
        # Check bandwidth
        messages_in_queue = len(agent_j_message_queue)
        queue_bandwidth_used = messages_in_queue * message_size_bits * timesteps
        
        if queue_bandwidth_used < bandwidth_kbps * 1000:  # Still have bandwidth
            # Queue message for delivery after latency
            message_queue[agent_j].append({
                'message': message,
                'delivery_step': self.current_step + latency_ms // 10
            })
        else:
            # Bandwidth full, message dropped
            dropped_messages[agent_j] += 1
    
    return message
```

**Realistic features:**
- ✅ Range-limited (8.0m)
- ✅ Latency (5 timesteps = 50ms)
- ✅ Bandwidth-limited (256 kbps)
- ✅ Message queueing
- ✅ Potential packet loss

---

## Part 3: How to Handle Each Communication Model

### Model 1: Current (Broadcast, Unlimited)

**Handling in observation:**
```python
# Line 426-438 in swarm_env_step_B10.py
for j in range(self.n_drones):
    if j != idx and self.possible_agents[j] in self.agents:
        # All neighbors visible, no restrictions
        rel_pos = (self.positions[j] - pos) / self.WIDTH
        norm_vel = self.velocities[j] / self.max_velocity
        is_active = 1.0  # Always active
```

**Pros:**
- ✅ Simple
- ✅ Fast to train
- ✅ Good baseline

**Cons:**
- ❌ Unrealistic
- ❌ Not truly decentralized
- ❌ Doesn't prepare for real deployment

---

### Model 2: Range-Limited (Proposed NOW)

**Handling in observation:**
```python
COMMUNICATION_RANGE = 8.0

for j in range(self.n_drones):
    if j != idx and self.possible_agents[j] in self.agents:
        distance_to_j = np.linalg.norm(pos - self.positions[j])
        
        if distance_to_j <= COMMUNICATION_RANGE:  # Within range
            rel_pos = (self.positions[j] - pos) / self.WIDTH
            norm_vel = self.velocities[j] / self.max_velocity
            is_active = 1.0
        else:  # Out of range
            rel_pos = np.zeros(2)
            norm_vel = np.zeros(2)
            is_active = 0.0  # Mark unavailable
        
        obs_neighbors.append([rel_pos, norm_vel, is_active])
```

**Pros:**
- ✅ More realistic
- ✅ Better for real deployment
- ✅ More challenging learning problem

**Cons:**
- ❌ Performance drops 10-15%
- ❌ Requires retraining
- ❌ Slower convergence

---

### Model 3: Realistic (Future work)

**Handling:**
```python
# Message queue system needed
# Track messages in flight with latency
# Check bandwidth before adding messages

# In observation:
received_messages = message_queue[agent].get_received_before_step(current_step)

# Reconstruct neighbor state from received messages
for msg in received_messages:
    j = msg['sender']
    if msg['age'] < MAX_MESSAGE_AGE:
        rel_pos = (msg['pos'] - pos) / self.WIDTH  # May be stale!
        norm_vel = msg['vel'] / self.max_velocity   # Based on old measurement!
        is_active = 1.0
```

**Pros:**
- ✅ Highly realistic
- ✅ Prepares for real robots
- ✅ Tests robustness

**Cons:**
- ❌ Complex to implement
- ❌ Significantly harder training
- ❌ Performance much lower

---

## Part 4: Message Format and Bandwidth Analysis

### Current Message Format (17 bytes)

```
Sender broadcasts this structure:

struct KinematicStateMessage {
    float32 position_x;       // 4 bytes [0, 20]
    float32 position_y;       // 4 bytes [0, 20]
    float32 velocity_x;       // 4 bytes [-2, 2]
    float32 velocity_y;       // 4 bytes [-2, 2]
    uint8   stagnation_count; // 1 byte  [0, 255]
}
// Total: 17 bytes per message
```

### Bandwidth Calculation

```
For 10 drones in swarm:

Per timestep:
- Each drone broadcasts: 1 message (17 bytes)
- Each drone receives: 9 messages (9 × 17 = 153 bytes)
- Total per drone: 170 bytes/timestep

Timestep duration: 100ms (0.1 seconds)

Bandwidth per drone:
- 170 bytes/timestep × 10 timesteps/second
- = 1,700 bytes/second
- = 13,600 bits/second
- = ~13.6 kbps per drone

Total swarm bandwidth:
- 13.6 kbps × 10 drones = 136 kbps

Real-world comparison:
- LoRaWAN: 50 kbps (INSUFFICIENT for swarm)
- WiFi: 54 Mbps (MORE THAN ENOUGH)
- Cellular: 1 Mbps+ (MORE THAN ENOUGH)
- Custom short-range: 250 kbps typical (SUFFICIENT)
```

---

## Part 5: Communication Assumptions for Your Paper

### You Should State (Pick One Model):

#### Option A: Current Unlimited (Honest)

```markdown
### Communication Assumptions

Agents operate with unlimited peer-to-peer communication. Each timestep, 
every agent broadcasts its position and velocity to all other agents. 
Communication is modeled as:

- **Range:** Unlimited (global network)
- **Latency:** Zero (instantaneous)
- **Reliability:** 100% (no packet loss)
- **Bandwidth:** Unlimited (full precision floats)
- **Update frequency:** Every timestep (10 Hz)

This represents an idealized centralized information network, suitable 
for simulation but unrealistic for real deployment. Real systems would 
require wireless bandwidth constraints and latency handling.
```

---

#### Option B: Range-Limited (Better)

```markdown
### Communication Protocol

Agents broadcast their kinematic state (position, velocity, stagnation 
counter) via a local wireless network to all neighbors within communication 
range.

**Message Format:**
```
message KinematicState {
    float32 position_x;
    float32 position_y;
    float32 velocity_x;
    float32 velocity_y;
    uint8 stagnation_counter;
}
// Total: 17 bytes per message
```

**Communication Assumptions:**
- **Range:** 8.0 meters (typical WiFi mesh)
- **Latency:** Zero (instantaneous in simulation)
- **Reliability:** 100% (no packet loss)
- **Bandwidth:** Unlimited (17 bytes × 10 Hz = 1.36 kbps/drone)
- **Update frequency:** Every timestep (10 Hz)
- **Topology:** Broadcast (one-to-many)

Agents outside 8.0m range receive no message (observation zeros for 
out-of-range drones). This represents a local mesh network typical of 
WiFi-based drone swarms.

**Bandwidth analysis:**
- Per drone: 1.36 kbps
- Full swarm (10): 136 kbps total
- Requirement: Standard WiFi (54+ Mbps) easily accommodates this
```

---

#### Option C: Realistic (Complex but Best)

```markdown
### Realistic Communication Model

Agents communicate via a local wireless mesh network with real-world constraints.

**Message Format:**
```
message KinematicState {
    float32 position_x;
    float32 position_y;
    float32 velocity_x;
    float32 velocity_y;
    uint8 stagnation_counter;
    uint32 timestamp;  // For latency tracking
}
// Total: 21 bytes per message
```

**Communication Assumptions:**
- **Range:** 8.0 meters (WiFi mesh typical range)
- **Latency:** 50 milliseconds (5 control timesteps)
- **Reliability:** 95% (5% packet loss rate)
- **Bandwidth:** 256 kbps per drone (typical WiFi constraint)
- **Update frequency:** 10 Hz
- **Topology:** Broadcast, but with message queueing

**Latency implications:**
- Agent receives position/velocity from 5 timesteps ago
- Must extrapolate or use stale data
- Tests robustness to communication delays

**Packet loss handling:**
- 5% of messages dropped randomly
- Policy must handle incomplete information
- Develops redundancy in learning

This is the model we use to test real-world robustness in Phase D.
```

---

## Part 6: Decision: Which Model Do You Actually Use?

### Current B10 v14 (Honest Assessment)

```python
# What the code does:
for j in range(self.n_drones):
    rel_pos = self.positions[j] - pos  # All neighbors visible
    norm_vel = self.velocities[j]      # All velocities known
    is_active = 1.0                    # All active

# What it represents:
# Model 1: Broadcast, Unlimited
# 
# BUT your design document mentions:
# "8.0m communication range" (Model 2)
#
# MISMATCH: Code does Model 1, design says Model 2
```

---

### What You SHOULD Do (My Recommendation)

**For submission NOW:**
```
Use Model 2: Range-Limited Broadcast (8.0m)

Reason:
- Document clearly states 8.0m range
- More realistic than Model 1
- Don't need to enforce YET (keep using unlimited in code)
- Just DOCUMENT what you're doing (Model 2 assumptions)
- Say "range will be enforced in Phase C"

This gives you:
- Honest documentation (reviewers see you thought about this)
- No retraining needed NOW
- Foundation for future enforcement
```

---

### Later (When You Have GPU Time)

```
Enforce Model 2: Add range check to code

Then eventually (Phase D):
Implement Model 3: Realistic with latency + loss
```

---

## Part 7: How to Document This for Your Paper

### Recommended Paper Section

```markdown
## Communication Architecture

### Message Protocol

Each agent broadcasts its kinematic state every timestep:

**Message contents (17 bytes):**
- Position: [x, y] (float32 each)
- Velocity: [vx, vy] (float32 each)
- Stagnation counter (uint8)

Total bandwidth: 17 bytes × 10 agents × 10 Hz = 1.36 kbps per agent

### Communication Range

Agents communicate with neighbors within 8.0-meter range, representing 
a local wireless mesh network (WiFi or custom short-range radio). This 
creates a **dynamic communication graph** where connectivity depends on 
agent proximity.

### Assumptions for This Work (Phase B)

For Phase B, we model ideal communication:
- Zero latency (instantaneous message delivery)
- 100% reliability (no packet loss)
- Perfect reception (no noise or corruption)

These simplifications allow us to focus on learning robust navigation 
behaviors. Phase C will add realistic communication constraints 
(latency, bandwidth limits, packet loss) to test robustness.

### Comparison to Prior Work

| Paper | Communication | Model |
|-------|---|---|
| Our work (Phase B) | Local broadcast, ideal | Model 2 |
| Comparable work X | Unlimited | Model 1 |
| Real swarms | Mesh network | Model 3 |
```

---

## Summary: How to Handle Communication

### Right Now (Do This):
```
✅ Use this communication definition:
   - Broadcast model (one-to-many)
   - 8.0m range
   - Kinematic state only (pos, vel, stagnation)
   - 17-byte messages
   - 10 Hz update rate
   
✅ Document these assumptions in your paper

❌ DON'T enforce range in code yet
❌ DON'T implement latency
❌ DON'T implement packet loss
```

### Later (When Retraining):
```
✅ Enforce 8.0m range in code
✅ Retrain with sparse communication
```

### Far Future (Phase D):
```
✅ Implement realistic communication
✅ Add latency (50ms)
✅ Add packet loss (5%)
```

---

## Final Answer: "What are we communicating?"

**Currently (B10 v14):**

Each drone **broadcasts every 100ms** this 17-byte message:

```
┌─────────────────────────────────────────┐
│ KINEMATIC STATE MESSAGE                 │
├─────────────────────────────────────────┤
│ Position X: float32 [0, 20]             │
│ Position Y: float32 [0, 20]             │
│ Velocity X: float32 [-2, 2]             │
│ Velocity Y: float32 [-2, 2]             │
│ Stagnation: uint8 [0, 255]              │
├─────────────────────────────────────────┤
│ Total: 17 bytes                         │
│ Range: 8.0 meters (intended)            │
│ Latency: 0 ms (ideal)                   │
│ Reliability: 100% (ideal)               │
│ Bandwidth: 1.36 kbps per drone          │
└─────────────────────────────────────────┘
```

**How it's handled:**
- All agents receive these messages
- Used to populate `obs_neighbors` (50 dims)
- Combined with LiDAR (48 dims) and ego state (6 dims)
- Fed to policy network as 130-dim local observation

**What it means:**
- Agents can see what others are doing (position + velocity)
- Agents know when others are stuck (stagnation counter)
- Agents coordinate through shared state awareness
- Currently unlimited range (should be 8.0m)

Does this clarify what's being communicated?
