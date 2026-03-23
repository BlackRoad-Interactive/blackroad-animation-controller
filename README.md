# blackroad-animation-controller

> Skeletal and sprite animation controller

Part of the [BlackRoad OS](https://blackroad.io) ecosystem — [BlackRoad-Interactive](https://github.com/BlackRoad-Interactive)

---

# BlackRoad Animation Controller

Skeletal animation system with Forward Kinematics, FABRIK IK, clip blending, and humanoid presets.

## Features

- **Skeleton**: Hierarchical bone system with parent/child relationships
- **Forward Kinematics**: Full FK traversal with world position/angle calculation
- **Inverse Kinematics**: FABRIK algorithm with configurable iterations
- **Animation Clips**: Keyframe-based clips with linear/cubic/step easing
- **Loop Modes**: Once, loop, ping-pong
- **Animator**: play, pause, stop, blend, transition_to with smooth cross-fading
- **Presets**: Humanoid skeleton, walk cycle, idle, jump clips

## Usage

```bash
python animation_controller.py
```

## License

Proprietary — BlackRoad OS, Inc. All rights reserved.
