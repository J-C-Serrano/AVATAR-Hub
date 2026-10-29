"""First-draft spoken.txt for a lecture remade from a recording: the recording's words (asr_long_words.py) split per
slide (pdf_states.py reveals.json), a [+] cue at the sentence where each build appeared, obvious fillers and
immediate repeats removed. The draft is then edited by hand into fluent text (keep the ### blocks and [+] cues).
usage: python3 script_draft.py <words.json> <reveals.json> <out spoken_draft.txt>"""
import json, re, sys
words, rev = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
FILL = re.compile(r"^(uh+|um+|uhm+|erm+|eh+|ehm+|ah+|hmm+|mm+|mhm)[,.?!]*$", re.I)


def sentences(ws):
    out, cur = [], []
    for w in ws:
        if FILL.match(w["w"]): continue
        if cur and re.sub(r"\W", "", cur[-1]["w"]).lower() == re.sub(r"\W", "", w["w"]).lower(): cur[-1] = w; continue
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]): out.append(cur); cur = []
    if cur: out.append(cur)
    return [{"t0": s[0]["t0"], "t1": s[-1]["t1"] or s[-1]["t0"], "text": " ".join(x["w"] for x in s)} for s in out]


blocks = []
for n in sorted(rev, key=int):
    r = rev[n]; t0, t1 = r["t0"], r["t1"]
    ss = sentences([w for w in words if w["t0"] is not None and t0 <= w["t0"] < t1])
    cue_at = set()
    for b in r["builds"]:        # cue at the sentence being spoken when the build appeared (next one if it was nearly over)
        i = next((k for k, s in enumerate(ss) if s["t1"] >= b), len(ss) - 1)
        if i >= 0 and ss and ss[i]["t1"] - b < 0.35 * (ss[i]["t1"] - ss[i]["t0"]) and i + 1 < len(ss): i += 1
        while i in cue_at and i + 1 < len(ss): i += 1
        cue_at.add(i)
    lines = [("[+] " if k in cue_at else "") + s["text"] for k, s in enumerate(ss)]
    extra = len(r["builds"]) - len(cue_at & set(range(len(ss))))
    lines += ["[+]"] * max(0, extra)
    blocks.append(f"### {n}   (rec {t0:.0f}-{t1:.0f} s, {len(r['builds'])} builds)\n" + ("\n".join(lines) if lines else "[silence 3]"))
open(sys.argv[3], "w").write("\n\n".join(blocks) + "\n")
print(sys.argv[3], len(blocks), "slides,", sum(len(rev[n]["builds"]) for n in rev), "builds")
