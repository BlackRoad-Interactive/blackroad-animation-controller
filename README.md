# BlackRoad Animation Controller

> **Production-ready skeletal animation engine** — Forward Kinematics, FABRIK Inverse Kinematics, keyframe clip blending, and humanoid presets.
>
> Built by **BlackRoad OS, Inc.** — Proprietary software. Commercial licensing available via [Stripe](#licensing--commercial-use).

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
   - [Python (pip)](#python-pip)
   - [Node.js / npm](#nodejs--npm)
4. [Quick Start](#quick-start)
5. [API Reference](#api-reference)
   - [Enums](#enums)
   - [Bone](#bone)
   - [Skeleton](#skeleton)
   - [Keyframe](#keyframe)
   - [Clip](#clip)
   - [Animator](#animator)
   - [Forward Kinematics](#forward-kinematics)
   - [Inverse Kinematics (FABRIK)](#inverse-kinematics-fabrik)
   - [Preset Factories](#preset-factories)
6. [Examples](#examples)
   - [Humanoid Skeleton + Walk Cycle](#humanoid-skeleton--walk-cycle)
   - [Blending Between Clips](#blending-between-clips)
   - [Smooth Transition](#smooth-transition)
   - [IK Reach](#ik-reach)
7. [Licensing & Commercial Use](#licensing--commercial-use)
8. [Support](#support)

---

## Overview

**BlackRoad Animation Controller** is a self-contained, dependency-free skeletal animation library designed for games, simulations, and interactive media. It provides a complete pipeline from skeleton construction through keyframe animation to real-time blending — all in pure Python with no external dependencies.

The library ships with a humanoid preset and three production-ready animation clips (walk, idle, jump) that can be used out of the box or extended with custom rigs.

---

## Features

| Feature | Description |
|---|---|
| **Hierarchical Skeleton** | Parent/child bone relationships with automatic world-transform propagation |
| **Forward Kinematics (FK)** | Full recursive FK traversal computing world position and angle for every bone |
| **Inverse Kinematics (IK)** | FABRIK algorithm with configurable iterations and convergence tolerance |
| **Keyframe Clips** | Time-sorted keyframe sequences with per-keyframe easing |
| **Interpolation Types** | `LINEAR`, `CUBIC` (smoothstep), and `STEP` easing per keyframe |
| **Loop Modes** | `ONCE`, `LOOP`, and `PING_PONG` playback modes per clip |
| **Clip Blending** | Instant weighted blend between two clips with a normalized alpha |
| **Smooth Transitions** | Time-based cross-fade (`transition_to`) with configurable duration |
| **Animator Controls** | `play`, `pause`, `resume`, `stop`, `blend`, `transition_to`, `update`, `export_frame` |
| **Humanoid Preset** | 11-bone humanoid rig: root, spine, head, arms, and legs |
| **Clip Presets** | Walk cycle, idle breathe, and jump clips ready for immediate use |
| **JSON Export** | Full skeleton and frame state serialisable to JSON |
| **Zero Dependencies** | Pure Python 3.8+ standard library only (`math`, `dataclasses`, `enum`) |

---

## Installation

### Python (pip)

```bash
pip install blackroad-animation-controller
```

Or install directly from source:

```bash
git clone https://github.com/BlackRoad-Interactive/blackroad-animation-controller.git
cd blackroad-animation-controller
pip install .
```

Requires **Python 3.8 or later**. No additional dependencies.

### Node.js / npm

A JavaScript/TypeScript port is available on the npm registry:

```bash
npm install @blackroad/animation-controller
```

> **Note:** The npm package mirrors the Python API and is kept in sync with this repository. See the [npm package page](https://www.npmjs.com/package/@blackroad/animation-controller) for Node.js-specific documentation.

---

## Quick Start

```python
from animation_controller import (
    make_humanoid_skeleton,
    make_walk_clip,
    make_idle_clip,
    Animator,
)

# 1. Build a humanoid skeleton
skeleton = make_humanoid_skeleton()

# 2. Load clips
clips = {
    "walk": make_walk_clip(),
    "idle": make_idle_clip(),
}

# 3. Create an animator
animator = Animator(skeleton, clips)

# 4. Play a clip
animator.play("walk")

# 5. Drive the update loop (call once per frame with delta-time in seconds)
dt = 1.0 / 60.0          # 60 fps
for _ in range(60):
    animator.update(dt)

# 6. Export the current frame
frame = animator.export_frame()
print(frame)
```

Run the built-in demo:

```bash
python animation_controller.py
```

---

## API Reference

### Enums

#### `PlaybackState`

| Value | Description |
|---|---|
| `STOPPED` | Animator is stopped; no frame advance |
| `PLAYING` | Active playback |
| `PAUSED` | Playback suspended; time is frozen |
| `BLENDING` | Cross-fade between two clips in progress |

#### `LoopMode`

| Value | Description |
|---|---|
| `ONCE` | Play once and stop at the last frame |
| `LOOP` | Loop continuously from start |
| `PING_PONG` | Play forward, then backward, indefinitely |

#### `InterpolationType`

| Value | Description |
|---|---|
| `LINEAR` | Linear interpolation between keyframes |
| `CUBIC` | Smoothstep (cubic ease-in/out) interpolation |
| `STEP` | Hold previous keyframe value until the next |

---

### Bone

```python
@dataclass
class Bone:
    id: int
    name: str
    parent_id: Optional[int]
    length: float = 1.0
    rest_angle: float = 0.0
    current_angle: float = 0.0
    world_x: float = 0.0
    world_y: float = 0.0
    world_angle: float = 0.0
    weight: float = 1.0
```

**Properties**

| Property | Type | Description |
|---|---|---|
| `tip_x` | `float` | World X coordinate of the bone's distal end |
| `tip_y` | `float` | World Y coordinate of the bone's distal end |

**Methods**

| Method | Returns | Description |
|---|---|---|
| `to_dict()` | `dict` | Serialise bone state to a JSON-compatible dictionary |

---

### Skeleton

```python
class Skeleton:
    def __init__(self, bones: Optional[List[Bone]] = None)
```

**Attributes**

| Attribute | Type | Description |
|---|---|---|
| `bones` | `Dict[int, Bone]` | All bones keyed by bone ID |
| `root_x` | `float` | World X origin of the skeleton |
| `root_y` | `float` | World Y origin of the skeleton |

**Methods**

| Method | Returns | Description |
|---|---|---|
| `add_bone(bone)` | `None` | Add a bone to the skeleton |
| `get_bone(bone_id)` | `Optional[Bone]` | Look up a bone by integer ID |
| `get_bone_by_name(name)` | `Optional[Bone]` | Look up a bone by string name |
| `get_children(parent_id)` | `List[Bone]` | Return all direct children of a bone |
| `get_chain(end_bone_id)` | `List[Bone]` | Return the full chain from the root to the given bone |
| `root_bones()` | `List[Bone]` | Return all bones without a parent |
| `to_dict()` | `dict` | Serialise skeleton state to a JSON-compatible dictionary |

---

### Keyframe

```python
@dataclass
class Keyframe:
    time: float
    bone_angles: Dict[int, float]
    easing: InterpolationType = InterpolationType.LINEAR
```

| Attribute | Type | Description |
|---|---|---|
| `time` | `float` | Timestamp in seconds |
| `bone_angles` | `Dict[int, float]` | Mapping of bone ID → angle (radians) |
| `easing` | `InterpolationType` | Interpolation type applied from this keyframe to the next |

**Methods**

| Method | Returns | Description |
|---|---|---|
| `to_dict()` | `dict` | Serialise keyframe to a JSON-compatible dictionary |

---

### Clip

```python
@dataclass
class Clip:
    name: str
    keyframes: List[Keyframe] = field(default_factory=list)
    loop: bool = True
    fps: float = 24.0
    loop_mode: LoopMode = LoopMode.LOOP
```

**Properties**

| Property | Type | Description |
|---|---|---|
| `duration` | `float` | Time of the last keyframe in seconds |

**Methods**

| Method | Returns | Description |
|---|---|---|
| `add_keyframe(keyframe)` | `None` | Insert a keyframe (automatically sorted by time) |
| `sample(t)` | `Dict[int, float]` | Interpolate all bone angles at time `t` (seconds) |
| `to_dict()` | `dict` | Serialise clip metadata and keyframes to a JSON-compatible dictionary |

---

### Animator

```python
class Animator:
    def __init__(
        self,
        skeleton: Skeleton,
        clips: Optional[Dict[str, Clip]] = None,
    )
```

**Attributes**

| Attribute | Type | Description |
|---|---|---|
| `skeleton` | `Skeleton` | The skeleton being driven |
| `clips` | `Dict[str, Clip]` | Registered clips keyed by name |
| `state` | `PlaybackState` | Current playback state |
| `current_clip` | `Optional[str]` | Name of the active clip |
| `blend_clip` | `Optional[str]` | Name of the clip being blended in |
| `blend_alpha` | `float` | Current blend weight (`0.0` = current clip, `1.0` = blend clip) |

**Methods**

| Method | Signature | Description |
|---|---|---|
| `add_clip` | `(clip: Clip) → None` | Register a clip with the animator |
| `play` | `(clip_name, reset_time=True, speed=1.0) → None` | Begin playback of a named clip |
| `stop` | `() → None` | Stop playback and reset time to `0.0` |
| `pause` | `() → None` | Suspend playback without resetting time |
| `resume` | `() → None` | Resume playback from a paused state |
| `blend` | `(clip1, clip2, alpha) → None` | Instantly blend two clips by a fixed alpha weight |
| `transition_to` | `(clip_name, duration=0.3) → None` | Cross-fade from the current clip to a new clip over `duration` seconds |
| `update` | `(dt: float) → None` | Advance animation time by `dt` seconds and apply the resulting pose to the skeleton |
| `export_frame` | `() → dict` | Return a snapshot of the current time, state, blend alpha, and full skeleton pose |

---

### Forward Kinematics

```python
def calculate_forward_kinematics(skeleton: Skeleton) -> None
```

Performs a recursive depth-first traversal of the skeleton, computing the world-space position (`world_x`, `world_y`) and orientation (`world_angle`) of every bone from root to leaves. Must be called after manually modifying `current_angle` values or after `Animator.update()` if direct bone access is needed.

---

### Inverse Kinematics (FABRIK)

```python
def calculate_inverse_kinematics(
    skeleton: Skeleton,
    end_effector_id: int,
    target_x: float,
    target_y: float,
    iterations: int = 20,
    tolerance: float = 0.01,
) -> bool
```

Solves the bone chain ending at `end_effector_id` using the **FABRIK** (Forward And Backward Reaching Inverse Kinematics) algorithm.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `skeleton` | `Skeleton` | — | The skeleton to solve |
| `end_effector_id` | `int` | — | Bone ID of the chain's end effector |
| `target_x` | `float` | — | Target world X coordinate |
| `target_y` | `float` | — | Target world Y coordinate |
| `iterations` | `int` | `20` | Maximum solver iterations |
| `tolerance` | `float` | `0.01` | Convergence distance threshold |

**Returns** `True` if the end effector reached the target within `tolerance`, `False` otherwise.

---

### Preset Factories

| Function | Returns | Description |
|---|---|---|
| `make_humanoid_skeleton()` | `Skeleton` | 11-bone humanoid rig with FK pre-calculated |
| `make_walk_clip()` | `Clip` | 24-frame looping bipedal walk cycle at 24 fps |
| `make_idle_clip()` | `Clip` | 48-frame looping idle breathe animation at 24 fps |
| `make_jump_clip()` | `Clip` | 6-keyframe one-shot jump arc (crouch → launch → peak → fall → land → stand) |

---

## Examples

### Humanoid Skeleton + Walk Cycle

```python
from animation_controller import make_humanoid_skeleton, make_walk_clip, Animator

skeleton = make_humanoid_skeleton()
animator = Animator(skeleton, {"walk": make_walk_clip()})
animator.play("walk")

for frame in range(24):
    animator.update(1.0 / 24.0)
    spine = skeleton.get_bone_by_name("spine")
    print(f"Frame {frame:02d}: spine tip = ({spine.tip_x:.3f}, {spine.tip_y:.3f})")
```

### Blending Between Clips

```python
from animation_controller import (
    make_humanoid_skeleton, make_walk_clip, make_idle_clip, Animator
)

skeleton = make_humanoid_skeleton()
animator = Animator(skeleton, {
    "walk": make_walk_clip(),
    "idle": make_idle_clip(),
})

# 50/50 blend of walk and idle
animator.blend("walk", "idle", alpha=0.5)
animator.update(0.1)
```

### Smooth Transition

```python
from animation_controller import (
    make_humanoid_skeleton, make_walk_clip, make_jump_clip, Animator
)

skeleton = make_humanoid_skeleton()
animator = Animator(skeleton, {
    "walk": make_walk_clip(),
    "jump": make_jump_clip(),
})

animator.play("walk")
animator.transition_to("jump", duration=0.2)   # 200 ms cross-fade

for _ in range(30):
    animator.update(1.0 / 30.0)

frame = animator.export_frame()
print(f"Active clip: {frame['clip']}, State: {frame['state']}")
```

### IK Reach

```python
from animation_controller import (
    make_humanoid_skeleton,
    calculate_inverse_kinematics,
    calculate_forward_kinematics,
)

skeleton = make_humanoid_skeleton()
l_lower_arm = skeleton.get_bone_by_name("l_lower_arm")

converged = calculate_inverse_kinematics(
    skeleton, l_lower_arm.id,
    target_x=0.4, target_y=1.2,
    iterations=30, tolerance=0.005,
)
calculate_forward_kinematics(skeleton)

print(f"Converged: {converged}")
print(f"End effector tip: ({l_lower_arm.tip_x:.3f}, {l_lower_arm.tip_y:.3f})")
```

---

## Licensing & Commercial Use

This software is **proprietary and confidential**.

Copyright © 2024–2026 BlackRoad OS, Inc. All Rights Reserved.
Founder, CEO & Sole Stockholder: Alexa Louise Amundson.

**Personal / evaluation use** — permitted for review and non-commercial evaluation only.

**Commercial use** — requires a paid commercial license. Purchase a license or start a subscription directly through our Stripe billing portal:

> 🔗 **[Purchase a Commercial License — BlackRoad OS Stripe Portal](https://buy.stripe.com/blackroad-animation-controller)**

For volume licensing, enterprise agreements, white-label rights, or custom SLAs, contact us at **licensing@blackroad.io**.

For the full terms see the [`LICENSE`](./LICENSE) file included with this repository.

---

## Support

| Channel | Details |
|---|---|
| **Bug reports & feature requests** | [GitHub Issues](https://github.com/BlackRoad-Interactive/blackroad-animation-controller/issues) |
| **Commercial licensing** | licensing@blackroad.io |
| **General enquiries** | hello@blackroad.io |
| **Website** | [blackroad.io](https://blackroad.io) |

---

*BlackRoad Animation Controller is a product of BlackRoad OS, Inc. — Delaware C-Corporation.*
