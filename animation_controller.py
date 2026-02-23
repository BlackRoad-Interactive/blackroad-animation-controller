"""
BlackRoad Animation Controller
Skeletal animation with FK/IK, clip blending, and sprite support.
"""

import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlaybackState(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BLENDING = "blending"


class LoopMode(str, Enum):
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"


class InterpolationType(str, Enum):
    LINEAR = "linear"
    STEP = "step"
    CUBIC = "cubic"


# ---------------------------------------------------------------------------
# Bone
# ---------------------------------------------------------------------------

@dataclass
class Bone:
    """A single bone in a skeleton."""
    id: int
    name: str
    parent_id: Optional[int]
    length: float = 1.0
    rest_angle: float = 0.0       # radians, default orientation
    current_angle: float = 0.0    # current animated angle
    world_x: float = 0.0
    world_y: float = 0.0
    world_angle: float = 0.0
    weight: float = 1.0           # for blending

    @property
    def tip_x(self) -> float:
        return self.world_x + self.length * math.cos(self.world_angle)

    @property
    def tip_y(self) -> float:
        return self.world_y + self.length * math.sin(self.world_angle)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "length": self.length,
            "rest_angle": round(self.rest_angle, 4),
            "current_angle": round(self.current_angle, 4),
            "world_x": round(self.world_x, 4),
            "world_y": round(self.world_y, 4),
            "world_angle": round(self.world_angle, 4),
            "tip": (round(self.tip_x, 4), round(self.tip_y, 4)),
        }


# ---------------------------------------------------------------------------
# Skeleton
# ---------------------------------------------------------------------------

class Skeleton:
    """Hierarchical bone structure."""

    def __init__(self, bones: Optional[List[Bone]] = None):
        self.bones: Dict[int, Bone] = {}
        self.root_x: float = 0.0
        self.root_y: float = 0.0
        if bones:
            for b in bones:
                self.bones[b.id] = b

    def add_bone(self, bone: Bone):
        self.bones[bone.id] = bone

    def get_bone(self, bone_id: int) -> Optional[Bone]:
        return self.bones.get(bone_id)

    def get_bone_by_name(self, name: str) -> Optional[Bone]:
        for b in self.bones.values():
            if b.name == name:
                return b
        return None

    def get_children(self, parent_id: int) -> List[Bone]:
        return [b for b in self.bones.values() if b.parent_id == parent_id]

    def get_chain(self, end_bone_id: int) -> List[Bone]:
        """Return chain from root to end_bone_id."""
        chain = []
        bid = end_bone_id
        visited = set()
        while bid is not None and bid not in visited:
            bone = self.get_bone(bid)
            if not bone:
                break
            chain.append(bone)
            visited.add(bid)
            bid = bone.parent_id
        return chain[::-1]

    def root_bones(self) -> List[Bone]:
        return [b for b in self.bones.values() if b.parent_id is None]

    def to_dict(self) -> dict:
        return {
            "root": (self.root_x, self.root_y),
            "bones": [b.to_dict() for b in sorted(self.bones.values(), key=lambda b: b.id)],
        }


# ---------------------------------------------------------------------------
# FK
# ---------------------------------------------------------------------------

def calculate_forward_kinematics(skeleton: Skeleton):
    """Update world positions of all bones via FK traversal."""
    def _process(bone_id: int, parent_world_x: float, parent_world_y: float, parent_world_angle: float):
        bone = skeleton.get_bone(bone_id)
        if not bone:
            return
        bone.world_x = parent_world_x
        bone.world_y = parent_world_y
        bone.world_angle = parent_world_angle + bone.rest_angle + bone.current_angle
        # Process children
        for child in skeleton.get_children(bone_id):
            _process(child.id, bone.tip_x, bone.tip_y, bone.world_angle)

    for root_bone in skeleton.root_bones():
        _process(root_bone.id, skeleton.root_x, skeleton.root_y, 0.0)


# ---------------------------------------------------------------------------
# IK — FABRIK
# ---------------------------------------------------------------------------

