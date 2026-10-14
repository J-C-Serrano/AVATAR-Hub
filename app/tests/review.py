import json
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("/hub/app/app.py", default_timeout=900)
at.session_state["page"] = "voice"; at.session_state["vview"] = "review"; at.session_state["vid"] = "pipeline-test"; at.run()
assert not at.exception, at.exception
at.radio[0].set_value("B").run()
at.text_area[0].input("I want more accent and a bit slower please").run()
next(b for b in at.button if "Try again" in b.label).click().run()
assert not at.exception, at.exception
p = json.load(open("/hub/data/voices/pipeline-test/profile.json"))
r = p["rounds"][-1]; print("round", r["round"], "notes:", r["notes"], "based_on:", r["based_on"])
for t in "ABC":
    c = json.load(open(f"/hub/data/voices/pipeline-test/{r['dir']}/{t}.json")); s = c["settings"]
    print(t, c["label"], "| lora_scale", s["lora_scale"], "speed", s["speed"])
print("caption:", [c.value[:120] for c in at.caption][:2])
at.radio[0].set_value("C").run()
next(b for b in at.button if "Save version" in b.label).click().run()
p = json.load(open("/hub/data/voices/pipeline-test/profile.json")); print("saved:", p["status"], p["chosen"], p["settings"]["lora_scale"], p["settings"]["speed"])
print("REVIEW_OK")
