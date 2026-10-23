"""Render build-up states of a teacher's .pptx without changing its layout (the original file is never modified).
usage: python3 deck_build.py <deck.pptx> <out dir> [--width 1920]
Per slide, "units" appear one after another: each top-level paragraph of a body text (with its sub-bullets), each
other text box, and each large picture/group. Titles, footers and small pictures (decoration, < 6% of the slide)
are always shown. Hidden text is made fully transparent (text + bullet), so line breaks and positions stay exactly
as in the deck; hidden pictures are left out (absolute positions, nothing reflows). Slides with many small shapes
(diagrams) are shown whole (one state).
Writes <out>/units.json (per slide: units with their text) and <out>/png/slide_NN_kK.png (K = units visible)."""
import argparse, json, os, re, subprocess, sys, zipfile, glob, shutil
from lxml import etree

A = "http://schemas.openxmlformats.org/drawingml/2006/main"; P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"; NS = {"a": A, "p": P, "r": R}
SOFFICE = "/home/julios/.claude/skills/synced/5530c109-8206-4538-b936-7bd28ef578d7_bc5322ee-ceaf-4248-a4cc-e657bbe2c7a3/pptx/scripts/office/soffice.py"
PPR_ORDER = ["lnSpc", "spcBef", "spcAft", "buClrTx", "buClr"]
ap = argparse.ArgumentParser(); ap.add_argument("deck"); ap.add_argument("out"); ap.add_argument("--width", type=int, default=1920)
a = ap.parse_args()
z = zipfile.ZipFile(a.deck)
pres = etree.fromstring(z.read("ppt/presentation.xml"))
sz = pres.find("p:sldSz", NS); SW, SH = int(sz.get("cx")), int(sz.get("cy"))
rels = {r.get("Id"): r.get("Target") for r in etree.fromstring(z.read("ppt/_rels/presentation.xml.rels"))}
slides = ["ppt/" + rels[s.get(f"{{{R}}}id")] for s in pres.find("p:sldIdLst", NS)]


def txt(el): return "".join(t.text or "" for t in el.iter(f"{{{A}}}t")).strip()


def box(el):
    x = el.find(".//a:xfrm", NS)
    if x is None or x.find("a:off", NS) is None: return None
    o, e = x.find("a:off", NS), x.find("a:ext", NS)
    return int(o.get("x")), int(o.get("y")), int(e.get("cx")), int(e.get("cy"))


def units_of(sld):
    """[(kind, element(s), text, sort key)] in reading order; kind 'para' = list of <a:p>, 'shape' = top-level element,
    'shapes' = explicit unit: all top-level shapes named 'u<k>_...' (decks built by rod_deck.py), k = click order."""
    tree = sld.find(".//p:spTree", NS); out, n_small_shapes = [], 0
    named = {}
    for el in tree:
        c = el.find(".//p:cNvPr", NS); m = re.match(r"u(\d+)_", c.get("name", "")) if c is not None else None
        if m: named.setdefault(int(m.group(1)), []).append(el)
    if named:
        return [("shapes", named[k], " ".join(txt(e) for e in named[k]), (k, 0)) for k in sorted(named)]
    if EXPLICIT: return []   # deck uses named units: slides without them are shown whole
    for el in tree:
        tag = etree.QName(el).localname
        if tag not in ("sp", "pic", "grpSp", "graphicFrame", "cxnSp"): continue
        ph = el.find(".//p:nvPr/p:ph", NS); b = box(el)
        if ph is not None and ph.get("type") in ("title", "ctrTitle", "subTitle", "dt", "ftr", "sldNum"): continue
        area = (b[2] * b[3] / (SW * SH)) if b else 1.0
        key = (b[1], b[0]) if b else (0, 0)
        body = el.find("p:txBody", NS)
        if tag == "sp" and body is not None and txt(body):
            paras = [p for p in body.findall("a:p", NS)]
            groups, cur = [], None
            for p in paras:
                lvl = int(p.find("a:pPr", NS).get("lvl", "0")) if p.find("a:pPr", NS) is not None else 0
                if lvl == 0 and txt(p) or cur is None: cur = [p]; groups.append(cur)
                else: cur.append(p)
            groups = [g for g in groups if any(txt(p) for p in g)]
            if len(txt(body)) < 40 and ph is None: n_small_shapes += 1
            for gi, g in enumerate(groups):
                out.append(("para", g, " ".join(txt(p) for p in g), (key[0] + gi, key[1])))
        elif tag in ("pic", "grpSp", "graphicFrame") and area >= 0.06:
            out.append(("shape", el, txt(el), key))
        elif tag in ("sp", "cxnSp"):
            n_small_shapes += 1
    if n_small_shapes >= 6: return []   # diagram slide: show whole
    return sorted(out, key=lambda u: u[3])