def calculate_inverse_kinematics(
    skeleton: Skeleton,
    end_effector_id: int,
    target_x: float,
    target_y: float,
    iterations: int = 20,
    tolerance: float = 0.01,
) -> bool:
    """
    FABRIK (Forward And Backward Reaching Inverse Kinematics).
    Returns True if converged within tolerance.
    """
    chain = skeleton.get_chain(end_effector_id)
    if len(chain) < 2:
        return False

    # Collect current positions
    positions: List[Tuple[float, float]] = []
    for bone in chain:
        positions.append((bone.world_x, bone.world_y))
    # Add tip of last bone
    last = chain[-1]
    positions.append((last.tip_x, last.tip_y))

    bone_lengths = [b.length for b in chain]
    root_pos = positions[0]
    target = (target_x, target_y)

    # Total chain length
    total_length = sum(bone_lengths)
    dist_to_target = math.dist(root_pos, target)

    if dist_to_target > total_length:
        # Target out of reach — stretch toward it
        for i in range(len(positions) - 1):
            r = math.dist(positions[i], target)
            lam = bone_lengths[i] / (r if r > 0 else 1e-9)
            nx = (1 - lam) * positions[i][0] + lam * target[0]
            ny = (1 - lam) * positions[i][1] + lam * target[1]
            positions[i + 1] = (nx, ny)
    else:
        for _ in range(iterations):
            # Forward reaching
            positions[-1] = target
            for i in range(len(positions) - 2, -1, -1):
                r = math.dist(positions[i], positions[i + 1])
                lam = bone_lengths[i] / (r if r > 0 else 1e-9)
                nx = (1 - lam) * positions[i + 1][0] + lam * positions[i][0]
                ny = (1 - lam) * positions[i + 1][1] + lam * positions[i][1]
                positions[i] = (nx, ny)
            # Backward reaching
            positions[0] = root_pos
            for i in range(len(positions) - 1):
                r = math.dist(positions[i], positions[i + 1])
                lam = bone_lengths[i] / (r if r > 0 else 1e-9)
                nx = (1 - lam) * positions[i][0] + lam * positions[i + 1][0]
                ny = (1 - lam) * positions[i][1] + lam * positions[i + 1][1]
                positions[i + 1] = (nx, ny)

            if math.dist(positions[-1], target) < tolerance:
                break

    # Apply positions back to bones as angles
    for i, bone in enumerate(chain):
        px, py = positions[i]
        qx, qy = positions[i + 1]
        dx, dy = qx - px, qy - py
        world_angle = math.atan2(dy, dx)
        parent_world_angle = 0.0
        if bone.parent_id is not None:
            parent = skeleton.get_bone(bone.parent_id)
            if parent:
                parent_world_angle = parent.world_angle
        bone.current_angle = world_angle - parent_world_angle - bone.rest_angle
        bone.world_x = px
        bone.world_y = py
        bone.world_angle = world_angle

    # Final tip of last bone
    last_bone = chain[-1]
    qx, qy = positions[-1]

    return math.dist(positions[-1], target) < tolerance


# ---------------------------------------------------------------------------
# Keyframe & Clip
# ---------------------------------------------------------------------------

@dataclass
class Keyframe:
    """A single keyframe of bone angles at a given time."""
    time: float                          # seconds
    bone_angles: Dict[int, float]        # bone_id → angle
    easing: InterpolationType = InterpolationType.LINEAR

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "bone_angles": {str(k): round(v, 4) for k, v in self.bone_angles.items()},
            "easing": self.easing.value,
        }


