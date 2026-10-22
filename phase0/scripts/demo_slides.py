"""HTML slides for the Zoom-alternative demo (1920x1080): demo_slides.py <outdir>
writes intro.html, outro.html and body_<k>.html (one per reveal state of the support slide).
The avatar box on intro/outro is left empty; demo_compose.py overlays the video at AV_X, AV_Y, AV_S.
Voice-over slides keep a corner spot (CX, CY, CS) for the small nodding avatar circle, with a green "AI avatar" light."""
import os, sys
AV_X, AV_Y, AV_S = 150, 210, 660
CX, CY, CS = 1622, 40, 148
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;background:#0e1420;color:#e8edf5;font-family:'Ubuntu Sans','Ubuntu',sans-serif}
.k{color:#f0a028;font-weight:700;letter-spacing:.18em;font-size:26px;text-transform:uppercase}
h1{font-size:76px;line-height:1.08;font-weight:700;letter-spacing:-.01em}
h2{font-size:30px;font-weight:700;margin-bottom:22px}
.m{color:#9aa7bd}
.bar{position:absolute;left:0;top:0;width:1920px;height:10px;background:linear-gradient(90deg,#f0a028,#f0a02800)}
.foot{position:absolute;left:150px;right:150px;bottom:52px;display:flex;justify-content:space-between;font-size:22px;color:#6f7d95}
.av{position:absolute;border:6px solid #f0a028;border-radius:34px;background:#182235}
.badge{position:absolute;background:#f0a028;color:#0e1420;font-weight:700;font-size:22px;padding:8px 18px;border-radius:999px;letter-spacing:.06em}
.panel{position:absolute;background:#182235;border-radius:24px;padding:36px 40px;transition:none}
.li{display:flex;gap:18px;align-items:flex-start;font-size:29px;line-height:1.3;margin-bottom:20px}
.ic{flex:none;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;margin-top:-1px}
.x{background:#3a2430;color:#ff8a8a}.n{background:#f0a028;color:#0e1420}
.card{position:absolute;top:676px;width:384px;height:232px;background:#182235;border-radius:22px;padding:30px 32px;border:3px solid transparent}
.card b{display:block;font-size:40px;color:#f0a028;margin-bottom:12px}
.card span{font-size:26px;line-height:1.32;color:#cfd7e4}
.on{border-color:#f0a028;box-shadow:0 0 0 6px #f0a02822}
.hid{opacity:0}
.ring{position:absolute;border-radius:50%;border:4px solid #3ddc84;background:#182235}
.ai{position:absolute;display:flex;align-items:center;gap:8px;font-size:18px;font-weight:700;color:#3ddc84;letter-spacing:.04em}
.ai i{width:10px;height:10px;border-radius:50%;background:#3ddc84;box-shadow:0 0 8px #3ddc84}
.step{position:absolute;top:262px;height:400px;background:#182235;border-radius:24px;padding:36px 36px;border:3px solid transparent}
.step .no{font-size:24px;font-weight:700;color:#0e1420;background:#f0a028;border-radius:999px;padding:6px 16px;display:inline-block}
.step b{display:block;font-size:42px;margin:26px 0 16px}
.step span{display:block;font-size:28px;line-height:1.35;color:#cfd7e4}
.step.on{border-color:#f0a028}
.chip{display:inline-flex;align-items:center;gap:10px;margin-top:26px;padding:10px 18px;border-radius:999px;border:2px dashed #3ddc84;color:#3ddc84;font-size:24px}
.seg{position:absolute;top:720px;height:56px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700}
.banner{position:absolute;left:150px;right:150px;top:938px;height:84px;border-radius:18px;background:#f0a028;color:#0e1420;font-size:36px;font-weight:700;display:flex;align-items:center;justify-content:center}
"""
page = lambda body: f"<!doctype html><html><head><meta charset=utf-8><style>{CSS}</style></head><body><div class=bar></div>{body}</body></html>"
foot = "<div class=foot><span>AVATAR Hub · demo</span><span>Voice and avatar are AI-generated</span></div>"

def avatar_side(kicker, title, sub, extra=""):
    return page(f"""
<div class=badge style="left:{AV_X}px;top:{AV_Y - 58}px">AI avatar</div>
<div class=av style="left:{AV_X - 6}px;top:{AV_Y - 6}px;width:{AV_S + 12}px;height:{AV_S + 12}px"></div>
<div style="position:absolute;left:{AV_X + AV_S + 110}px;right:150px;top:300px">
 <div class=k>{kicker}</div><h1 style="margin-top:26px">{title}</h1>
 <div class=m style="font-size:36px;line-height:1.35;margin-top:34px">{sub}</div>{extra}
</div>{foot}""")

INTRO = avatar_side("Demo", "From Zoom recordings<br>to written lectures",
                    "A voice and avatar tool that lets teachers write a lecture instead of recording it.",
                    "<div style='margin-top:60px;font-size:28px;color:#6f7d95'>Presented by Julio Serrano’s AI avatar</div>")
OUTRO = avatar_side("Thank you", "Thanks for watching",
                    "I hope this was useful.",
                    "<div style='margin-top:70px;font-size:30px;line-height:1.6;color:#cfd7e4'>Write the lecture<br>Keep your own voice<br>Keep your data at the university</div>")

ZOOM = ["An hour in front of a webcam", "One stumble, start again", "Small window, uneven sound",
        "Re-record when one figure changes"]
FLOW = ["Write the script, slide by slide", "Your trained voice reads it", "Every sentence checked by speech recognition",
        "The avatar presents, marked as AI"]
CARDS = [("Time", "Fix a sentence by editing text. Updates take minutes."),
         ("Quality", "Clean, steady sound. Short, focused parts."),
         ("Reach", "Script becomes subtitles and searchable notes."),
         ("Control", "Runs on our own hardware in Finland.")]
corner = (f"<div class=ring style='left:{CX - 4}px;top:{CY - 4}px;width:{CS + 8}px;height:{CS + 8}px'></div>"
          f"<div class=ai style='left:{CX + 22}px;top:{CY + CS + 12}px'><i></i>AI avatar</div>")
# reveal states: 0 zoom panel, 1 tool panel, 2..5 cards, 6 banner
def body(st):
    vis = lambda i: "" if st >= i else " hid"
    lis = lambda items, cls, mark: "".join(f"<div class=li><div class='ic {cls}'>{mark(i)}</div><div>{t}</div></div>" for i, t in enumerate(items))
    cards = "".join(f"<div class='card{' on' if st == 2 + i else ''}{vis(2 + i)}' style='left:{150 + i * 412}px'><b>{h}</b><span>{t}</span></div>"
                    for i, (h, t) in enumerate(CARDS))
    return page(f"""
<div style="position:absolute;left:150px;top:64px"><div class=k>Why it matters</div>
 <h1 style="font-size:62px;margin-top:14px">Write your lecture instead of recording it</h1></div>
<div class='panel{" on" if st == 0 else ""}{vis(0)}' style="left:150px;top:248px;width:770px;height:392px;border:3px solid {'#f0a028' if st == 0 else 'transparent'}">
 <h2 class=m>Recording over Zoom</h2>{lis(ZOOM, "x", lambda i: "✕")}</div>
<div class='panel{vis(1)}' style="left:1000px;top:248px;width:770px;height:392px;border:3px solid {'#f0a028' if st == 1 else 'transparent'}">
 <h2 style="color:#f0a028">With this tool</h2>{lis(FLOW, "n", lambda i: i + 1)}</div>
{cards}
<div class='banner{vis(6)}'>It replaces the recording session, not the teaching.</div>{corner}""")

# how a lecture is built; states: 0 title + timeline, 1 avatar steps, 2 voice-over step, 3 optional face, 4 banner
def process(st):
    vis = lambda i: "" if st >= i else " hid"
    on = lambda i: " on" if st == i else ""
    return page(f"""
<div style="position:absolute;left:150px;top:64px"><div class=k>How a lecture is built</div>
 <h1 style="font-size:62px;margin-top:14px">Avatar, voice-over, avatar</h1></div>
<div class='step{on(1)}{vis(1)}' style="left:150px;width:420px"><div class=no>Start</div><b>Avatar opens</b>
 <span>On camera, in your voice: welcome and what the lecture covers.</span></div>
<div class='step{on(2)}{on(3)}{vis(2)}' style="left:610px;width:700px"><div class=no>Main part</div><b>Slides + voice-over</b>
 <span>Your trained voice reads the script while the slides run.</span>
 <div class='chip{vis(3)}'><i style="width:10px;height:10px;border-radius:50%;background:#3ddc84"></i>Optional: small nodding avatar face</div></div>
<div class='step{on(1)}{vis(1)}' style="left:1350px;width:420px"><div class=no>End</div><b>Avatar closes</b>
 <span>On camera again: thanks and a short summary.</span></div>
<div class='seg{vis(1)}' style="left:150px;width:420px;background:#f0a028;color:#0e1420">avatar</div>
<div class='seg{vis(2)}' style="left:610px;width:700px;background:#2a3a57;color:#e8edf5">voice-over</div>
<div class='seg{vis(1)}' style="left:1350px;width:420px;background:#f0a028;color:#0e1420">avatar</div>
<div class='banner{vis(4)}' style="top:880px">This demo follows exactly the same structure.</div>{corner}""")

STEPS = [("First meeting", "The teacher contacts us and books a meeting."),
         ("Needs and fit", "We discuss what the course needs and check that an avatar fits."),
         ("Studio session", "We record video, photos and audio in our studio."),
         ("Avatar + voice", "The avatar and the voice are cloned and personalised."),
         ("Lessons", "The teacher sends scripts and slides. We build the lessons.")]
# our service; states: 0 title, 1..5 steps (current one highlighted, 5 also shows the summary banner)
def service(st):
    vis = lambda i: "" if st >= i else " hid"
    cards = "".join(f"<div class='step{' on' if st == i + 1 else ''}{vis(i + 1)}' style='left:{150 + i * 330}px;width:300px;height:360px;padding:30px 28px'>"
                    f"<div class=no>{i + 1}</div><b style='font-size:34px;margin:24px 0 14px'>{h}</b><span style='font-size:25px'>{t}</span></div>"
                    for i, (h, t) in enumerate(STEPS))
    arrows = "".join(f"<div class='{vis(i + 2).strip()}' style='position:absolute;left:{150 + i * 330 + 302}px;top:420px;width:26px;text-align:center;"
                     f"font-size:30px;color:#f0a028'>›</div>" for i in range(4))
    return page(f"""
<div style="position:absolute;left:150px;top:64px"><div class=k>Our service</div>
 <h1 style="font-size:62px;margin-top:14px">From first meeting to finished lessons</h1></div>
{cards}{arrows}
<div class='banner{vis(5)}' style="top:700px;font-size:32px">The teacher’s part: one meeting, one studio session, then scripts and slides.</div>{corner}""")

if __name__ == "__main__":
    d = sys.argv[1]; os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "intro.html"), "w").write(INTRO)
    open(os.path.join(d, "outro.html"), "w").write(OUTRO)
    for st in range(7): open(os.path.join(d, f"body_{st}.html"), "w").write(body(st))
    for st in range(5): open(os.path.join(d, f"process_{st}.html"), "w").write(process(st))
    for st in range(6): open(os.path.join(d, f"service_{st}.html"), "w").write(service(st))
    print("wrote", d)
