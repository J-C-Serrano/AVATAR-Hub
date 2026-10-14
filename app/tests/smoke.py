"""Headless click-through of the voice tool (streamlit.testing). Run inside avatar-hub-app:p0 with GPU."""
import os, time
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("/hub/app/app.py", default_timeout=600).run()
assert not at.exception, at.exception
print("home buttons:", [(b.label, b.disabled) for b in at.button])
at.button[0].click().run()                                   # Open Voice
print("voice page subheaders:", [s.value for s in at.subheader])
assert any("Speak with" in m.value for m in at.markdown), "speak panel missing"
at.text_area[0].input("Hello everyone. This is a short test of the voice tool.").run()
btn = next(b for b in at.button if "Create speech" in b.label)
t = time.time(); btn.click().run(); print(f"create speech took {time.time() - t:.0f}s")
assert not at.exception, at.exception
print("success:", [s.value for s in at.success])
gens = os.listdir("/hub/data/voices/julio-serrano/generations"); print("generations:", gens)
d = os.path.join("/hub/data/voices/julio-serrano/generations", sorted(gens)[-1]); print("files:", sorted(os.listdir(d)))
# create-voice form
at.button[0].click().run() if False else None
at2 = AppTest.from_file("/hub/app/app.py", default_timeout=120)
at2.session_state["page"] = "voice"; at2.session_state["vview"] = "create"; at2.run()
assert not at2.exception, at2.exception
print("create form inputs:", [t.label for t in at2.text_input], [c.label[:40] for c in at2.checkbox])
at3 = AppTest.from_file("/hub/app/app.py", default_timeout=120)
at3.session_state["page"] = "voice"; at3.session_state["vview"] = "record"; at3.session_state["vid"] = "julio-serrano"; at3.run()
assert not at3.exception, at3.exception
print("record page expanders:", [e.label[:30] for e in at3.expander])
print("SMOKE_OK")
