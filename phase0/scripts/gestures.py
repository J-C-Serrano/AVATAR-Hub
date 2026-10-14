"""Gesture library for the MPFB/TalkingHead-compatible rig (Mixamo-style bone names).
Angles in degrees as Blender pose-bone XYZ Euler deltas from the A-pose rest. Written for the
character's RIGHT side; LEFT is mirrored automatically (y, z negated).
Learned from debug renders (scripts/blender_axes.py): Arm y- lowers arm to the side, Arm x- raises it
sideways; with arm lowered, ForeArm x- lifts the hand forward/up, ForeArm z- brings it across the body."""

IDLE_R = {"Arm": (6, -66, 0), "ForeArm": (-18, 0, 0), "Hand": (0, 0, 0)}

# each gesture: dict side -> {bone: euler}; sides "R", "L" (unspecified side stays idle)
GESTURES = {
    "open_palms": {"R": {"Arm": (0, -52, -12), "ForeArm": (-55, 0, 10), "Hand": (0, 0, 0)},
                   "L": {"Arm": (0, -52, -12), "ForeArm": (-55, 0, 10), "Hand": (0, 0, 0)}},
    "wave":       {"R": {"Arm": (-25, -25, 0), "ForeArm": (-105, 0, 0), "Hand": (0, 0, 0)}},
    "point_slide": {"R": {"Arm": (-35, -15, -20), "ForeArm": (-15, 0, 0), "Hand": (0, 0, 0)}},
    "hand_chest": {"R": {"Arm": (10, -45, -10), "ForeArm": (-45, 0, -95), "Hand": (0, 0, 0)}},
    "count":      {"R": {"Arm": (0, -48, -15), "ForeArm": (-110, 0, 10), "Hand": (0, 0, 0)}},
    "shrug":      {"R": {"Arm": (0, -58, 0), "ForeArm": (-40, 0, 30), "Hand": (0, 0, 0)},
                   "L": {"Arm": (0, -58, 0), "ForeArm": (-40, 0, 30), "Hand": (0, 0, 0)}},
}
# small oscillation while a gesture is held: (side, bone, axis, amplitude deg, Hz)
WIGGLE = {"wave": ("R", "ForeArm", 2, 22, 2.2), "count": ("R", "ForeArm", 0, 6, 1.5),
          "open_palms": ("R", "ForeArm", 0, 5, 0.8)}


def mirror(e):
    return (e[0], -e[1], -e[2])


def pose(name=None):
    """Full arm pose {bone_name: euler} for a gesture (None = idle)."""
    out = {}
    g = GESTURES.get(name, {}) if name else {}
    for side, pre in (("R", "Right"), ("L", "Left")):
        src = g.get(side, IDLE_R)
        for bone, e in src.items():
            out[pre + bone] = e if side == "R" else mirror(e)
    return out
