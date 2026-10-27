"""Flag lines of a lecture script where the avatar would speak as the real teacher (rule: the avatar knows it is an avatar).
usage: python3 script_lint.py <spoken.txt>
Contact, questions, email, sharing material, meeting students, "see you next week": only the real person can do these,
so the line must name the teacher instead ("you can let <Name> know", "<Name>'s email address"). Exit code 1 if anything
is flagged. Opinions and lecture content in the first person ("I think", "I recommend this book") are listed separately
as notes; they may stay."""
import re, sys
MUST = [r"\blet me know\b", r"\b(contact|email|e-mail|mail|message|call|ask|tell|reach|write to|text|ping) me\b", r"\bmy (e-?mail|email address|office|phone|number|contact)",
        r"\bsend (it |them |this )?(to )?me\b", r"\bI('ll| will) (see|meet|answer|reply|send|share|upload|post|grade|check|read|be (there|available))",
        r"\bsee you\b", r"\b(come|drop) (to|by) (me|my)\b", r"\bwith me\b", r"\bI('m| am) (available|here for you|happy to (help|answer))",
        r"\b(that|what) I (was )?(present|show|shar)(ed|ing)\b"]
NOTE = [r"\bI (think|believe|recommend|would like|want|took|will be)\b", r"\bin my (opinion|view|experience)\b", r"\bmy (book|paper|research|students|class)\b"]
bad = set(); slide = None
for ln, line in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
    if line.startswith("### "): slide = line[4:].strip(); continue
    for kind, pats in (("FIX", MUST), ("note", NOTE)):
        for p in pats:
            for m in re.finditer(p, line, re.I):
                s = max(0, m.start() - 50); print(f"{kind} slide {slide} line {ln}: ...{line[s:m.end() + 50].strip()}...")
                if kind == "FIX": bad.add(ln)
print(f"{len(bad)} line(s) to rewrite"); sys.exit(1 if bad else 0)