@dataclass
class Clip:
    """Animation clip containing keyframes."""
    name: str
    keyframes: List[Keyframe] = field(default_factory=list)
    loop: bool = True
    fps: float = 24.0
    loop_mode: LoopMode = LoopMode.LOOP

    @property
    def duration(self) -> float:
        if not self.keyframes:
            return 0.0
        return self.keyframes[-1].time

    def add_keyframe(self, keyframe: Keyframe):
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda k: k.time)

    def sample(self, t: float) -> Dict[int, float]:
        """Interpolate bone angles at time t."""
        if not self.keyframes:
            return {}

        # Handle looping
        duration = self.duration
        if duration > 0:
            if self.loop_mode == LoopMode.LOOP:
                t = t % duration
            elif self.loop_mode == LoopMode.PING_PONG:
                cycle = t % (duration * 2)
                t = cycle if cycle <= duration else duration * 2 - cycle
            else:
                t = min(t, duration)

        # Find surrounding keyframes
        kfs = self.keyframes
        if t <= kfs[0].time:
            return dict(kfs[0].bone_angles)
        if t >= kfs[-1].time:
            return dict(kfs[-1].bone_angles)

        for i in range(len(kfs) - 1):
            k0, k1 = kfs[i], kfs[i + 1]
            if k0.time <= t <= k1.time:
                span = k1.time - k0.time
                alpha = (t - k0.time) / span if span > 0 else 0.0
                # Cubic ease
                if k0.easing == InterpolationType.CUBIC:
                    alpha = alpha * alpha * (3 - 2 * alpha)
                elif k0.easing == InterpolationType.STEP:
                    alpha = 0.0

                result = {}
                all_ids = set(k0.bone_angles) | set(k1.bone_angles)
                for bid in all_ids:
                    a0 = k0.bone_angles.get(bid, 0.0)
                    a1 = k1.bone_angles.get(bid, 0.0)
                    result[bid] = a0 + (a1 - a0) * alpha
                return result

        return dict(kfs[-1].bone_angles)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": self.duration,
            "fps": self.fps,
            "loop": self.loop,
            "loop_mode": self.loop_mode.value,
            "keyframes": [k.to_dict() for k in self.keyframes],
        }


# ---------------------------------------------------------------------------
# Animator
# ---------------------------------------------------------------------------

class Animator:
    """Controls playback and blending of animation clips on a skeleton."""

    def __init__(self, skeleton: Skeleton, clips: Optional[Dict[str, Clip]] = None):
        self.skeleton = skeleton
        self.clips: Dict[str, Clip] = clips or {}
        self.state: PlaybackState = PlaybackState.STOPPED
        self.current_clip: Optional[str] = None
        self.blend_clip: Optional[str] = None
        self.blend_alpha: float = 0.0
        self._time: float = 0.0
        self._speed: float = 1.0
        self._blend_duration: float = 0.0
        self._blend_time: float = 0.0

    def add_clip(self, clip: Clip):
        self.clips[clip.name] = clip

    def play(self, clip_name: str, reset_time: bool = True, speed: float = 1.0):
        if clip_name not in self.clips:
            raise ValueError(f"Clip '{clip_name}' not found")
        self.current_clip = clip_name
        self.state = PlaybackState.PLAYING
        self._speed = speed
        self.blend_clip = None
        self.blend_alpha = 0.0
        if reset_time:
            self._time = 0.0

    def stop(self):
        self.state = PlaybackState.STOPPED
        self._time = 0.0
        self.current_clip = None

    def pause(self):
        if self.state == PlaybackState.PLAYING:
            self.state = PlaybackState.PAUSED

    def resume(self):
        if self.state == PlaybackState.PAUSED:
            self.state = PlaybackState.PLAYING

    def blend(self, clip1: str, clip2: str, alpha: float):
        """Instantly blend between two clips with alpha (0=clip1, 1=clip2)."""
        if clip1 not in self.clips or clip2 not in self.clips:
            raise ValueError("One or more clips not found")
        self.current_clip = clip1
        self.blend_clip = clip2
        self.blend_alpha = max(0.0, min(1.0, alpha))
        self.state = PlaybackState.BLENDING

    def transition_to(self, clip_name: str, duration: float = 0.3):
        """Smooth transition from current clip to a new one over duration seconds."""
        if clip_name not in self.clips:
            raise ValueError(f"Clip '{clip_name}' not found")
        if self.current_clip:
            self.blend_clip = clip_name
            self._blend_duration = duration
            self._blend_time = 0.0
            self.state = PlaybackState.BLENDING
        else:
            self.play(clip_name)

    def update(self, dt: float):
        """Advance animation time and apply to skeleton."""
        if self.state == PlaybackState.STOPPED or self.state == PlaybackState.PAUSED:
            return
        self._time += dt * self._speed

        if self.state == PlaybackState.BLENDING and self._blend_duration > 0:
            self._blend_time += dt
            self.blend_alpha = min(1.0, self._blend_time / self._blend_duration)
            if self.blend_alpha >= 1.0:
                self.current_clip = self.blend_clip
                self.blend_clip = None
                self.blend_alpha = 0.0
                self.state = PlaybackState.PLAYING

        # Sample current pose
        if self.current_clip and self.current_clip in self.clips:
            clip = self.clips[self.current_clip]
            pose = clip.sample(self._time)
            # Blend if needed
            if self.blend_clip and self.blend_clip in self.clips:
                blend_pose = self.clips[self.blend_clip].sample(self._time)
                all_ids = set(pose) | set(blend_pose)
                blended = {}
                for bid in all_ids:
                    a = pose.get(bid, 0.0)
                    b = blend_pose.get(bid, 0.0)
                    blended[bid] = a + (b - a) * self.blend_alpha
                pose = blended

            # Apply angles to skeleton
            for bone_id, angle in pose.items():
                bone = self.skeleton.get_bone(bone_id)
                if bone:
                    bone.current_angle = angle

            calculate_forward_kinematics(self.skeleton)

    def export_frame(self) -> dict:
        """Export current skeleton pose."""
        calculate_forward_kinematics(self.skeleton)
        return {
            "time": round(self._time, 4),
            "clip": self.current_clip,
            "state": self.state.value,
            "blend_alpha": round(self.blend_alpha, 4),
            "skeleton": self.skeleton.to_dict(),
        }


