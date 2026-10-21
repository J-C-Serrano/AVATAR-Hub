"""HTML slides for the Zoom-alternative demo (1920x1080): demo_slides.py <outdir>
writes intro.html, outro.html and body_<k>.html (one per reveal state of the support slide).
The avatar box on intro/outro is left empty; compose_demo.sh overlays the video at AV_X, AV_Y, AV_S."""
import os, sys
AV_X, AV_Y, AV_S = 150, 210, 660
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
<div class='banner{vis(6)}'>It replaces the recording session, not the teaching.</div>""")

if __name__ == "__main__":
    d = sys.argv[1]; os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "intro.html"), "w").write(INTRO)
    open(os.path.join(d, "outro.html"), "w").write(OUTRO)
    for st in range(7): open(os.path.join(d, f"body_{st}.html"), "w").write(body(st))
    print("wrote", d)
