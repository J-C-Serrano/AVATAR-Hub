"""Turn free-text feedback about a voice into parameter changes (rule-based, transparent).
Each rule: keywords -> parameter deltas. Matched deltas are summed; three variants are produced at
0.5x / 1x / 1.6x of that change so the user can hear a small, medium and large step."""
import random

LIMITS = {"lora_scale": (0.0, 2.2), "exaggeration": (0.25, 1.3), "temperature": (0.5, 1.0), "speed": (0.8, 1.25),
          "cfg_weight": (0.0, 0.7)}
RULES = [
    (("more accent", "stronger accent", "more like me", "sounds like me more", "more of me", "more my voice", "not like me",
      "doesn't sound like me", "more personal", "more salvador", "more latino", "more spanish"), {"lora_scale": +0.35}, "stronger personal style / accent"),
    (("less accent", "too much accent", "accent too strong", "too strong", "exaggerated accent", "clearer english", "more neutral"),
     {"lora_scale": -0.35}, "softer accent"),
    (("more expressive", "more emotion", "more energy", "livelier", "lively", "monotone", "flat", "boring", "more enthusiastic",
      "more excited", "dull"), {"exaggeration": +0.18}, "more expressive"),
    (("calmer", "calm", "less dramatic", "too emotional", "over the top", "too excited", "more relaxed", "softer"),
     {"exaggeration": -0.15}, "calmer delivery"),
    (("faster", "too slow", "speed up", "quicker"), {"speed": +0.07}, "faster pace"),
    (("slower", "too fast", "slow down", "rushed", "hurry"), {"speed": -0.07}, "slower pace"),
    (("robotic", "glitch", "artifact", "noise", "weird sound", "mumbl", "unclear", "clearer", "strange sound", "fart", "buzz"),
     {"temperature": -0.12}, "more stable / cleaner takes"),
    (("more natural", "more variation", "too perfect", "more human"), {"temperature": +0.08, "exaggeration": +0.05}, "more natural variation"),
    (("pauses", "breathe", "more pauses", "more space"), {"cfg_weight": +0.15}, "more measured phrasing"),
]
UNSUPPORTED = {("deeper", "higher pitch", "lower pitch", "pitch", "younger", "older"):
               "pitch/age can't be set directly yet; trying alternative reference clips of the same person instead"}


NICE = {"lora_scale": "personal style", "exaggeration": "expressiveness", "temperature": "variation", "speed": "speed",
        "cfg_weight": "phrasing"}


def interpret(text):
    t = (text or "").lower()
    delta, notes = {}, []
    for keys, d, label in RULES:
        if any(k in t for k in keys):
            for p, v in d.items(): delta[p] = delta.get(p, 0) + v
            notes.append(label)
    for keys, msg in UNSUPPORTED.items():
        if any(k in t for k in keys): notes.append(msg)
    return delta, notes


def variants(base, text, n_refs=0, seed=0):
    """-> list of (label, settings, explanation). Without a matching rule, vary reference clip / seed."""
    delta, notes = interpret(text)
    out = []
    if delta:
        for tag, f in (("A", 0.5), ("B", 1.0), ("C", 1.6)):
            s = dict(base)
            for p, v in delta.items():
                lo, hi = LIMITS[p]; s[p] = round(min(hi, max(lo, s.get(p, 0) + f * v)), 3)
            changes = ", ".join(f"{NICE[p]} {base.get(p)}→{s[p]}" for p in delta)
            out.append((tag, s, f"{'small' if f < 1 else 'medium' if f == 1 else 'large'} step: {changes}"))
    else:
        rnd = random.Random(seed)
        for tag in ("A", "B", "C"):
            s = dict(base); s["seed"] = rnd.randint(1, 10_000); s["ref_index"] = rnd.randint(0, max(0, n_refs - 1))
            out.append((tag, s, "same settings, different reference clip / take"))
        notes = notes or ["no specific change recognised: trying alternative takes and reference clips"]
    return out, notes