# ---------------------------------------------------------------------------
# Preset skeletons & clips
# ---------------------------------------------------------------------------

def make_humanoid_skeleton() -> Skeleton:
    """Create a simple humanoid skeleton."""
    sk = Skeleton()
    BONES = [
        Bone(0, "root",         None, length=0.1, rest_angle=0.0),
        Bone(1, "spine",        0,    length=0.5, rest_angle=math.pi/2),
        Bone(2, "head",         1,    length=0.3, rest_angle=math.pi/2),
        Bone(3, "l_upper_arm",  1,    length=0.4, rest_angle=math.pi),
        Bone(4, "l_lower_arm",  3,    length=0.35, rest_angle=0.0),
        Bone(5, "r_upper_arm",  1,    length=0.4, rest_angle=0.0),
        Bone(6, "r_lower_arm",  5,    length=0.35, rest_angle=0.0),
        Bone(7, "l_upper_leg",  0,    length=0.45, rest_angle=-math.pi/2),
        Bone(8, "l_lower_leg",  7,    length=0.4,  rest_angle=0.0),
        Bone(9, "r_upper_leg",  0,    length=0.45, rest_angle=-math.pi/2),
        Bone(10,"r_lower_leg",  9,    length=0.4,  rest_angle=0.0),
    ]
    for b in BONES:
        sk.add_bone(b)
    calculate_forward_kinematics(sk)
    return sk


def make_walk_clip() -> Clip:
    """Create a simple bipedal walk cycle."""
    clip = Clip(name="walk", fps=24.0, loop=True, loop_mode=LoopMode.LOOP)
    amplitude = 0.4
    for frame in range(24):
        t = frame / 24.0
        phase = 2 * math.pi * t
        kf = Keyframe(
            time=t,
            bone_angles={
                1: math.sin(phase) * 0.05,                    # spine sway
                7: math.sin(phase) * amplitude,                # l_upper_leg
                8: max(0, -math.sin(phase)) * amplitude * 0.5,
                9: math.sin(phase + math.pi) * amplitude,      # r_upper_leg
                10: max(0, math.sin(phase)) * amplitude * 0.5,
                3: math.sin(phase + math.pi) * amplitude * 0.5,
                5: math.sin(phase) * amplitude * 0.5,
            },
            easing=InterpolationType.CUBIC,
        )
        clip.add_keyframe(kf)
    return clip


def make_idle_clip() -> Clip:
    clip = Clip(name="idle", fps=24.0, loop=True)
    for frame in range(48):
        t = frame / 24.0
        breathe = math.sin(2 * math.pi * t / 2.0) * 0.03
        clip.add_keyframe(Keyframe(
            time=t,
            bone_angles={1: breathe, 2: breathe * 0.5},
            easing=InterpolationType.CUBIC,
        ))
    return clip