def hide_para(p):
    for rpr in p.findall("a:r/a:rPr", NS) + p.findall("a:fld/a:rPr", NS) + p.findall("a:endParaRPr", NS):
        for f in rpr:
            if etree.QName(f).localname in ("solidFill", "gradFill", "noFill", "pattFill"): rpr.remove(f)
        sf = etree.Element(f"{{{A}}}solidFill"); c = etree.SubElement(sf, f"{{{A}}}srgbClr", val="FFFFFF"); etree.SubElement(c, f"{{{A}}}alpha", val="0")
        ln = rpr.find("a:ln", NS); rpr.insert(1 if ln is not None else 0, sf)
    for r in p.findall("a:r", NS):
        if r.find("a:rPr", NS) is None:
            rpr = etree.Element(f"{{{A}}}rPr"); r.insert(0, rpr)
            sf = etree.SubElement(rpr, f"{{{A}}}solidFill"); c = etree.SubElement(sf, f"{{{A}}}srgbClr", val="FFFFFF"); etree.SubElement(c, f"{{{A}}}alpha", val="0")
    ppr = p.find("a:pPr", NS)
    if ppr is None: ppr = etree.Element(f"{{{A}}}pPr"); p.insert(0, ppr)
    for b in ppr.findall("a:buClr", NS) + ppr.findall("a:buClrTx", NS): ppr.remove(b)
    bc = etree.Element(f"{{{A}}}buClr"); c = etree.SubElement(bc, f"{{{A}}}srgbClr", val="FFFFFF"); etree.SubElement(c, f"{{{A}}}alpha", val="0")
    ppr.insert(sum(1 for ch in ppr if etree.QName(ch).localname in PPR_ORDER[:3]), bc)


EXPLICIT = False
EXPLICIT = any(re.search(rb'name="u[0-9]+_', z.read(s)) for s in slides)
os.makedirs(os.path.join(a.out, "png"), exist_ok=True)
info, n_units = [], []
for i, s in enumerate(slides, 1):
    u = units_of(etree.fromstring(z.read(s)))
    n_units.append(len(u)); info.append({"slide": i, "units": [{"kind": k, "text": t[:300]} for k, _, t, _ in u]})
json.dump(info, open(os.path.join(a.out, "units.json"), "w"), indent=1, ensure_ascii=False)
print("units per slide:", n_units)

for k in range(max(n_units) + 1):   # deck variant k: on every slide the first k units are visible
    todo = [i for i, n in enumerate(n_units, 1) if k < n or (k == n)]
    if not todo: continue
    tmp = os.path.join(a.out, f"_k{k}"); os.makedirs(tmp, exist_ok=True); dk = os.path.join(tmp, "deck.pptx")
    zo = zipfile.ZipFile(dk, "w", zipfile.ZIP_DEFLATED)
    for name in z.namelist():
        data = z.read(name)
        if name in slides:
            i = slides.index(name) + 1
            if i in todo and k < n_units[i - 1]:
                x = etree.fromstring(data)
                for kind, el, _, _ in units_of(x)[k:]:
                    if kind == "para":
                        for p in el: hide_para(p)
                    elif kind == "shapes":
                        for e in el: e.getparent().remove(e)
                    else: el.getparent().remove(el)
                data = etree.tostring(x, xml_declaration=True, encoding="UTF-8", standalone=True)
        zo.writestr(name, data)
    zo.close()
    subprocess.run([sys.executable, SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", tmp, dk], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in todo:
        subprocess.run(["pdftoppm", "-png", "-singlefile", "-scale-to-x", str(a.width), "-scale-to-y", "-1", "-f", str(i), "-l", str(i),
                        os.path.join(tmp, "deck.pdf"), os.path.join(a.out, "png", f"slide_{i:02d}_k{k}")], check=True)
    shutil.rmtree(tmp); print(f"state {k}: {len(todo)} slides", flush=True)