def make_jump_clip() -> Clip:
    clip = Clip(name="jump", fps=24.0, loop=False, loop_mode=LoopMode.ONCE)
    keyframes = [
        (0.0,  {7: -0.6, 8: 1.0, 9: -0.6, 10: 1.0, 1: -0.3}),   # crouch
        (0.15, {7: 0.3,  8: 0.0, 9: 0.3,  10: 0.0, 1:  0.2}),    # launch
        (0.4,  {7: 0.5,  8: 0.2, 9: 0.5,  10: 0.2, 1:  0.3}),    # peak
        (0.7,  {7: -0.4, 8: 0.8, 9: -0.4, 10: 0.8, 1: -0.1}),    # fall
        (0.9,  {7: -0.5, 8: 1.0, 9: -0.5, 10: 1.0, 1: -0.2}),    # land
        (1.0,  {7: 0.0,  8: 0.0, 9: 0.0,  10: 0.0, 1:  0.0}),    # stand
    ]
    for t, angles in keyframes:
        clip.add_keyframe(Keyframe(time=t, bone_angles=angles, easing=InterpolationType.CUBIC))
    return clip


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    print("=== BlackRoad Animation Controller Demo ===")

    sk = make_humanoid_skeleton()
    print(f"\nSkeleton: {len(sk.bones)} bones")
    for bone in sorted(sk.bones.values(), key=lambda b: b.id):
        print(f"  [{bone.id}] {bone.name:15s} parent={bone.parent_id}  len={bone.length}")

    # FK test
    calculate_forward_kinematics(sk)
    spine = sk.get_bone_by_name("spine")
    print(f"\nSpine tip after FK: ({spine.tip_x:.3f}, {spine.tip_y:.3f})")

    # IK test
    print("\n[IK] Moving l_lower_arm to (0.4, 1.2)...")
    l_lower = sk.get_bone_by_name("l_lower_arm")
    converged = calculate_inverse_kinematics(sk, l_lower.id, 0.4, 1.2, iterations=30)
    calculate_forward_kinematics(sk)
    print(f"  Converged: {converged}, tip: ({l_lower.tip_x:.3f}, {l_lower.tip_y:.3f})")

    # Clips
    walk_clip = make_walk_clip()
    idle_clip = make_idle_clip()
    jump_clip = make_jump_clip()
    print(f"\nWalk clip: {walk_clip.duration:.2f}s, {len(walk_clip.keyframes)} keyframes")
    print(f"Idle clip: {idle_clip.duration:.2f}s, {len(idle_clip.keyframes)} keyframes")
    print(f"Jump clip: {jump_clip.duration:.2f}s, {len(jump_clip.keyframes)} keyframes")

    # Animator
    anim = Animator(sk, {"walk": walk_clip, "idle": idle_clip, "jump": jump_clip})

    # Play walk
    anim.play("walk")
    for i in range(5):
        anim.update(0.1)
        frame = anim.export_frame()
        print(f"  t={frame['time']:.2f}s  clip={frame['clip']}  spine_angle={sk.get_bone(1).current_angle:.3f}")

    # Blend to idle
    print("\n[Blending walk → idle]")
    anim.blend("walk", "idle", alpha=0.5)
    anim.update(0.2)
    frame = anim.export_frame()
    print(f"  blend_alpha={frame['blend_alpha']}, state={frame['state']}")

    # Transition to jump
    print("\n[Transition to jump (0.2s)]")
    anim.play("walk")
    anim.transition_to("jump", duration=0.2)
    for i in range(10):
        anim.update(0.05)
    frame = anim.export_frame()
    print(f"  After transition: clip={frame['clip']}, state={frame['state']}")

    # Sample walk at various times
    print("\n[Walk clip sample at t=0.25, 0.5, 0.75]")
    for t in [0.0, 0.25, 0.5, 0.75]:
        pose = walk_clip.sample(t)
        print(f"  t={t:.2f}: l_upper_leg={pose.get(7, 0.0):.3f}  r_upper_leg={pose.get(9, 0.0):.3f}")

    # Export frame
    print("\n[Exported frame (skeleton snippet)]")
    snap = anim.export_frame()
    bones_snap = snap["skeleton"]["bones"][:3]
    for b in bones_snap:
        print(f"  {b['name']}: world=({b['world_x']:.3f},{b['world_y']:.3f}) tip={b['tip']}")


if __name__ == "__main__":
    demo()
